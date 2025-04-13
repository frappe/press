from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.audit import BackupRecordCheck, OffsiteBackupCheck
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_activity.site_activity import log_site_activity
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup
from press.telegram_utils import Telegram


@patch.object(Telegram, "send", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestBackupRecordCheck(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def setUp(self):
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
		site = create_test_site(creation=self._2_hrs_before_yesterday)

		create_test_site_backup(
			site.name,
			creation=self._2_hrs_before_yesterday + timedelta(hours=3),
		)
		BackupRecordCheck()
		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": BackupRecordCheck.audit_type})
		self.assertEqual(audit_log.status, "Success")

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


@patch.object(Telegram, "send", new=Mock())
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
		with patch.object(
			OffsiteBackupCheck,
			"_get_all_files_in_s3",
			new=lambda x: ["remote_file1", "remote_file2", "remote_file3"],
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
		with patch.object(OffsiteBackupCheck, "_get_all_files_in_s3", new=lambda x: ["remote_file1"]):
			OffsiteBackupCheck()
		audit_log = frappe.get_last_doc("Audit Log", {"audit_type": OffsiteBackupCheck.audit_type})
		self.assertEqual(audit_log.status, "Failure")
