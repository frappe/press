# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

import boto3
import frappe
from frappe.tests.utils import FrappeTestCase
from moto import mock_aws

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_backup.backup_history import MAX_RANGE_DAYS, get_backup_history

BUCKET = "test-backups"
REGION = "us-east-1"


@mock_aws
class TestBackupHistory(FrappeTestCase):
	def setUp(self):
		self.site = create_test_site()
		self.setup_press_settings()
		boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)

	def tearDown(self):
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

	def test_day_holding_backups_is_sized_by_artifact(self):
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"d" * 2048)
		self.upload_backup("2023-10-02", "20231002_000502-files.tar", body=b"p" * 512)
		self.upload_backup("2023-10-02", "20231002_000502-private-files.tar", body=b"q" * 128)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")[0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 2048)
		self.assertEqual(day["public"], 512)
		self.assertEqual(day["private"], 128)

	def test_private_files_are_not_counted_as_public_files(self):
		self.upload_backup("2023-10-02", "20231002_000502-private-files.tar", body=b"q" * 128)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")[0]

		self.assertEqual(day["public"], 0)
		self.assertEqual(day["private"], 128)

	def test_day_holding_nothing_is_marked_not_available(self):
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz")

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-03")

		self.assertEqual([day["status"] for day in history], ["Success", "Not Available"])
		self.assertEqual(history[1]["database"], 0)

	def test_config_only_day_still_counts_as_a_backup(self):
		self.upload_backup("2023-10-02", "20231002_000502-site_config_backup.json")

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")[0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 0)

	def test_range_is_inclusive_and_ordered_newest_first(self):
		history = get_backup_history(self.site.name, "2023-10-01", "2023-10-04")

		self.assertEqual(
			[day["date"] for day in history],
			["2023-10-04", "2023-10-03", "2023-10-02", "2023-10-01"],
		)

	def test_backups_outside_the_range_are_left_out(self):
		self.upload_backup("2023-09-30", "before-database.sql.gz")
		self.upload_backup("2023-10-02", "inside-database.sql.gz")
		self.upload_backup("2023-10-05", "after-database.sql.gz")

		history = get_backup_history(self.site.name, "2023-10-01", "2023-10-03")

		self.assertEqual(
			[day["status"] for day in history],
			["Not Available", "Success", "Not Available"],
		)

	def test_another_sites_backups_are_left_out(self):
		other_site = create_test_site()
		boto3.client("s3", region_name=REGION).put_object(
			Bucket=BUCKET, Key=f"{other_site.name}/2023-10-02/database.sql.gz", Body=b"backup"
		)

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertEqual(history[0]["status"], "Not Available")

	def test_press_record_answers_for_a_day_whose_object_is_gone_from_the_bucket(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")[0]

		self.assertEqual(day["status"], "Success")
		self.assertEqual(day["database"], 4096)

	def test_press_record_is_preferred_over_the_bucket_for_the_same_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)
		self.upload_backup("2023-10-02", "20231002_000502-database.sql.gz", body=b"x" * 99)

		day = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")[0]

		self.assertEqual(day["database"], 4096)

	def test_bucket_fills_in_days_press_has_no_record_of(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz", body=b"x" * 99)

		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-03")

		self.assertEqual([day["database"] for day in history], [99, 4096])

	def test_bucket_is_left_alone_when_records_cover_every_day(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz", size=4096)

		# Dropping the bucket makes any S3 read fail, so a passing call proves none happened
		boto3.client("s3", region_name=REGION).delete_bucket(Bucket=BUCKET)
		history = get_backup_history(self.site.name, "2023-10-02", "2023-10-02")

		self.assertEqual(history[0]["database"], 4096)

	def test_every_day_reports_the_same_shape_whatever_the_source(self):
		self.record_backup("2023-10-02", "20231002_000502-database.sql.gz")
		self.upload_backup("2023-10-03", "20231003_000502-database.sql.gz")

		history = get_backup_history(self.site.name, "2023-10-01", "2023-10-03")

		keys = {"date", "status", "database", "public", "private", "config"}
		self.assertEqual([set(day) for day in history], [keys, keys, keys])

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
