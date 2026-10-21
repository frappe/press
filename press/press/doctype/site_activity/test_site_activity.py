# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team

if TYPE_CHECKING:
	from press.press.doctype.site_activity.site_activity import SiteActivity


def create_test_site_activity(site: str, action: str, reason: str | None = None) -> SiteActivity:
	return frappe.get_doc(
		{  # type: ignore
			"doctype": "Site Activity",
			"site": site,
			"action": action,
			"reason": reason,
			"team": frappe.db.get_value("Site", site, "team"),
		}
	).insert()


class TestSiteActivity(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.site = create_test_site(team=create_test_press_admin_team().name)
		sendmail = patch("press.press.doctype.press_notification.press_notification.frappe.sendmail")
		self.sendmail = sendmail.start()
		self.addCleanup(sendmail.stop)

	def tearDown(self):
		frappe.db.rollback()

	def resource_access_notifications(self) -> list:
		return frappe.get_all(
			"Press Notification",
			{"type": "Resource Access", "reference_name": self.site.name},
			["team", "title", "message"],
		)

	def test_admin_login_notifies_site_team_in_dashboard_and_by_email(self):
		create_test_site_activity(self.site.name, "Login as Administrator", reason="Fixing a report")
		notification = self.resource_access_notifications()[0]
		self.assertEqual(notification.team, self.site.team)
		self.assertEqual(notification.title, f"Administrator login to {self.site.name}")
		self.assertIn("Reason: Fixing a report", notification.message)
		self.assertEqual(self.sendmail.call_args.kwargs["template"], "resource_access")

	def test_admin_login_without_reason_still_notifies_site_team(self):
		create_test_site_activity(self.site.name, "Login as Administrator")
		self.assertEqual(len(self.resource_access_notifications()), 1)
		self.sendmail.assert_called_once()

	def test_admin_login_reason_is_escaped_in_notification(self):
		create_test_site_activity(self.site.name, "Login as Administrator", reason="<img src=x>")
		message = self.resource_access_notifications()[0].message
		self.assertNotIn("<img", message)
		self.assertIn("&lt;img", message)

	def test_backup_access_notifies_site_team(self):
		create_test_site_activity(self.site.name, "Access Offsite Backups")
		notification = self.resource_access_notifications()[0]
		self.assertEqual(notification.title, f"Backup of {self.site.name} accessed")

	def test_other_site_activity_does_not_notify_site_team(self):
		create_test_site_activity(self.site.name, "Clear Cache")
		self.assertEqual(self.resource_access_notifications(), [])
		self.sendmail.assert_not_called()
