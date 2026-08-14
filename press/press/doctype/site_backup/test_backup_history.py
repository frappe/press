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
	AGENT_JOB_TYPE,
	CACHE_TTL,
	MAX_RANGE_DAYS,
	PARTIAL_CACHE_TTL,
	REALTIME_EVENT,
	agent_answer_key,
	build_and_cache,
	build_key,
	cache_key,
	cache_seconds,
	get_backup_history,
	process_fetch_backup_jobs_update,
	read_agent_answer,
	ready,
)
from press.press.doctype.site_backup_summary.site_backup_summary import record_days

BUILD_METHOD = "press.press.doctype.site_backup.backup_history.build_and_cache"


class BucketOnFire(Exception):
	"""Whatever a build can die of, which the trail has to survive either way."""


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
		# Building a test bench leaves failures against its server, which would make
		# every test look like it is talking to an unreachable agent
		frappe.db.delete("Agent Request Failure", {"server": self.server})

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
		realtime = patch("press.press.doctype.site_backup.backup_history.frappe.publish_realtime")
		self.publish_realtime = realtime.start()
		self.addCleanup(realtime.stop)

	def audit_trail(self, start: str, end: str) -> dict:
		"""The first look starts the build. It finishes inline here, so look again."""
		get_backup_history(self.site.name, start, end)
		return get_backup_history(self.site.name, start, end)

	def given_undelivered_job(self, minutes_ago: int):
		"""A job the agent never acknowledged, which leaves job_id at 0."""
		if not frappe.db.exists("Agent Job Type", AGENT_JOB_TYPE):
			frappe.get_doc(
				{
					"doctype": "Agent Job Type",
					"name": AGENT_JOB_TYPE,
					"request_method": "POST",
					"request_path": "server/backup-jobs",
					"steps": [{"step_name": AGENT_JOB_TYPE}],
				}
			).insert(ignore_permissions=True)

		job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"server_type": "Server",
				"server": self.server,
				"site": self.site.name,
				"status": "Undelivered",
				"job_type": AGENT_JOB_TYPE,
				"request_method": "POST",
				"request_path": "server/backup-jobs",
				"request_data": "{}",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"Agent Job",
			job.name,
			"creation",
			frappe.utils.add_to_date(None, minutes=-minutes_ago),
			update_modified=False,
		)

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
		frappe.cache().delete_value(f"backup_audit_trail_agent_unavailable:{self.server}")
		frappe.db.rollback()

	@property
	def server(self) -> str:
		return frappe.db.get_value("Site", self.site.name, "server")

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

		keys = {
			"date",
			"status",
			"database",
			"public",
			"private",
			"config",
			"files",
			"source",
			"expired_on",
			"rule",
			"keep_till",
			"sizes_known",
			"started_at",
			"offsite",
			"with_files",
			"physical",
		}
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
			"press.press.doctype.site_backup.backup_objects.get_decrypted_password",
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

	def test_a_build_never_waits_on_the_server(self):
		"""Sleeping here would hold a long queue worker while the agent job is delivered."""
		self.audit_trail("2023-10-02", "2023-10-02")

		self.queue_backup_jobs.assert_called_once()
		self.assertIsNone(read_agent_answer(self.site.name, "2023-10-02", "2023-10-02"))

	def test_a_finished_build_tells_the_page_to_look_again(self):
		self.audit_trail("2023-10-02", "2023-10-02")

		events = [call.kwargs.get("event") for call in self.publish_realtime.call_args_list]
		self.assertIn(REALTIME_EVENT, events)

	def test_the_servers_answer_drops_the_trail_built_without_it(self):
		"""Otherwise the answer sits behind an hour-old trail that was built ignoring it."""
		day = frappe.utils.getdate("2023-10-02")
		self.audit_trail("2023-10-02", "2023-10-02")
		self.assertIsNotNone(frappe.cache().get_value(cache_key(self.site.name, day, day)))

		process_fetch_backup_jobs_update(
			self.fake_job(data={"jobs": [self.agent_job("2023-10-02 04:00:00")], "truncated": False})
		)

		self.assertIsNone(frappe.cache().get_value(cache_key(self.site.name, day, day)))

	def test_an_unreachable_server_is_not_asked(self):
		"""An Agent Request Failure row means nothing is getting through to it."""
		frappe.get_doc(
			{
				"doctype": "Agent Request Failure",
				"server_type": "Server",
				"server": self.server,
				"failure_count": 1,
				"error": "Connection refused",
				"traceback": "Connection refused",
			}
		).insert(ignore_permissions=True)
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 8)

		history = self.audit_trail("2023-10-02", "2023-10-02")

		self.queue_backup_jobs.assert_not_called()
		# The buckets still answer, so the trail is not held up by the server
		self.assertEqual(history["days"][0]["database"], 8)

	def test_a_job_left_undelivered_is_not_waited_on(self):
		self.given_undelivered_job(minutes_ago=5)

		self.audit_trail("2023-10-02", "2023-10-02")

		self.queue_backup_jobs.assert_not_called()

	def test_a_job_only_just_queued_still_counts(self):
		self.given_undelivered_job(minutes_ago=0)

		self.audit_trail("2023-10-02", "2023-10-02")

		self.queue_backup_jobs.assert_called_once()

	def test_a_trimmed_range_comes_back_with_the_trail(self):
		"""The page keys its completion event off this, so it has to be the used range."""
		history = get_backup_history(self.site.name, "2022-06-01", "2023-01-05")

		self.assertEqual(history["start_date"], "2023-01-01")
		self.assertEqual(history["end_date"], "2023-01-05")

	def test_a_future_end_comes_back_trimmed_to_today(self):
		today = frappe.utils.getdate()

		history = get_backup_history(self.site.name, str(today), str(frappe.utils.add_days(today, 30)))

		self.assertEqual(history["end_date"], str(today))

	def test_the_event_carries_the_same_range_the_trail_reports(self):
		history = self.audit_trail("2022-06-01", "2023-01-05")

		published = [
			call.kwargs["message"]
			for call in self.publish_realtime.call_args_list
			if call.kwargs.get("event") == REALTIME_EVENT
		]
		self.assertIn(
			{
				"site": self.site.name,
				"start_date": history["start_date"],
				"end_date": history["end_date"],
			},
			published,
		)

	def test_a_site_name_that_is_not_text_is_rejected_plainly(self):
		from press.api.site import backup_history

		for value in [{"a": 1}, ["x"], 5]:
			with self.subTest(value=value):
				self.assertRaisesRegex(
					frappe.ValidationError,
					"Could not read the site name",
					backup_history,
					value,
					"2023-10-01",
					"2023-10-02",
				)

	def test_a_date_that_is_not_a_date_is_rejected_plainly(self):
		"""Whitelisted parameters arrive as whatever the caller sent."""
		for value in [{"a": 1}, ["2023-10-02"], None, "banana", 20231002]:
			with self.subTest(value=value):
				self.assertRaisesRegex(
					frappe.ValidationError,
					"Could not read the start date",
					get_backup_history,
					self.site.name,
					value,
					"2023-10-02",
				)

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

	def record_expired_backup(self, day: str, rule: str = "Daily", expired_on: str = "2023-10-09"):
		"""A backup whose files retention has since deleted, which is most of an audit's range."""
		remote_file = self.record_backup(day, f"{day.replace('-', '')}_000502-database.sql.gz")
		backup = frappe.db.get_value("Site Backup", {"remote_database_file": remote_file.name})
		frappe.db.set_value(
			"Site Backup",
			backup,
			{
				"database_size": 4096,
				"files_availability": "Unavailable",
				"files_expired_on": expired_on,
				"retention_rule": rule,
			},
		)
		return backup

	def summarise(self, days: dict):
		"""What the nightly roll-up leaves behind once the records are pruned."""
		record_days(self.site.name, days)

	def test_a_day_whose_files_retention_deleted_still_reports_their_size(self):
		self.record_expired_backup("2023-10-02")

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 4096)
		self.assertTrue(day["sizes_known"])

	def test_a_day_whose_files_retention_deleted_says_when_and_under_which_rule(self):
		self.record_expired_backup("2023-10-02", rule="Weekly", expired_on="2023-11-02")

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["files"], "Deleted")
		self.assertEqual(day["rule"], "Weekly")
		self.assertTrue(day["expired_on"].startswith("2023-11-02"))

	def test_a_day_whose_files_are_still_stored_says_so(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz")

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["files"], "Stored")
		self.assertEqual(day["source"], "Press record")

	def test_a_stored_day_names_the_tier_holding_it_and_how_long(self):
		frappe.db.set_single_value("Press Settings", "backup_rotation_scheme", "Grandfather-father-son")
		self.record_backup("2023-10-04", "20231004_000502-database.sql.gz")

		day = self.audit_trail("2023-10-04", "2023-10-04")["days"][0]

		self.assertEqual(day["rule"], "Daily")
		self.assertEqual(day["keep_till"], "2023-10-11")

	def test_a_day_holding_nothing_but_the_config_object_reports_the_files_as_deleted(self):
		self.upload_backup("2023-10-02", "20231002_000502-site_config_backup.json", body=b"c" * 24)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["files"], "Deleted")
		self.assertFalse(day["sizes_known"])

	def test_a_day_holding_a_database_object_reports_the_files_as_stored(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"d" * 64)
		self.upload_backup("2023-10-02", "20231002_000502-site_config_backup.json", body=b"c" * 24)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["files"], "Stored")
		self.assertTrue(day["sizes_known"])

	def test_a_failed_backup_press_recorded_is_reported_without_asking_the_server(self):
		frappe.get_doc(
			{
				"doctype": "Site Backup",
				"site": self.site.name,
				"status": "Failure",
				"creation": "2023-10-02 04:00:00",
			}
		).db_insert()

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Failure")
		self.assertEqual(day["files"], "None")
		self.assertEqual(day["source"], "Press record")

	def test_a_day_press_no_longer_has_a_record_of_is_answered_by_the_summary(self):
		self.summarise(
			{
				"2023-10-02": {
					"date": "2023-10-02",
					"status": "Success",
					"files": "Deleted",
					"rule": "Daily",
					"expired_on": "2023-10-09",
					"sizes_known": True,
					"database": 8192,
				}
			}
		)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 8192)
		self.assertEqual(day["rule"], "Daily")
		self.assertEqual(day["source"], "Daily summary")

	def test_a_record_answers_ahead_of_the_summary_for_the_same_day(self):
		self.summarise({"2023-10-02": {"date": "2023-10-02", "status": "Success", "database": 1}})
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=2048)

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["database"], 2048)
		self.assertEqual(day["source"], "Press record")

	def test_the_summary_is_not_read_when_records_cover_every_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz")

		with patch(
			"press.press.doctype.site_backup.backup_history.get_summarised_days"
		) as get_summarised_days:
			self.audit_trail("2023-10-02", "2023-10-02")

		get_summarised_days.assert_not_called()

	def test_a_day_the_server_answered_for_says_the_files_are_unknown(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00")])

		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["files"], "Unknown")
		self.assertEqual(day["source"], "Server job log")

	def test_a_day_nothing_answered_for_reports_no_source(self):
		day = self.audit_trail("2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Not Available")
		self.assertIsNone(day["source"])
		self.assertFalse(day["sizes_known"])

	def failing_build(self):
		return patch(
			"press.press.doctype.site_backup.backup_history.build_history",
			side_effect=BucketOnFire,
		)

	def test_a_build_that_fails_tells_the_page_instead_of_leaving_it_waiting(self):
		"""Without an answer the page keeps saying the trail is being put together."""
		with self.failing_build():
			self.assertRaises(BucketOnFire, build_and_cache, self.site.name, "2023-10-02", "2023-10-02")

		self.assertEqual(get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["status"], "Broken")
		self.publish_realtime.assert_called()

	def test_a_failed_build_is_not_left_marked_as_building(self):
		with self.failing_build():
			self.assertRaises(BucketOnFire, build_and_cache, self.site.name, "2023-10-02", "2023-10-02")

		self.assertFalse(frappe.cache().get_value(build_key(self.site.name, "2023-10-02", "2023-10-02")))
