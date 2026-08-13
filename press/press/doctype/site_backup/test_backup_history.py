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
	MAX_RANGE_DAYS,
	cache_key,
	get_backup_history,
)

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
		# The job database lives on a real agent, so every test stubs it and the ones
		# that care about it set a return value
		agent = patch(
			"press.press.doctype.site_backup.backup_history.Agent.get_site_backup_jobs",
			return_value={"jobs": []},
		)
		self.agent_backup_jobs = agent.start()
		self.addCleanup(agent.stop)

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

	def given_agent_jobs(self, jobs: list[dict]):
		self.agent_backup_jobs.return_value = {"site": self.site.name, "jobs": jobs}

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

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 2048)
		self.assertEqual(day["public"], 512)
		self.assertEqual(day["private"], 128)

	def test_private_files_are_not_counted_as_public_files(self):
		self.upload_backup("2023-10-02", "20231002_000502-private-files.tar", body=b"q" * 128)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["public"], 0)
		self.assertEqual(day["private"], 128)

	def test_day_holding_nothing_is_marked_not_available(self):
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz")

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-03")["days"]

		self.assertEqual([day["status"] for day in history], ["Success", "Not Available"])
		self.assertEqual(history[1]["database"], 0)

	def test_config_only_day_still_counts_as_a_backup(self):
		self.upload_backup("2023-10-02", "20231002_000502-site_config_backup.json")

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 0)

	def test_range_is_inclusive_and_ordered_newest_first(self):
		history = get_backup_history(self.site.name, "2023-10-01", "2023-10-04")["days"]

		self.assertEqual(
			[day["date"] for day in history],
			["2023-10-04", "2023-10-03", "2023-10-02", "2023-10-01"],
		)

	def test_backups_outside_the_range_are_left_out(self):
		self.upload_backup("2023-09-30", "before-database.sql.gz")
		self.upload_backup("2023-10-02", "inside-database.sql.gz")
		self.upload_backup("2023-10-05", "after-database.sql.gz")

		history = get_backup_history(self.site.name, "2023-10-01", "2023-10-03")["days"]

		self.assertEqual(
			[day["status"] for day in history],
			["Not Available", "Success", "Not Available"],
		)

	def test_another_sites_backups_are_left_out(self):
		other_site = create_test_site()
		boto3.client("s3", region_name=REGION).put_object(
			Bucket=BUCKET, Key=f"{other_site.name}/2023-10-02/database.sql.gz", Body=b"backup"
		)

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"]

		self.assertEqual(history[0]["status"], "Not Available")

	def test_press_record_answers_for_a_day_whose_object_is_gone_from_the_bucket(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 4096)

	def test_press_record_is_preferred_over_the_bucket_for_the_same_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 99)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["database"], 4096)

	def test_bucket_fills_in_days_press_has_no_record_of(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz", body=b"x" * 99)

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-03")["days"]

		self.assertEqual([day["database"] for day in history], [99, 4096])

	def test_bucket_is_left_alone_when_records_cover_every_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)

		# Dropping the bucket makes any S3 read fail, so a passing call proves none happened
		boto3.client("s3", region_name=REGION).delete_bucket(Bucket=BUCKET)
		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"]

		self.assertEqual(history[0]["database"], 4096)

	def test_every_day_reports_the_same_shape_whatever_the_source(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz")
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz")

		history = get_backup_history(self.site.name, "2023-10-01", "2023-10-03")["days"]

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

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

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

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["database"], 32)

	def test_days_before_the_site_existed_are_left_out(self):
		created_on = frappe.utils.getdate(frappe.db.get_value("Site", self.site.name, "creation"))
		start = frappe.utils.add_days(created_on, -5)

		history = get_backup_history(self.site.name, str(start), str(created_on))["days"]

		self.assertEqual([day["date"] for day in history], [str(created_on)])

	def test_range_entirely_before_the_site_existed_is_empty(self):
		created_on = frappe.utils.getdate(frappe.db.get_value("Site", self.site.name, "creation"))

		history = get_backup_history(
			self.site.name,
			str(frappe.utils.add_days(created_on, -10)),
			str(frappe.utils.add_days(created_on, -2)),
		)["days"]

		self.assertEqual(history, [])

	def test_future_days_are_left_out(self):
		today = frappe.utils.getdate()

		history = get_backup_history(self.site.name, str(today), str(frappe.utils.add_days(today, 5)))["days"]

		self.assertEqual([day["date"] for day in history], [str(today)])

	def test_a_finished_range_is_served_from_cache_on_the_second_call(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 16)
		first = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		# Removing the object would make a fresh walk come back empty, so 16 proves the cache
		boto3.client("s3", region_name=REGION).delete_object(
			Bucket=BUCKET, Key=f"{self.site.name}/2023-10-02/20231002_000502-database.sql.gz"
		)
		second = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertEqual(first, second)
		self.assertEqual(second["days"][0]["database"], 16)

	def test_a_range_reaching_today_is_not_cached(self):
		today = frappe.utils.getdate()
		get_backup_history(self.site.name, str(today), str(today))

		self.assertIsNone(frappe.cache().get_value(cache_key(self.site.name, today, today)))

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

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 24)

	def test_a_full_year_range_returns_a_row_per_day(self):
		self.upload_backup("2023-06-15", "20230615_000502-database.sql.gz")

		history = get_backup_history(self.site.name, "2023-01-01", "2023-12-31")["days"]

		self.assertEqual(len(history), 365)
		self.assertEqual(sum(day["status"] == "Success" for day in history), 1)

	def test_a_day_the_server_ran_a_backup_on_is_reported_even_with_nothing_stored(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00")])

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 64)
		self.assertEqual(day["config"], 8)

	def test_a_failed_backup_is_reported_as_a_failure_not_as_missing(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00", status="Failure")])

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Failure")

	def test_a_day_that_failed_then_succeeded_is_reported_as_a_success(self):
		jobs = [
			self.agent_job("2023-10-02 04:00:00", status="Failure"),
			self.agent_job("2023-10-02 06:00:00"),
		]
		self.given_agent_jobs(jobs)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")

	def test_stored_objects_outrank_what_the_server_remembers(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 900)

		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00", status="Failure")])

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 900)

	def test_the_server_is_left_alone_when_records_cover_every_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz")

		get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.agent_backup_jobs.assert_not_called()

	def test_the_bucket_is_left_alone_when_the_server_reports_a_success(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00")])
		boto3.client("s3", region_name=REGION).delete_bucket(Bucket=BUCKET)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Success")

	def test_an_unreachable_server_is_reported_as_unconfirmed_not_as_no_backup(self):
		self.agent_backup_jobs.side_effect = Exception("connection refused")

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertEqual(history["days"][0]["status"], "Not Available")
		self.assertTrue(history["unconfirmed"])

	def test_an_agent_without_the_endpoint_leaves_the_trail_readable(self):
		self.agent_backup_jobs.side_effect = Exception("404 Not Found")

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertEqual(history["days"][0]["status"], "Not Available")
		self.assertTrue(history["unconfirmed"])

	def test_a_server_that_could_not_answer_is_not_asked_again(self):
		self.agent_backup_jobs.side_effect = Exception("404 Not Found")
		get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		get_backup_history(self.site.name, "2023-10-03", "2023-10-03")

		self.assertEqual(self.agent_backup_jobs.call_count, 1)

	def test_a_trail_the_server_could_not_confirm_is_not_cached(self):
		self.agent_backup_jobs.side_effect = Exception("404 Not Found")

		get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertIsNone(
			frappe.cache().get_value(
				cache_key(
					self.site.name, frappe.utils.getdate("2023-10-02"), frappe.utils.getdate("2023-10-02")
				)
			)
		)

	def test_a_trail_the_other_sources_fully_answered_is_not_unconfirmed(self):
		self.agent_backup_jobs.side_effect = Exception("404 Not Found")
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz")

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertFalse(history["unconfirmed"])

	def test_an_agent_that_answers_a_missing_route_with_nothing_is_not_asked_again(self):
		# Agent.request swallows a 404 into None rather than raising
		self.agent_backup_jobs.return_value = None
		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		get_backup_history(self.site.name, "2023-10-03", "2023-10-03")

		self.assertTrue(history["unconfirmed"])
		self.assertEqual(self.agent_backup_jobs.call_count, 1)

	def test_a_truncated_answer_leaves_the_remaining_days_unconfirmed(self):
		self.agent_backup_jobs.return_value = {"jobs": [], "truncated": True}

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertTrue(history["unconfirmed"])

	def test_a_complete_answer_leaves_nothing_unconfirmed(self):
		self.given_agent_jobs([self.agent_job("2023-10-02 04:00:00")])

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertFalse(history["unconfirmed"])

	def test_a_bench_without_offsite_credentials_still_answers(self):
		"""get_decrypted_password throws when the secret was never set, which used to 500 the page."""
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=64)

		with patch(
			"press.press.doctype.site_backup.backup_history.get_decrypted_password",
			return_value=None,
		):
			history = get_backup_history(self.site.name, "2023-10-01", "2023-10-02")

		self.assertEqual([day["status"] for day in history["days"]], ["Success", "Not Available"])
		self.assertEqual(history["days"][0]["database"], 64)

	def test_an_unset_access_key_skips_the_bucket_rather_than_raising(self):
		frappe.db.set_single_value("Press Settings", "offsite_backups_access_key_id", "")
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz")

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")["days"][0]

		self.assertEqual(day["status"], "Not Available")

	def test_reversed_range_is_rejected(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"Start date must be on or before the end date",
			get_backup_history,
			self.site.name,
			"2023-10-05",
			"2023-10-01",
		)

	def test_range_wider_than_a_year_is_rejected(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			f"Pick a range of {MAX_RANGE_DAYS} days or less",
			get_backup_history,
			self.site.name,
			"2023-01-01",
			"2024-12-31",
		)
