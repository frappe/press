# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.press_user_permission.press_user_permission import (
	has_user_permission,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_team


class TestPressUserPermission(FrappeTestCase):
	def setUp(self):
		self.team = create_test_team()
		self.site = create_test_site(subdomain="testpermsite")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_press_user_permission(self):
		self.assertFalse(has_user_permission("Site", self.site.name, "press.api.site.login"))

		frappe.get_doc(
			doctype="Press User Permission",
			type="User",
			user=frappe.session.user,
			document_type="Site",
			document_name=self.site.name,
			action="press.api.site.login",
		).insert(ignore_permissions=True)

		self.assertTrue(has_user_permission("Site", self.site.name, "press.api.site.login"))
		self.assertFalse(
			has_user_permission("Site", self.site.name, "press.api.site.migrate")
		)

	def test_press_group_permission(self):
		group = frappe.get_doc(
			doctype="Press Permission Group", team=self.team.name, title="Test Group"
		)
		group.append("users", {"user": frappe.session.user})
		group.insert(ignore_permissions=True)

		frappe.get_doc(
			doctype="Press User Permission",
			type="Group",
			group=group.name,
			document_type="Site",
			document_name=self.site.name,
			action="press.api.site.overview",
		).insert(ignore_permissions=True)

		self.assertTrue(
			has_user_permission(
				"Site", self.site.name, "press.api.site.overview", groups=[group.name]
			)
		)
		self.assertFalse(
			has_user_permission(
				"Site", self.site.name, "press.api.site.migrate", groups=[group.name]
			)
		)

	def test_press_config_permission(self):
		perms = {
			"global": {
				"Site": {"*": "press.api.site.login"},
			},
			"restricted": {"Site": {"test.frappe.dev": "press.api.site.migrate"}},
		}
		frappe.get_doc(
			doctype="Press User Permission",
			type="Config",
			config=frappe.as_json(perms),
			user=frappe.session.user,
		).insert(ignore_permissions=True)

		self.assertTrue(has_user_permission("Site", self.site.name, "press.api.site.login"))
		self.assertFalse(
			has_user_permission("Site", "sometest.frappe.dev", "press.api.site.restore")
		)
		self.assertFalse(
			has_user_permission("Site", "test.frappe.dev", "press.api.site.migrate")
		)
		self.assertTrue(
			has_user_permission("Site", "test.frappe.dev", "press.api.site.login")
		)
