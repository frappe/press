# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_team


class TestPressRole(FrappeTestCase):
	def setUp(self):
		super().setUp()

		frappe.set_user("Administrator")
		frappe.db.delete("Press Role")
		self.team_user = create_user("team@example.com")
		self.team = create_test_team(self.team_user.email)
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

	def test_delete_role(self):
		perm = frappe.new_doc("Press Role Permission")
		perm.role = self.perm_role.name
		perm.team = self.team.name
		perm.save()

		self.perm_role.delete()
		self.assertFalse(frappe.db.exists("Press Role", self.perm_role.name))
		self.assertFalse(frappe.db.get_all("Press Role Permission", filters={"role": self.perm_role.name}))

	def test_delete_permissions(self):
		perm = frappe.new_doc("Press Role Permission")
		perm.role = self.perm_role.name
		perm.team = self.team.name
		perm.save()

		permissions = frappe.get_all(
			"Press Role Permission", filters={"role": self.perm_role.name}, pluck="name"
		)
		self.perm_role.delete_permissions(permissions)
		self.assertFalse(frappe.db.get_all("Press Role Permission", filters={"role": self.perm_role.name}))

	def test_get_list_with_permissions(self):
		from press.api.client import get_list

		frappe.set_user("Administrator")
		site1 = create_test_site(team=self.team.name)
		site2 = create_test_site(team=self.team.name)
		self.perm_role.add_user(self.team_member.name)
		self.perm_role2.add_user(self.team_member.name)
		frappe.set_user(self.team_member.name)
		# Important because _get_current_team doesn't resolve team for team members in background jobs / function call
		frappe.local._current_team = self.team_doc

		# no permissions added should show all records
		self.assertCountEqual(get_list("Site"), [])
		frappe.set_user("Administrator")
		perm = frappe.new_doc("Press Role Permission")
		perm.role = self.perm_role.name
		perm.team = self.team.name
		perm.site = site1.name
		perm.save()
		frappe.set_user(self.team_member.name)
		# Important because _get_current_team doesn't resolve team for team members in background jobs / function call
		frappe.local._current_team = self.team_doc

		# permission for site1 added in the role
		self.assertEqual(get_list("Site"), [{"name": site1.name, "bench": site1.bench}])

		frappe.set_user("Administrator")
		perm2 = frappe.new_doc("Press Role Permission")
		perm2.role = self.perm_role2.name
		perm2.team = self.team.name
		perm2.site = site2.name
		perm2.save()
		frappe.set_user(self.team_member.name)
		# Important because _get_current_team doesn't resolve team for team members in background jobs / function call
		frappe.local._current_team = self.team_doc

		# permission for site2 added in another role
		self.assertCountEqual(
			get_list("Site"),
			[
				{"name": site1.name, "bench": site1.bench},
				{"name": site2.name, "bench": site2.bench},
			],
		)

	def test_get_with_permissions(self):
		from press.api.client import get

		frappe.set_user("Administrator")
		site = create_test_site(team=self.team.name)
		site2 = create_test_site(team=self.team.name)
		self.perm_role.add_user(self.team_member.name)
		frappe.set_user(self.team_member.name)
		# Important because _get_current_team doesn't resolve team for team members in background jobs / function call
		frappe.local._current_team = self.team_doc

		# no permissions added should throw exception for both sites
		self.assertRaises(Exception, get, "Site", site.name)
		self.assertRaises(Exception, get, "Site", site2.name)

		frappe.set_user("Administrator")
		perm = frappe.new_doc("Press Role Permission")
		perm.role = self.perm_role.name
		perm.team = self.team.name
		perm.site = site.name
		perm.save()
		frappe.set_user(self.team_member.name)
		# Important because _get_current_team doesn't resolve team for team members in background jobs / function call
		frappe.local._current_team = self.team_doc

		# permission for site added in the role
		self.assertEqual(get("Site", site.name).name, site.name)
		self.assertRaises(Exception, get, "Site", site2.name)

	def test_newly_created_sites_are_permitted_for_roles_with_allow_site_creation_and_existing_perms(
		self,
	):
		role = create_permission_role(self.team.name, allow_site_creation=1)

		# admin have insert perms (fw level), so adding admin as role user
		# Add Administrator to team_members first so that the role can be created
		self.team.append("team_members", {"user": "Administrator"})
		self.team.save()

		role.add_user("Administrator")
		role.add_user(self.team_member.name)
		frappe.set_user("Administrator")
		# Important because _get_current_team doesn't resolve team for team members in background jobs / function call
		frappe.local._current_team = self.team_doc

		# creating this site to add a permission
		site = create_test_site(team=self.team.name)

		frappe.set_user(self.team_member.name)
		# Important because _get_current_team doesn't resolve team for team members in background jobs / function call
		frappe.local._current_team = self.team_doc

		self.assertTrue(frappe.db.exists("Press Role Permission", {"site": site.name, "role": role.name}))

		frappe.set_user("Administrator")
		frappe.delete_doc("Press Role", role.name, force=1)

	def test_dont_allow_to_add_user_if_not_team_member(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = self.team_doc

		role = create_permission_role(self.team.name)
		self.assertRaises(frappe.exceptions.ValidationError, role.add_user, self.external_team_member.name)


# utils
def create_permission_role(team, allow_site_creation=0):
	import random

	doc = frappe.new_doc("Press Role")
	doc.title = "Test Role" + str(random.randint(1, 1000))
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
