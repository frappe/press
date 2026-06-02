# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

if TYPE_CHECKING:
	from press.press.doctype.site_activity.site_activity import SiteActivity


def create_test_site_activity(site: str, action: str) -> SiteActivity:
	return frappe.get_doc(
		{  # type: ignore
			"doctype": "Site Activity",
			"site": site,
			"action": action,
			"team": frappe.db.get_value("Site", site, "team"),
		}
	).insert()


class TestSiteActivityAfterInsert(FrappeTestCase):
	"""after_insert() sends email for specific actions when conditions are met."""

	_MODULE = "press.press.doctype.site_activity.site_activity"

	def _make_doc(self, action, team="team-1", reason=None, site="my.site.com"):
		from unittest.mock import MagicMock

		doc = MagicMock()
		doc.action = action
		doc.team = team
		doc.reason = reason
		doc.site = site
		doc.owner = "admin@example.com"
		doc.doctype = "Site Activity"
		doc.name = "SA-001"
		return doc

	def test_administrator_team_skips_email(self):
		"""after_insert() is a no-op when team is 'Administrator'."""
		from unittest.mock import patch

		from press.press.doctype.site_activity.site_activity import SiteActivity

		doc = self._make_doc("Login as Administrator", team="Administrator", reason="testing")
		with patch(f"{self._MODULE}.frappe.sendmail") as mock_mail:
			SiteActivity.after_insert(doc)
		mock_mail.assert_not_called()

	def test_login_as_administrator_with_reason_sends_email(self):
		"""'Login as Administrator' action with a reason triggers an email to recipients."""
		from unittest.mock import patch

		from press.press.doctype.site_activity.site_activity import SiteActivity

		doc = self._make_doc("Login as Administrator", reason="Debugging issue")
		with (
			patch(f"{self._MODULE}.get_communication_info", return_value=["owner@example.com"]),
			patch(f"{self._MODULE}.frappe.sendmail") as mock_mail,
		):
			SiteActivity.after_insert(doc)
		mock_mail.assert_called_once()

	def test_login_as_administrator_without_reason_skips_email(self):
		"""'Login as Administrator' without a reason does NOT send an email."""
		from unittest.mock import patch

		from press.press.doctype.site_activity.site_activity import SiteActivity

		doc = self._make_doc("Login as Administrator", reason=None)
		with (
			patch(f"{self._MODULE}.get_communication_info", return_value=["owner@example.com"]),
			patch(f"{self._MODULE}.frappe.sendmail") as mock_mail,
		):
			SiteActivity.after_insert(doc)
		mock_mail.assert_not_called()

	def test_login_as_administrator_no_recipients_skips_email(self):
		"""'Login as Administrator' with a reason but no recipients skips email."""
		from unittest.mock import patch

		from press.press.doctype.site_activity.site_activity import SiteActivity

		doc = self._make_doc("Login as Administrator", reason="Testing")
		with (
			patch(f"{self._MODULE}.get_communication_info", return_value=[]),
			patch(f"{self._MODULE}.frappe.sendmail") as mock_mail,
		):
			SiteActivity.after_insert(doc)
		mock_mail.assert_not_called()

	def test_disable_monitoring_with_reason_sends_email(self):
		"""'Disable Monitoring And Alerts' with reason sends a monitoring-disabled email."""
		from unittest.mock import patch

		from press.press.doctype.site_activity.site_activity import SiteActivity

		doc = self._make_doc("Disable Monitoring And Alerts", reason="Cost saving")
		with (
			patch(f"{self._MODULE}.get_communication_info", return_value=["owner@example.com"]),
			patch(f"{self._MODULE}.frappe.sendmail") as mock_mail,
		):
			SiteActivity.after_insert(doc)
		mock_mail.assert_called_once()

	def test_other_action_does_not_send_email(self):
		"""Actions that are not 'Login as Administrator' or 'Disable Monitoring And Alerts' send no email."""
		from unittest.mock import patch

		from press.press.doctype.site_activity.site_activity import SiteActivity

		for action in ("Backup", "Migrate", "Archive", "Restore"):
			doc = self._make_doc(action, reason="some reason")
			with (
				patch(f"{self._MODULE}.get_communication_info", return_value=["owner@example.com"]),
				patch(f"{self._MODULE}.frappe.sendmail") as mock_mail,
			):
				SiteActivity.after_insert(doc)
			mock_mail.assert_not_called(), f"Unexpected email for action={action}"
