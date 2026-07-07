# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_team


class TestPressRole(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Press Role")
		self.team_user = create_user("team@example.com")
		self.team = create_test_team(self.team_user.email)
		self.team.user = "Administrator"
		self.team_member = create_user("user123@example.com")
		self.team.append("team_members", {"user": self.team_member.name})
		self.team.save()
		self.external_team_member = create_user("external@example.com")
		self.admin_perm_role = create_permission_role(self.team.name)
		self.perm_role = create_permission_role(self.team.name)
		self.perm_role2 = create_permission_role(self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.delete_doc("Press Role", self.perm_role.name, force=True)
		frappe.delete_doc("Press Role", self.perm_role2.name, force=True)
		frappe.delete_doc("Team", self.team.name, force=True)
		frappe.delete_doc("User", self.team_member.name, force=True)
		frappe.delete_doc("User", self.team_user.name, force=True)
		frappe.local._current_team = None

	@property
	def team_doc(self):
		return frappe.get_doc("Team", self.team.name)

	def test_add_user(self):
		self.perm_role.add_user(self.team_member.name)
		perm_role_users = get_users(self.perm_role)
		perm_role_user_exists = any(
			self.team_member.name == perm_role_user.user for perm_role_user in perm_role_users
		)
		self.assertTrue(perm_role_user_exists)
		self.assertRaises(frappe.ValidationError, self.perm_role.add_user, self.team_member.name)

	def test_remove_user(self):
		self.perm_role.add_user(self.team_member.name)
		self.perm_role.remove_user(self.team_member.name)
		perm_role_users = get_users(self.perm_role)
		perm_role_user_exists = any(
			self.team_member.name == perm_role_user.user for perm_role_user in perm_role_users
		)
		self.assertFalse(perm_role_user_exists)
		self.assertRaises(frappe.ValidationError, self.perm_role.remove_user, self.team_member.name)

	def test_delete_role_unsets_press_role_on_account_requests(self):
		"""Invites keep the selected role in Account Request.press_role even
		after acceptance. Deleting the role must unset those references,
		otherwise the link check blocks the deletion forever."""
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"team": self.team.name,
				"email": "invitee@example.com",
				"invited_by": self.team.user,
				"press_role": self.perm_role.name,
			}
		).insert(ignore_permissions=True)

		frappe.delete_doc("Press Role", self.perm_role.name)

		self.assertFalse(frappe.db.exists("Press Role", self.perm_role.name))
		self.assertFalse(frappe.db.get_value("Account Request", account_request.name, "press_role"))

	def test_add_resource_rejects_cross_team_document(self):
		other_team = create_test_team()
		self.addCleanup(frappe.delete_doc, "Team", other_team.name, force=True)
		subdomain = frappe.generate_hash(length=8)
		site_name = f"{subdomain}.frappe.cloud"
		create_test_site_record(site_name, subdomain, other_team.name)
		self.addCleanup(lambda: frappe.db.sql("DELETE FROM `tabSite` WHERE name = %s", (site_name,)))

		with self.assertRaises(frappe.ValidationError):
			self.perm_role.add_resource([{"document_type": "Site", "document_name": site_name}])

		self.perm_role.reload()
		self.assertFalse(any(r.document_name == site_name for r in self.perm_role.resources))


# utils
def create_permission_role(team, allow_site_creation=0):
	doc = frappe.new_doc("Press Role")
	doc.title = make_autoname("Test-Role-.###")
	doc.team = team
	doc.allow_site_creation = allow_site_creation
	doc.save()

	return doc


def create_user(email):
	if frappe.db.exists("User", email):
		return frappe.get_doc("User", email)
	user = frappe.new_doc("User")
	user.email = email
	user.first_name = email.split("@")[0]
	user.save()
	return user


def get_users(role):
	return role.users


def create_test_site_record(name, subdomain, team_name):
	"""Insert a bare Site row without running any hooks. For use in tests only."""
	frappe.db.sql(
		"INSERT INTO `tabSite`"
		" (name, team, subdomain, status, server, bench, cluster, `group`)"
		" VALUES (%s, %s, %s, 'Active', 'test-server', 'test-bench', 'Default', 'test-group')",
		(name, team_name, subdomain),
	)
