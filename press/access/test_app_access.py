# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests import IntegrationTestCase

from press.access import dashboard_access_rules
from press.access.test_employee_consent import create_test_employee
from press.api.app import new as new_app_in_group
from press.api.bench import add_apps, apply_patch, ensure_can_manage_apps
from press.api.client import get_list
from press.api.tests.test_client import sign_in_as
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team

REFUSED = "You do not have permission to perform this action"


@patch("frappe.sendmail", new=Mock())
class IntegrationTestSupportAgentAppAccess(IntegrationTestCase):
	"""A support agent with a grant sees the apps of a site or a bench group, but does not change them."""

	def setUp(self):
		super().setUp()
		self.owner_team = create_test_press_admin_team()
		self.site = create_test_site(team=self.owner_team.name)
		self.group = ReleaseGroup("Release Group", self.site.group)
		self.agent_team = create_test_press_admin_team()
		frappe.get_doc("User", self.agent_team.user).add_roles("Press Employee")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def grant(self, document_type: str, document_name: str):
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": self.agent_team.user,
				"requested_team": self.agent_team.name,
				"reason": "Debugging an app",
				"resources": [{"document_type": document_type, "document_name": document_name}],
			}
		).insert(ignore_permissions=True)
		allowed_till = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=1)
		frappe.db.set_value(
			"Support Access", access.name, {"status": "Accepted", "access_allowed_till": allowed_till}
		)

	def apps_listed_by(self, team, doctype: str, parenttype: str, parent: str) -> list[str]:
		sign_in_as(team)
		filters = {"parenttype": parenttype, "parent": parent}
		return sorted(app.get("app") or app.get("name") for app in get_list(doctype, filters=filters))

	def site_apps_listed_by(self, team) -> list[str]:
		return self.apps_listed_by(team, "Site App", "Site", self.site.name)

	def group_apps_listed_by(self, team) -> list[str]:
		return self.apps_listed_by(team, "Release Group App", "Release Group", self.group.name)

	def rules_seen_by_agent(self, doctype: str, name: str, team: str) -> frappe._dict:
		sign_in_as(self.agent_team)
		return dashboard_access_rules(frappe._dict(doctype=doctype, name=name, team=team))

	def test_site_grant_lets_support_agent_list_the_installed_apps_of_the_site(self):
		expected = self.site_apps_listed_by(self.owner_team)
		self.assertIn("frappe", expected)
		self.grant("Site", self.site.name)
		self.assertEqual(self.site_apps_listed_by(self.agent_team), expected)

	def test_support_agent_without_a_grant_cannot_list_the_installed_apps_of_the_site(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Not permitted"):
			self.site_apps_listed_by(self.agent_team)

	def test_another_customer_team_cannot_list_the_installed_apps_of_the_site(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Not permitted"):
			self.site_apps_listed_by(create_test_press_admin_team())

	def test_support_agent_dashboard_shows_the_site_apps_tab_but_not_the_app_actions(self):
		self.grant("Site", self.site.name)
		rules = self.rules_seen_by_agent("Site", self.site.name, self.site.team)
		self.assertNotIn("Apps", rules.tabs_access)
		self.assertFalse(rules.actions_access["Manage Apps"])

	def test_site_owner_dashboard_does_not_restrict_the_app_actions(self):
		sign_in_as(self.owner_team)
		data = frappe._dict(doctype="Site", name=self.site.name, team=self.site.team)
		self.assertEqual(dashboard_access_rules(data).actions_access, {})

	def test_support_agent_with_a_site_grant_cannot_install_an_app(self):
		self.grant("Site", self.site.name)
		sign_in_as(self.agent_team)
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			Site("Site", self.site.name).install_app("erpnext")

	def test_support_agent_with_a_site_grant_cannot_uninstall_an_app(self):
		self.grant("Site", self.site.name)
		sign_in_as(self.agent_team)
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			Site("Site", self.site.name).uninstall_app("frappe")
		self.assertIn("frappe", [app.app for app in Site("Site", self.site.name).apps])

	def test_group_grant_lets_support_agent_list_the_apps_of_the_bench_group(self):
		expected = self.group_apps_listed_by(frappe.get_doc("Team", self.group.team))
		self.assertIn("frappe", expected)
		self.grant("Release Group", self.group.name)
		self.assertEqual(self.group_apps_listed_by(self.agent_team), expected)

	def test_support_agent_dashboard_hides_the_app_actions_of_the_bench_group(self):
		self.grant("Release Group", self.group.name)
		rules = self.rules_seen_by_agent("Release Group", self.group.name, self.group.team)
		self.assertFalse(rules.actions_access["Manage Apps"])

	def test_support_agent_with_a_group_grant_cannot_remove_an_app_or_fetch_its_updates(self):
		self.grant("Release Group", self.group.name)
		sign_in_as(self.agent_team)
		group = ReleaseGroup("Release Group", self.group.name)
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			group.remove_app("frappe")
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			group.fetch_latest_app_update("frappe")
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			group.change_app_branch("frappe", "develop")
		self.assertIn("frappe", [app.app for app in ReleaseGroup("Release Group", self.group.name).apps])

	def test_support_agent_with_a_group_grant_cannot_add_an_app_or_apply_a_patch(self):
		self.grant("Release Group", self.group.name)
		sign_in_as(self.agent_team)
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			add_apps(name=self.group.name, apps=[{"app": "erpnext", "source": "any"}])
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			apply_patch(release_group=self.group.name, app="frappe", patch_config={})

	def test_support_agent_with_a_group_grant_cannot_add_a_new_app_from_github(self):
		self.grant("Release Group", self.group.name)
		sign_in_as(self.agent_team)
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			new_app_in_group({"name": "erpnext", "group": self.group.name})

	def test_another_customer_team_cannot_add_a_new_app_to_the_bench_group(self):
		sign_in_as(create_test_press_admin_team())
		with self.assertRaisesRegex(frappe.PermissionError, REFUSED):
			new_app_in_group({"name": "erpnext", "group": self.group.name})

	def test_bench_group_owner_can_still_manage_the_apps_of_the_group(self):
		sign_in_as(frappe.get_doc("Team", self.group.team))
		ensure_can_manage_apps(self.group.name)

	def test_employee_outside_the_team_can_still_manage_apps_and_list_site_apps(self):
		employee = create_test_employee()
		frappe.set_user(employee.user)
		ensure_can_manage_apps(self.group.name)
		expected = self.site_apps_listed_by(self.owner_team)
		self.assertEqual(self.site_apps_listed_by(employee), expected)
