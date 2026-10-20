# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.access import dashboard_access_rules
from press.access.support_access import has_support_access
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_press_admin_team


def create_test_employee() -> Team:
	"""A Frappe Cloud employee: a system user with a team of their own."""
	team = create_test_press_admin_team()
	frappe.get_doc("User", team.user).add_roles("System Manager")
	return team


@patch("frappe.sendmail", new=Mock())
@patch.object(Site, "get_login_sid", new=Mock(return_value="sid"))
class TestEmployeeConsent(FrappeTestCase):
	"""An employee switched into a customer team needs the consent of that team."""

	def setUp(self):
		super().setUp()
		self.site = create_test_site(team=create_test_press_admin_team().name)
		self.employee = create_test_employee()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def act_as_employee_in_site_team(self):
		frappe.set_user(self.employee.user)
		switched = patch("press.access.utils.get_current_team", return_value=self.site.team)
		switched.start()
		self.addCleanup(switched.stop)

	def grant(self, **permissions):
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": self.employee.user,
				"requested_team": self.employee.name,
				"reason": "Debugging",
				"resources": [{"document_type": "Site", "document_name": self.site.name}],
			}
		).insert(ignore_permissions=True)
		allowed_till = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=1)
		frappe.db.set_value(
			"Support Access",
			access.name,
			{"status": "Accepted", "access_allowed_till": allowed_till, **permissions},
		)

	def site_rules(self) -> frappe._dict:
		data = frappe._dict(doctype="Site", name=self.site.name, team=self.site.team)
		return dashboard_access_rules(data)

	def test_employee_switched_into_site_team_cannot_login_as_administrator_without_consent(self):
		self.act_as_employee_in_site_team()
		with self.assertRaisesRegex(frappe.PermissionError, "You do not have permission"):
			Site("Site", self.site.name).login()

	def test_employee_with_login_grant_can_login_as_administrator(self):
		self.grant(login_as_administrator=1)
		self.act_as_employee_in_site_team()
		self.assertEqual(Site("Site", self.site.name).login(), "sid")

	def test_employee_grant_without_login_permission_does_not_allow_login_as_administrator(self):
		self.grant(site_domains=1)
		self.act_as_employee_in_site_team()
		with self.assertRaisesRegex(frappe.PermissionError, "You do not have permission"):
			Site("Site", self.site.name).login()

	def test_employee_who_is_member_of_site_team_can_login_as_administrator_without_grant(self):
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		self.act_as_employee_in_site_team()
		self.assertEqual(Site("Site", self.site.name).login(), "sid")

	def test_administrator_can_login_as_administrator_without_grant(self):
		frappe.set_user("Administrator")
		self.assertEqual(Site("Site", self.site.name).login(), "sid")

	def test_employee_dashboard_hides_login_and_domains_without_consent(self):
		self.act_as_employee_in_site_team()
		rules = self.site_rules()
		self.assertFalse(rules.actions_access["Login As Administrator"])
		self.assertFalse(rules.tabs_access["Domains"])

	def test_employee_dashboard_shows_login_and_domains_with_consent(self):
		self.grant(login_as_administrator=1, site_domains=1)
		self.act_as_employee_in_site_team()
		rules = self.site_rules()
		self.assertTrue(rules.actions_access["Login As Administrator"])
		self.assertTrue(rules.tabs_access["Domains"])

	def test_employee_dashboard_keeps_tabs_that_need_no_consent(self):
		self.act_as_employee_in_site_team()
		rules = self.site_rules()
		self.assertTrue(rules.tabs_access["Backups"])
		self.assertTrue(rules.tabs_access["Actions"])
		self.assertTrue(rules.actions_access["View in Desk"])

	def test_employee_reads_site_of_another_team_without_consent(self):
		self.act_as_employee_in_site_team()
		self.assertTrue(has_support_access("Site", self.site.name))

	def test_support_agent_dashboard_still_hides_backups_tab(self):
		agent = create_test_press_admin_team()
		frappe.get_doc("User", agent.user).add_roles("Press Support Agent")
		frappe.set_user(agent.user)
		self.assertFalse(self.site_rules().tabs_access["Backups"])
