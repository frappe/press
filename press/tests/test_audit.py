import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import frappe

from press.press.audit import BackupRecordCheck
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup
from press.telegram_utils import Telegram


@patch.object(Telegram, "send", new=Mock())
class TestAudit(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()


class TestBackupRecordCheck(TestAudit):
	def test_audit_will_fail_on_backup_older_than_interval(self):
		create_test_press_settings()
		site = create_test_site()
		create_test_site_backup(
			site.name, creation=datetime.now() - timedelta(hours=BackupRecordCheck.interval + 1)
		)
		BackupRecordCheck()
		audit_log = frappe.get_last_doc(
			"Audit Log", {"audit_type": BackupRecordCheck.audit_type}
		)
		self.assertEqual(audit_log.status, "Failure")
