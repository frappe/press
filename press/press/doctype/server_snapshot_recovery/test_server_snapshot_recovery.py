# Copyright (c) 2025, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.access.test_employee_consent import create_test_employee
from press.press.doctype.press_notification.press_notification import resource_route
from press.press.doctype.remote_file.test_remote_file import create_test_remote_file
from press.press.doctype.server_snapshot_recovery.server_snapshot_recovery import (
	ServerSnapshotRecovery,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team


@patch("frappe.sendmail", new=Mock())
class TestSnapshotRecoveryBackupDownload(FrappeTestCase):
	"""An employee outside the team, unless a System Manager, cannot download a recovered site's backups."""

	def setUp(self):
		super().setUp()
		self.site = create_test_site(team=create_test_press_admin_team().name)
		self.employee = create_test_employee()
		self.database_backup = create_test_remote_file(file_path="backups/database.sql.gz")
		self.database_backup.db_set("url", "https://example.com/database.sql.gz")
		self.recovery = self.create_recovery(team=self.site.team)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def create_recovery(self, team: str, site: str | None = None) -> ServerSnapshotRecovery:
		"""Rows written without hooks: inserting a recovery would provision servers."""
		snapshot = frappe.get_doc(
			{"doctype": "Server Snapshot", "app_server": self.site.server, "team": team}
		)
		snapshot.db_insert()
		recovery = frappe.get_doc(
			{"doctype": "Server Snapshot Recovery", "team": team, "snapshot": snapshot.name}
		)
		recovery.db_insert()
		recovery.append(
			"sites",
			{
				"site": site or self.site.name,
				"status": "Success",
				"database_remote_file": self.database_backup.name,
				"encryption_key": "secret",
			},
		)
		return recovery

	def download(self, file_type: str = "database"):
		return self.recovery.download_backup(self.site.name, file_type)

	def backup_accesses(self) -> int:
		return frappe.db.count("Site Activity", {"site": self.site.name, "action": "Access Offsite Backups"})

	def test_employee_outside_site_team_cannot_download_recovered_backup(self):
		frappe.set_user(self.employee.user)
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot download the backups"):
			self.download()
		self.assertEqual(self.backup_accesses(), 0)

	def test_employee_outside_site_team_cannot_get_recovered_encryption_key(self):
		frappe.set_user(self.employee.user)
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot download the backups"):
			self.download("encryption_key")
		self.assertEqual(self.backup_accesses(), 0)

	def test_system_manager_outside_site_team_downloads_recovered_backup_and_team_is_notified(self):
		frappe.set_user(create_test_employee("System Manager").user)
		self.assertEqual(self.download(), "https://example.com/database.sql.gz")
		self.assertEqual(self.backup_accesses(), 1)
		notification = {"team": self.site.team, "type": "Resource Access", "reference_name": self.site.name}
		self.assertTrue(frappe.db.exists("Press Notification", notification))

	def test_employee_outside_recovery_team_cannot_download_backup_of_a_gone_site(self):
		recovery = self.create_recovery(team=self.site.team, site="gone.example.com")
		frappe.set_user(self.employee.user)
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot download the backups"):
			recovery.download_backup("gone.example.com", "database")

	def test_member_of_recovery_team_can_download_backup_of_a_gone_site_and_team_is_notified(self):
		recovery = self.create_recovery(team=self.site.team, site="gone.example.com")
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		frappe.set_user(self.employee.user)
		self.assertEqual(
			recovery.download_backup("gone.example.com", "database"), "https://example.com/database.sql.gz"
		)
		self.assertEqual(self.backup_accesses(), 0)
		notification = frappe.get_last_doc("Press Notification", {"type": "Resource Access"})
		self.assertEqual(notification.team, self.site.team)
		self.assertEqual(notification.reference_doctype, "Server")
		self.assertEqual(notification.reference_name, self.site.server)
		self.assertEqual(resource_route(notification), f"servers/{self.site.server}/snapshots")

	def test_member_of_recovery_team_can_get_encryption_key_of_a_gone_site(self):
		recovery = self.create_recovery(team=self.site.team, site="gone.example.com")
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		frappe.set_user(self.employee.user)
		self.assertEqual(recovery.download_backup("gone.example.com", "encryption_key"), "secret")

	def test_employee_member_of_site_team_can_download_recovered_backup_and_team_is_notified(self):
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		frappe.set_user(self.employee.user)
		self.assertEqual(self.download(), "https://example.com/database.sql.gz")
		self.assertEqual(self.backup_accesses(), 1)
		notification = {"team": self.site.team, "type": "Resource Access", "reference_name": self.site.name}
		self.assertTrue(frappe.db.exists("Press Notification", notification))

	def test_team_member_gets_encryption_key_and_team_is_notified(self):
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		frappe.set_user(self.employee.user)
		self.assertEqual(self.download("encryption_key"), "secret")
		self.assertEqual(self.backup_accesses(), 1)

	def test_team_member_download_logs_activity_once(self):
		frappe.set_user(frappe.db.get_value("Team", self.site.team, "user"))
		self.download()
		self.assertEqual(self.backup_accesses(), 1)
