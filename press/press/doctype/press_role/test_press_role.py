# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.site.test_site import create_test_site


class TestPressRole(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Press Role")
		self.team_user = create_user("team@example.com")
		self.team = create_test_team(self.team_user.email)
		self.team_member = create_user("user123@example.com")
		self.team.append("team_members", {"user": self.team_member.name})
		self.team.save()
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

	def test_add_user(self):
		self.perm_role.add_user(self.team_member.name)
		perm_role_users = get_users(self.perm_role)
		perm_role_user_exists = any(
			self.team_member.name == perm_role_user.user for perm_role_user in perm_role_users
		)
		self.assertTrue(perm_role_user_exists)
		self.assertRaises(
			frappe.ValidationError, self.perm_role.add_user, self.team_member.name
		)

	def test_remove_user(self):
		self.perm_role.add_user(self.team_member.name)
		self.perm_role.remove_user(self.team_member.name)
		perm_role_users = get_users(self.perm_role)
		perm_role_user_exists = any(
			self.team_member.name == perm_role_user.user for perm_role_user in perm_role_users
		)
		self.assertFalse(perm_role_user_exists)
		self.assertRaises(
			frappe.ValidationError, self.perm_role.remove_user, self.team_member.name
		)

	def test_delete_role(self):
		perm = frappe.new_doc("Press Role Permission")
		perm.role = self.perm_role.name
		perm.team = self.team.name
		perm.save()

		self.perm_role.delete()
		self.assertFalse(frappe.db.exists("Press Role", self.perm_role.name))
		self.assertFalse(
			frappe.db.get_all("Press Role Permission", filters={"role": self.perm_role.name})
		)

	def test_delete_permissions(self):
		perm = frappe.new_doc("Press Role Permission")
		perm.role = self.perm_role.name
		perm.team = self.team.name
		perm.save()

		permissions = frappe.get_all(
			"Press Role Permission", filters={"role": self.perm_role.name}, pluck="name"
		)
		self.perm_role.delete_permissions(permissions)
		self.assertFalse(
			frappe.db.get_all("Press Role Permission", filters={"role": self.perm_role.name})
		)

	def test_get_list_with_permissions(self):
		from press.api.client import get_list

		frappe.set_user("Administrator")
		site1 = create_test_site(team=self.team.name)
		site2 = create_test_site(team=self.team.name)
		self.perm_role.add_user(self.team_user.name)
		self.perm_role2.add_user(self.team_user.name)
		frappe.set_user(self.team_user.name)

		# no permissions added should show all records
		self.assertCountEqual(get_list("Site"), [{"name": site1.name}, {"name": site2.name}])
		return
		frappe.set_user("Administrator")
		perm = frappe.new_doc("Press Role Permission")
		perm.role = self.perm_role.name
		perm.team = self.team.name
		perm.site = site1.name
		perm.save()
		frappe.set_user(self.team_user.name)

		# permission for site1 added in the role
		self.assertEqual(get_list("Site"), [{"name": site1.name}])

		frappe.set_user("Administrator")
		perm2 = frappe.new_doc("Press Role Permission")
		perm2.role = self.perm_role2.name
		perm2.team = self.team.name
		perm2.site = site2.name
		perm2.save()
		frappe.set_user(self.team_user.name)

		# permission for site2 added in another role
		self.assertCountEqual(get_list("Site"), [{"name": site1.name}, {"name": site2.name}])

	def test_get_with_permissions(self):
		from press.api.client import get

		frappe.set_user("Administrator")
		site = create_test_site(team=self.team.name)
		site2 = create_test_site(team=self.team.name)
		self.perm_role.add_user(self.team_user.name)
		frappe.set_user(self.team_user.name)

		# no permissions added should show all records
		self.assertEqual(get("Site", site.name).name, site.name)
		self.assertEqual(get("Site", site2.name).name, site2.name)

		frappe.set_user("Administrator")
		perm = frappe.new_doc("Press Role Permission")
		perm.role = self.perm_role.name
		perm.team = self.team.name
		perm.site = site.name
		perm.save()
		frappe.set_user(self.team_user.name)

		# permission for site added in the role
		self.assertEqual(get("Site", site.name).name, site.name)
		with self.assertRaises(Exception):
			get("Site", site2.name)


# utils
def create_permission_role(team):
	doc = frappe.new_doc("Press Role")
	doc.title = "Test Role"
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


def get_users(role):
	return role.users
