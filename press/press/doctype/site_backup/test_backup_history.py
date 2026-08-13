# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import patch

import boto3
import frappe
from frappe.tests.utils import FrappeTestCase
from moto import mock_aws

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_backup.backup_history import (
	CACHE_TTL,
	MAX_RANGE_DAYS,
	PARTIAL_CACHE_TTL,
	agent_answer_key,
	build_and_cache,
	cache_seconds,
	get_backup_history,
	process_fetch_backup_jobs_update,
	ready,
)

BUILD_METHOD = "press.press.doctype.site_backup.backup_history.build_and_cache"

BUCKET = "test-backups"
REPLICA_BUCKET = "test-backups-replica"
REGION = "us-east-1"


@mock_aws
class TestBackupHistory(FrappeTestCase):
	def setUp(self):
		# Rollback resets the naming series, so without this the next test reuses the
		# site name and inherits its objects, which moto does not roll back
		self.site = create_test_site(subdomain=f"audit-{frappe.generate_hash(length=8)}")
		# Backdate, or the clamp to site creation hides every date these tests use
		frappe.db.set_value("Site", self.site.name, "creation", "2023-01-01 00:00:00", update_modified=False)
		self.setup_press_settings()
		boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)
		# The server answers as a job of its own, so tests leave its answer in the
		# cache the way the job callback would, and stub the queueing
		agent = patch("press.press.doctype.site_backup.backup_history.Agent.fetch_site_backup_jobs")
		self.queue_backup_jobs = agent.start()
		self.addCleanup(agent.stop)
		self.addCleanup(self.clear_agent_answers)
		# The trail is built in the background; tests run that build inline. Everything
		# else enqueuing during a test, fixtures included, still goes the usual way.
		real_enqueue = frappe.enqueue

		def run_build_inline(method, **kwargs):
			if method == BUILD_METHOD:
				return build_and_cache(kwargs["site"], kwargs["start_date"], kwargs["end_date"])
			return real_enqueue(method, **kwargs)

		enqueue = patch.object(frappe, "enqueue", side_effect=run_build_inline)
		self.enqueue_build = enqueue.start()
		self.addCleanup(enqueue.stop)
		wait = patch(
			"press.press.doctype.site_backup.backup_history.wait_for_agent_answer",
			return_value=None,
		)
		self.wait_for_agent = wait.start()
		self.addCleanup(wait.stop)

	def audit_trail(self, start: str, end: str) -> dict:
		"""The first look starts the build. It finishes inline here, so look again."""
		get_backup_history(self.site.name, start, end)
		return get_backup_history(self.site.name, start, end)

	def build_calls(self) -> int:
		return sum(1 for call in self.enqueue_build.call_args_list if call.args[0] == BUILD_METHOD)

	def clear_agent_answers(self):
		for prefix in (
			"backup_audit_trail_jobs:",
			"backup_audit_trail_building:",
			"backup_audit_trail:",
		):
			frappe.cache().delete_keys(prefix)

	def tearDown(self):
		# The silence flag lives in redis, which no rollback undoes
		frappe.cache().delete_value(
			f"backup_audit_trail_agent_unavailable:{frappe.db.get_value('Site', self.site.name, 'server')}"
		)
		frappe.db.rollback()

	def setup_press_settings(self):
		settings = frappe.get_single("Press Settings")
		settings.aws_s3_bucket = BUCKET
		settings.backup_region = REGION
		settings.offsite_backups_access_key_id = "test-access-key"
		settings.offsite_backups_secret_access_key = "test-secret-key"  # pragma: allowlist secret
		settings.save()

	def upload_backup(self, day: str, file_name: str, body: bytes = b"backup"):
		boto3.client("s3", region_name=REGION).put_object(
			Bucket=BUCKET, Key=f"{self.site.name}/{day}/{file_name}", Body=body
		)

	def record_backup(self, day: str, file_name: str, size: int = 1024, field: str = "remote_database_file"):
		"""A Site Backup Press still holds, whether or not the object survives in the bucket."""
		remote_file = frappe.get_doc(
			{
				"doctype": "Remote File",
				"site": self.site.name,
				"file_name": file_name,
				"file_path": f"{self.site.name}/{day}/{file_name}",
				"file_size": size,
				"bucket": BUCKET,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Site Backup",
				"site": self.site.name,
				"status": "Success",
				"offsite": True,
				"creation": f"{day} 04:00:00",
				field: remote_file.name,
			}
		).db_insert()
		return remote_file

	def add_cluster_bucket(self, replication_enabled: bool):
		"""A Backup Bucket for the site's cluster, which get_backup_bucket resolves ahead of Press Settings."""
		frappe.get_doc(
			{
				"doctype": "Backup Bucket",
				"cluster": frappe.db.get_value("Site", self.site.name, "cluster"),
				"bucket_name": BUCKET,
				"region": REGION,
				"replication_enabled": int(replication_enabled),
				"replication_bucket": REPLICA_BUCKET,
				"replication_region": REGION,
			}
		).insert(ignore_permissions=True)
		boto3.client("s3", region_name=REGION).create_bucket(Bucket=REPLICA_BUCKET)

	def given_agent_jobs(self, jobs: list[dict], truncated: bool = False, day: str = "2023-10-02"):
		"""The answer the server's job leaves behind, for a single day range."""
		frappe.cache().set_value(
			agent_answer_key(self.site.name, day, day),
			{"jobs": jobs, "truncated": truncated},
		)

	def fake_job(self, status: str = "Success", data: dict | None = None, day: str = "2023-10-02"):
		"""Enough of an Agent Job for the callback, which only reads these four fields."""
		return frappe._dict(
			status=status,
			server=frappe.db.get_value("Site", self.site.name, "server"),
			request_path=f"server/backup-jobs?site={self.site.name}&start={day}&end={day}",
			data=frappe.as_json(data or {"jobs": [], "truncated": False}),
		)

	@staticmethod
	def agent_job(started_on: str, status: str = "Success", sizes: dict | None = None) -> dict:
		return {
			"id": 1,
			"status": status,
			"start": started_on,
			"sizes": sizes or {"database": 64, "public": 0, "private": 0, "site_config": 8},
		}

	def test_day_holding_backups_is_sized_by_artifact(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"d" * 2048)
		self.upload_backup("2023-10-02", "20231002_000502-files.tar", body=b"p" * 512)
		self.upload_backup("2023-10-02", "20231002_000502-private-files.tar", body=b"q" * 128)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 2048)
		self.assertEqual(day["public"], 512)
		self.assertEqual(day["private"], 128)

	def test_private_files_are_not_counted_as_public_files(self):
		self.upload_backup("2023-10-02", "20231002_000502-private-files.tar", body=b"q" * 128)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["public"], 0)
		self.assertEqual(day["private"], 128)

	def test_day_holding_nothing_is_marked_not_available(self):
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz")

		history = self.audit_trail("2023-10-02", "2023-10-03")["days"]

		self.assertEqual([day["status"] for day in history], ["Success", "Not Available"])
		self.assertEqual(history[1]["database"], 0)

	def test_config_only_day_still_counts_as_a_backup(self):
		self.upload_backup("2023-10-02", "20231002_000502-site_config_backup.json")

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 0)

	def test_range_is_inclusive_and_ordered_newest_first(self):
		history = self.audit_trail("2023-10-01", "2023-10-04")["days"]

		self.assertEqual(
			[day["date"] for day in history],
			["2023-10-04", "2023-10-03", "2023-10-02", "2023-10-01"],
		)

	def test_backups_outside_the_range_are_left_out(self):
		self.upload_backup("2023-09-30", "before-database.sql.gz")
		self.upload_backup("2023-10-02", "inside-database.sql.gz")
		self.upload_backup("2023-10-05", "after-database.sql.gz")

		history = self.audit_trail("2023-10-01", "2023-10-03")["days"]

		self.assertEqual(
			[day["status"] for day in history],
			["Not Available", "Success", "Not Available"],
		)

	def test_another_sites_backups_are_left_out(self):
		other_site = create_test_site()
		boto3.client("s3", region_name=REGION).put_object(
			Bucket=BUCKET, Key=f"{other_site.name}/2023-10-02/database.sql.gz", Body=b"backup"
		)

		history = self.audit_trail("2023-10-02", "2023-10-02")["days"]

		self.assertEqual(history[0]["status"], "Not Available")

	def test_press_record_answers_for_a_day_whose_object_is_gone_from_the_bucket(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 4096)

	def test_press_record_is_preferred_over_the_bucket_for_the_same_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 99)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["database"], 4096)

	def test_bucket_fills_in_days_press_has_no_record_of(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz", body=b"x" * 99)

		history = self.audit_trail("2023-10-02", "2023-10-03")["days"]

		self.assertEqual([day["database"] for day in history], [99, 4096])

	def test_bucket_is_left_alone_when_records_cover_every_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)

		# Dropping the bucket makes any S3 read fail, so a passing call proves none happened
		boto3.client("s3", region_name=REGION).delete_bucket(Bucket=BUCKET)
		history = self.audit_trail("2023-10-02", "2023-10-02")["days"]

		self.assertEqual(history[0]["database"], 4096)

	def test_every_day_reports_the_same_shape_whatever_the_source(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz")
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz")

		history = self.audit_trail("2023-10-01", "2023-10-03")["days"]

		keys = {"date", "status", "database", "public", "private", "config"}
		self.assertEqual([set(day) for day in history], [keys, keys, keys])

	def test_replicated_bucket_is_read_instead_of_the_primary(self):
		self.add_cluster_bucket(replication_enabled=True)
		# Only the replica holds it, as happens once the primary expires the object
		boto3.client("s3", region_name=REGION).put_object(
			Bucket=REPLICA_BUCKET,
			Key=f"{self.site.name}/2023-10-02/20231002_000502-database.sql.gz",
			Body=b"x" * 64,
		)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 64)

	def test_primary_bucket_is_read_when_replication_is_off(self):
		self.add_cluster_bucket(replication_enabled=False)
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 32)
		boto3.client("s3", region_name=REGION).put_object(
			Bucket=REPLICA_BUCKET,
			Key=f"{self.site.name}/2023-10-02/20231002_000502-database.sql.gz",
			Body=b"x" * 999,
		)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["database"], 32)

	def test_days_before_the_site_existed_are_left_out(self):
		created_on = frappe.utils.getdate(frappe.db.get_value("Site", self.site.name, "creation"))
		start = frappe.utils.add_days(created_on, -5)

		history = self.audit_trail(str(start), str(created_on))["days"]

		self.assertEqual([day["date"] for day in history], [str(created_on)])

	def test_range_entirely_before_the_site_existed_is_empty(self):
		created_on = frappe.utils.getdate(frappe.db.get_value("Site", self.site.name, "creation"))

		history = self.audit_trail(
			str(frappe.utils.add_days(created_on, -10)),
			str(frappe.utils.add_days(created_on, -2)),
		)["days"]

		self.assertEqual(history, [])

	def test_future_days_are_left_out(self):
		today = frappe.utils.getdate()

		history = self.audit_trail(str(today), str(frappe.utils.add_days(today, 5)))["days"]

		self.assertEqual([day["date"] for day in history], [str(today)])

	def test_a_finished_range_is_served_from_cache_on_the_second_call(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 16)
		first = self.audit_trail("2023-10-02", "2023-10-02")

		# Removing the object would make a fresh walk come back empty, so 16 proves the cache
		boto3.client("s3", region_name=REGION).delete_object(
			Bucket=BUCKET, Key=f"{self.site.name}/2023-10-02/20231002_000502-database.sql.gz"
		)
		second = self.audit_trail("2023-10-02", "2023-10-02")

		self.assertEqual(first, second)
		self.assertEqual(second["days"][0]["database"], 16)

	def test_a_range_reaching_today_is_kept_only_briefly(self):
		"""Today can still gain a backup, so its trail must not sit around for an hour."""
		today = frappe.utils.getdate()

		self.assertEqual(cache_seconds(ready([]), today), PARTIAL_CACHE_TTL)
		self.assertEqual(cache_seconds(ready([]), frappe.utils.add_days(today, -1)), CACHE_TTL)

	def test_a_trail_the_server_could_not_finish_is_kept_only_briefly(self):
		yesterday = frappe.utils.add_days(frappe.utils.getdate(), -1)

		self.assertEqual(cache_seconds(ready([], unconfirmed=True), yesterday), PARTIAL_CACHE_TTL)

	def test_a_bucket_the_site_used_before_moving_is_still_read(self):
		# A Remote File pointing at another bucket is how a past cluster shows up
		other_bucket = "old-cluster-backups"
		boto3.client("s3", region_name=REGION).create_bucket(Bucket=other_bucket)
		boto3.client("s3", region_name=REGION).put_object(
			Bucket=other_bucket,
			Key=f"{self.site.name}/2023-10-02/20231002_000502-database.sql.gz",
			Body=b"x" * 24,
		)
		frappe.get_doc(
			{
				"doctype": "Remote File",
				"site": self.site.name,
				"file_name": "older.sql.gz",
				"file_path": f"{self.site.name}/2020-01-01/older.sql.gz",
				"bucket": other_bucket,
			}
		).insert(ignore_permissions=True)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 24)

	def test_a_full_year_range_returns_a_row_per_day(self):
		self.upload_backup("2023-06-15", "20230615_000502-database.sql.gz")

		history = self.audit_trail("2023-01-01", "2023-12-31")["days"]

		self.assertEqual(len(history), 365)
		self.assertEqual(sum(day["status"] == "Success" for day in history), 1)

	def test_a_day_the_server_ran_a_backup_on_is_reported_even_with_nothing_stored(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00")])

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 64)
		self.assertEqual(day["config"], 8)

	def test_a_failed_backup_is_reported_as_a_failure_not_as_missing(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00", status="Failure")])

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Failure")

	def test_a_day_that_failed_then_succeeded_is_reported_as_a_success(self):
		jobs = [
			self.agent_job("2023-10-02 04:00:00", status="Failure"),
			self.agent_job("2023-10-02 06:00:00"),
		]
		self.given_agent_jobs(jobs)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")

	def test_stored_objects_outrank_what_the_server_remembers(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 900)

		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00", status="Failure")])

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 900)

	def test_the_server_is_left_alone_when_records_cover_every_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz")

		self.audit_trail("2023-10-02", "2023-10-02")

		self.queue_backup_jobs.assert_not_called()

	def test_the_bucket_is_left_alone_when_the_server_reports_a_success(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00")])
		boto3.client("s3", region_name=REGION).delete_bucket(Bucket=BUCKET)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")

	def test_the_first_look_reports_the_trail_as_preparing(self):
		"""Nothing is built in the request, so the first look starts it and says so."""
		with patch("press.press.doctype.site_backup.backup_history.frappe.enqueue") as enqueue:
			history = self.audit_trail("2023-10-02", "2023-10-02")

		enqueue.assert_called_once()
		self.assertEqual(history["status"], "Preparing")
		self.assertEqual(history["days"], [])

	def test_a_second_look_while_building_does_not_queue_another_build(self):
		with patch("press.press.doctype.site_backup.backup_history.frappe.enqueue") as enqueue:
			self.audit_trail("2023-10-02", "2023-10-02")
			self.audit_trail("2023-10-02", "2023-10-02")

		enqueue.assert_called_once()

	def test_a_built_trail_is_served_without_building_again(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 16)
		get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.enqueue_build.reset_mock()
		history = self.audit_trail("2023-10-02", "2023-10-02")

		self.assertEqual(self.build_calls(), 0)
		self.assertEqual(history["status"], "Ready")
		self.assertEqual(history["days"][0]["database"], 16)

	def test_refresh_builds_the_trail_again(self):
		get_backup_history(self.site.name, "2023-10-02", "2023-10-02")
		self.enqueue_build.reset_mock()

		get_backup_history(self.site.name, "2023-10-02", "2023-10-02", refresh=True)

		self.assertEqual(self.build_calls(), 1)

	def test_a_server_that_cannot_be_queued_is_reported_unconfirmed_not_as_no_backup(self):
		self.queue_backup_jobs.side_effect = Exception("connection refused")

		history = self.audit_trail("2023-10-02", "2023-10-02")

		self.assertEqual(history["days"][0]["status"], "Not Available")
		self.assertTrue(history["unconfirmed"])

	def test_a_server_that_could_not_be_queued_is_not_asked_again(self):
		self.queue_backup_jobs.side_effect = Exception("connection refused")
		self.audit_trail("2023-10-02", "2023-10-02")

		self.audit_trail("2023-10-03", "2023-10-03")

		self.assertEqual(self.queue_backup_jobs.call_count, 1)

	def test_a_failed_job_stops_the_server_being_asked_again(self):
		"""An agent without the route fails every time, so the callback stops the asking."""
		process_fetch_backup_jobs_update(self.fake_job(status="Failure"))

		history = self.audit_trail("2023-10-02", "2023-10-02")

		self.queue_backup_jobs.assert_not_called()
		self.assertTrue(history["unconfirmed"])

	def test_a_successful_job_leaves_its_answer_for_the_next_look(self):
		process_fetch_backup_jobs_update(
			self.fake_job(data={"jobs": [self.agent_job("2023-10-02 04:00:00")], "truncated": False})
		)

		history = self.audit_trail("2023-10-02", "2023-10-02")

		self.queue_backup_jobs.assert_not_called()
		self.assertEqual(history["days"][0]["status"], "Success")

	def test_a_trail_the_other_sources_fully_answered_is_not_unconfirmed(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz")

		history = self.audit_trail("2023-10-02", "2023-10-02")

		self.assertFalse(history["unconfirmed"])

	def test_a_truncated_answer_leaves_the_remaining_days_unconfirmed(self):
		self.given_agent_jobs([], truncated=True)

		history = self.audit_trail("2023-10-02", "2023-10-02")

		self.assertTrue(history["unconfirmed"])

	def test_a_complete_answer_leaves_nothing_unconfirmed(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00")])

		history = self.audit_trail("2023-10-02", "2023-10-02")

		self.assertFalse(history["unconfirmed"])

	def test_a_bench_without_offsite_credentials_still_answers(self):
		"""get_decrypted_password throws when the secret was never set, which used to 500 the page."""
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=64)

		with patch(
			"press.press.doctype.site_backup.backup_history.get_decrypted_password",
			return_value=None,
		):
			history = self.audit_trail("2023-10-01", "2023-10-02")

		self.assertEqual([day["status"] for day in history["days"]], ["Success", "Not Available"])
		self.assertEqual(history["days"][0]["database"], 64)

	def test_an_unset_access_key_skips_the_bucket_rather_than_raising(self):
		frappe.db.set_single_value("Press Settings", "offsite_backups_access_key_id", "")
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz")

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Not Available")

	def test_reversed_range_is_rejected(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"Pick a start date on or before the end date",
			get_backup_history,
			self.site.name,
			"2023-10-05",
			"2023-10-01",
		)

	def test_range_wider_than_a_year_is_rejected(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			f"more than the {MAX_RANGE_DAYS} day limit",
			get_backup_history,
			self.site.name,
			"2023-01-01",
			"2024-12-31",
		)
