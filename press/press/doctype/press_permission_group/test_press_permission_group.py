# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.team.test_team import create_test_team

from press.press.doctype.press_permission_group.press_permission_group import (
	get_all_restrictable_methods,
	has_method_permission,
)


class TestPressPermissionGroup(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Press Permission Group")
		self.team_user = create_user("team@example.com")
		self.team = create_test_team(self.team_user.email)
		self.team_member = create_user("user123@example.com")
		self.team.append("team_members", {"user": self.team_member.name})
		self.team.save()
		self.perm_group = create_permission_group(self.team.name)
		self.perm_group2 = create_permission_group(self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.delete_doc("Press Permission Group", self.perm_group.name, force=True)
		frappe.delete_doc("Press Permission Group", self.perm_group2.name, force=True)
		frappe.delete_doc("Team", self.team.name, force=True)
		frappe.delete_doc("User", self.team_member.name, force=True)
		frappe.delete_doc("User", self.team_user.name, force=True)
		frappe.local._current_team = None

	def test_add_user(self):
		self.perm_group.add_user(self.team_member.name)
		perm_group_users = self.perm_group.get_users()
		perm_group_user_exists = any(
			self.team_member.name == pg_user.name for pg_user in perm_group_users
		)
		self.assertTrue(perm_group_user_exists)
		self.assertRaises(
			frappe.ValidationError, self.perm_group.add_user, self.team_member.name
		)

	def test_remove_user(self):
		self.perm_group.add_user(self.team_member.name)
		self.perm_group.remove_user(self.team_member.name)
		perm_group_users = self.perm_group.get_users()
		perm_group_user_exists = any(
			self.team_member.name == pg_user.name for pg_user in perm_group_users
		)
		self.assertFalse(perm_group_user_exists)
		self.assertRaises(
			frappe.ValidationError, self.perm_group.remove_user, self.team_member.name
		)

	def test_update_permissions(self):
		frappe.set_user("Administrator")
		self.perm_group.add_user(self.team_member.name)
		self.perm_group.update_permissions({"Site": {"*": {"*": True}}})
		frappe.set_user(self.team_member.name)
		self.assertEqual(has_method_permission("Site", "site1.test", "reinstall"), True)

		frappe.set_user("Administrator")
		self.perm_group.update_permissions(
			{"Site": {"site1.test": {"*": True, "reinstall": False}}}
		)
		frappe.set_user(self.team_member.name)
		self.assertEqual(has_method_permission("Site", "site1.test", "reinstall"), False)

	def test_update_permissions_with_invalid_doctype(self):
		frappe.set_user("Administrator")
		self.assertRaises(
			frappe.ValidationError,
			self.perm_group.update_permissions,
			{"Invalid Doctype": {"*": {"*": True}}},
		)

	def test_update_permissions_with_invalid_method(self):
		frappe.set_user("Administrator")
		self.assertRaises(
			frappe.ValidationError,
			self.perm_group.update_permissions,
			{"Site": {"*": {"invalid_method": True}}},
		)

	def test_unrestricted_method_should_be_allowed(self):
		frappe.set_user("Administrator")
		self.perm_group.add_user(self.team_member.name)
		frappe.set_user(self.team_member.name)
		self.assertEqual(has_method_permission("Site", "site1.test", "create"), True)

	def test_most_permissive_permission_should_be_allowed(self):
		frappe.set_user("Administrator")
		self.perm_group2.add_user(self.team_member.name)
		self.perm_group2.update_permissions({"Site": {"*": {"*": False}}})
		self.perm_group.add_user(self.team_member.name)
		self.perm_group.update_permissions({"Site": {"*": {"*": True}}})
		frappe.set_user(self.team_member.name)
		self.assertEqual(has_method_permission("Site", "site1.test", "reinstall"), True)

	def test_specific_permission_should_be_allowed(self):
		frappe.set_user("Administrator")
		self.perm_group2.add_user(self.team_member.name)
		self.perm_group2.update_permissions({"Site": {"*": {"*": False}}})
		self.perm_group.add_user(self.team_member.name)
		self.perm_group.update_permissions({"Site": {"site1.test": {"reinstall": True}}})
		frappe.set_user(self.team_member.name)
		self.assertEqual(has_method_permission("Site", "site1.test", "reinstall"), True)

	def test_get_all_document_permissions(self):
		# Test case 1: User belongs to the permission group
		frappe.set_user("Administrator")
		self.perm_group.add_user(self.team_member.name)
		self.perm_group.update_permissions({"Site": {"*": {"*": True}}})

		site = frappe.new_doc("Site")
		site.name = "site1.test"
		site.team = self.team.name
		site.db_insert()

		frappe.set_user(self.team_member.name)
		frappe.local._current_team = self.team
		permissions = self.perm_group.get_all_document_permissions("Site")
		self.assertEqual(len(permissions), 1)
		self.assertEqual(permissions[0]["document_type"], "Site")
		self.assertEqual(permissions[0]["document_name"], "site1.test")
		site_restrictable_methods = get_all_restrictable_methods("Site")
		self.assertEqual(len(permissions[0]["permissions"]), len(site_restrictable_methods))

		# Test case 2: User does not belong to the permission group
		frappe.set_user("user@example.com")
		self.assertRaises(
			frappe.ValidationError, self.perm_group.get_all_document_permissions, "Site"
		)

		# Test case 3: Invalid restrictable doctype
		frappe.set_user("Administrator")
		self.assertRaises(
			frappe.ValidationError,
			self.perm_group.get_all_document_permissions,
			"InvalidDoctype",
		)

		# Test case 4: No restrictable methods for the doctype
		self.assertRaises(
			frappe.ValidationError, self.perm_group.get_all_document_permissions, "DocType2"
		)


# utils
def create_permission_group(team):
	doc = frappe.new_doc("Press Permission Group")
	doc.title = "Test Group"
	doc.team = team
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
