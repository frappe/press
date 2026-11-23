import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import boto3
import frappe
from frappe.tests.utils import FrappeTestCase
from moto import mock_aws

from press.press.audit import BackupRecordCheck, OffsiteBackupCheck
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.backup_bucket.test_backup_bucket import create_test_backup_bucket
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_activity.site_activity import log_site_activity
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.telegram_message.telegram_message import TelegramMessage


@patch.object(TelegramMessage, "enqueue", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestBackupRecordCheck(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def setUp(self):
		super().setUp()

		self.yesterday = frappe.utils.now_datetime().date() - timedelta(days=1)
		self._2_hrs_before_yesterday = datetime.combine(self.yesterday, datetime.min.time()) - timedelta(
			hours=2
		)

	def test_audit_will_fail_if_backup_older_than_interval(self):
		create_test_press_settings()
		site = create_test_site(creation=self._2_hrs_before_yesterday)
		create_test_site_backup(site.name, creation=self._2_hrs_before_yesterday + timedelta(hours=1))
		BackupRecordCheck()
		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": BackupRecordCheck.audit_type})
		self.assertEqual(audit_log.status, "Failure")

	def test_audit_succeeds_when_backup_in_interval_exists(self):
		create_test_press_settings()
		plan = create_test_plan("Site")
		site = create_test_site(creation=self._2_hrs_before_yesterday, plan=plan.name)

		create_test_site_backup(
			site.name,
			creation=self._2_hrs_before_yesterday + timedelta(hours=3),
		)
		BackupRecordCheck()
		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": BackupRecordCheck.audit_type})
		self.assertEqual(audit_log.status, "Success")

	def test_audit_succeeds_for_site_without_plan_that_has_backup_in_interval(self):
		create_test_press_settings()
		create_test_plan("Site", is_trial_plan=True)
		site = create_test_site(creation=self._2_hrs_before_yesterday)
		frappe.db.set_value("Site", site.name, "plan", None)
		create_test_site_backup(site.name, creation=self._2_hrs_before_yesterday + timedelta(hours=3))

		BackupRecordCheck()

		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": BackupRecordCheck.audit_type})
		sites_without_backup = frappe.parse_json(audit_log.log)[BackupRecordCheck.list_key]
		self.assertNotIn(site.name, sites_without_backup)

	def test_audit_log_is_created(self):
		create_test_press_settings()
		site = create_test_site(creation=self._2_hrs_before_yesterday)
		create_test_site_backup(site.name, creation=self.yesterday)
		audit_logs_before = frappe.db.count("Audit Log", {"audit_type": BackupRecordCheck.audit_type})
		BackupRecordCheck()
		audit_logs_after = frappe.db.count("Audit Log", {"audit_type": BackupRecordCheck.audit_type})
		self.assertGreater(audit_logs_after, audit_logs_before)

	def test_sites_created_within_interval_are_ignored(self):
		create_test_press_settings()
		create_test_site()
		# no backup
		BackupRecordCheck()

		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": BackupRecordCheck.audit_type})
		self.assertEqual(audit_log.status, "Success")

	def test_sites_that_were_recently_activated_are_ignored(self):
		create_test_press_settings()
		site = create_test_site(creation=self._2_hrs_before_yesterday)
		act = log_site_activity(site.name, "Activate Site")
		act.db_set("creation", self._2_hrs_before_yesterday + timedelta(hours=24))
		BackupRecordCheck()
		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": BackupRecordCheck.audit_type})
		self.assertEqual(audit_log.status, "Success")


@patch.object(TelegramMessage, "enqueue", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestOffsiteBackupCheck(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_audit_succeeds_when_all_remote_files_are_in_remote(self):
		create_test_press_settings()
		site = create_test_site()
		site_backup = create_test_site_backup(site.name)
		frappe.db.set_value("Remote File", site_backup.remote_database_file, "file_path", "remote_file1")
		frappe.db.set_value("Remote File", site_backup.remote_public_file, "file_path", "remote_file2")
		frappe.db.set_value("Remote File", site_backup.remote_private_file, "file_path", "remote_file3")
		frappe.db.set_single_value("Press Settings", "aws_s3_bucket", "default.backups.test")
		with patch.object(
			OffsiteBackupCheck,
			"_get_all_files_in_s3",
			new=lambda self, bucket: {"remote_file1", "remote_file2", "remote_file3"},
		):
			OffsiteBackupCheck()
		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": OffsiteBackupCheck.audit_type})
		self.assertEqual(audit_log.status, "Success")

	def test_audit_fails_when_all_remote_files_not_in_remote(self):
		create_test_press_settings()
		site = create_test_site()
		# 3 remote files are created here
		site_backup = create_test_site_backup(site.name)
		frappe.db.set_value("Remote File", site_backup.remote_database_file, "file_path", "remote_file1")
		frappe.db.set_single_value("Press Settings", "aws_s3_bucket", "default.backups.test")
		with patch.object(
			OffsiteBackupCheck, "_get_all_files_in_s3", new=lambda self, bucket: {"remote_file1"}
		):
			OffsiteBackupCheck()
		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": OffsiteBackupCheck.audit_type})
		self.assertEqual(audit_log.status, "Failure")

	def test_audit_checks_each_remote_file_against_its_own_bucket_only(self):
		create_test_press_settings()
		site = create_test_site()
		site_backup = create_test_site_backup(str(site.name), bucket="eu.backups.test")
		# Set after the backup, or creating it asks for offsite credentials
		frappe.db.set_single_value("Press Settings", "aws_s3_bucket", "default.backups.test")
		files_in = {"eu.backups.test": set(), "default.backups.test": set()}
		for field in ("remote_database_file", "remote_public_file", "remote_private_file"):
			file_path = f"{site.name}/{field}"
			frappe.db.set_value("Remote File", str(site_backup.get(field)), "file_path", file_path)
			files_in["eu.backups.test"].add(file_path)

		with patch.object(
			OffsiteBackupCheck, "_get_all_files_in_s3", new=lambda self, bucket: files_in.get(bucket, set())
		):
			OffsiteBackupCheck()

		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": OffsiteBackupCheck.audit_type})
		missing = json.loads(str(audit_log.get("log")))[OffsiteBackupCheck.list_key]
		self.assertEqual([file for file in missing if file["site"] == site.name], [])

	@mock_aws
	def test_audit_lists_the_replica_of_a_replicated_bucket(self):
		create_test_press_settings()
		settings = frappe.get_single("Press Settings")
		settings.update(
			{
				"offsite_backups_access_key_id": "test-access-key",
				"offsite_backups_secret_access_key": "test-secret-key",  # pragma: allowlist secret
			}
		)
		settings.save()
		bucket = create_test_backup_bucket("primary.backups.test", "us-east-1")
		bucket.update(
			{
				"replication_enabled": 1,
				"replication_bucket": "replica.backups.test",
				"replication_region": "us-east-1",
			}
		)
		bucket.save(ignore_permissions=True)
		site = create_test_site()
		site_backup = create_test_site_backup(str(site.name), bucket="primary.backups.test")
		database_path = f"{site.name}/database.sql.gz"
		frappe.db.set_value(
			"Remote File", str(site_backup.get("remote_database_file")), "file_path", database_path
		)
		# Only the replica holds it, as once the primary expires the object
		s3 = boto3.client("s3", region_name="us-east-1")
		s3.create_bucket(Bucket="replica.backups.test")
		s3.put_object(Bucket="replica.backups.test", Key=database_path, Body=b"x")

		OffsiteBackupCheck()

		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": OffsiteBackupCheck.audit_type})
		missing = json.loads(str(audit_log.get("log")))[OffsiteBackupCheck.list_key]
		missing_files = {file["name"] for file in missing if file["site"] == site.name}
		self.assertNotIn(str(site_backup.get("remote_database_file")), missing_files)
		self.assertEqual(
			missing_files,
			{str(site_backup.get("remote_public_file")), str(site_backup.get("remote_private_file"))},
		)
