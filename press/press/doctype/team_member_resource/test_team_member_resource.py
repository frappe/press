# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_role.test_press_role import (
	create_permission_role,
	create_test_site_record,
	create_user,
)
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.team_member_resource.team_member_resource import sync_press_role


class TestSyncPressRole(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Press Role")
		self.team = create_test_team()
		self.member = create_user(frappe.mock("email"))
		self.team.append("team_members", {"user": self.member.name})
		self.team.save()
		self.role = create_permission_role(self.team.name)
		self.role.append("users", {"user": self.member.name})
		self.role.save()
		self.test_sites = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for site_name in self.test_sites:
			frappe.db.sql("DELETE FROM `tabSite` WHERE name = %s", (site_name,))
		frappe.db.delete("Team Member Resource", {"team": self.team.name})
		frappe.delete_doc("Press Role", self.role.name, force=True)
		frappe.delete_doc("Team", self.team.name, force=True)
		frappe.delete_doc("User", self.member.name, force=True)
		frappe.local._current_team = None

	def create_site(self, team_name):
		subdomain = frappe.generate_hash(length=8)
		name = f"{subdomain}.frappe.cloud"
		create_test_site_record(name, subdomain, team_name)
		self.test_sites.append(name)
		return name

	def add_role_resource(self, document_type, document_name):
		resource = self.role.append(
			"resources",
			{
				"document_type": document_type,
				"document_name": document_name,
			},
		)
		resource.db_insert()
		self.role.reload()

	def test_sync_skips_stale_resource(self):
		other_team = create_test_team()
		self.addCleanup(frappe.delete_doc, "Team", other_team.name, force=True)
		stale_site = self.create_site(other_team.name)
		self.add_role_resource("Site", stale_site)

		sync_press_role(self.role)

		self.assertFalse(
			frappe.db.exists(
				{"doctype": "Team Member Resource", "team": self.team.name, "document_name": stale_site}
			)
		)

	def test_sync_creates_team_member_resource(self):
		valid_site = self.create_site(self.team.name)
		self.add_role_resource("Site", valid_site)

		sync_press_role(self.role)

		self.assertTrue(
			frappe.db.exists(
				{
					"doctype": "Team Member Resource",
					"team": self.team.name,
					"user": self.member.name,
					"document_type": "Site",
					"document_name": valid_site,
				}
			)
		)
