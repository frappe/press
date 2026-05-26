# Copyright (c) 2024, Frappe and Contributors
# See license.txt
"""
Task 1: RBAC & Team Management Coverage
Tests for:
- Team creation hooks and permission guards
- Member invitation & access control
- Custom role permissions on resources
- Non-admin user restriction scenarios
- Press Role guards (only_admin, only_owner, only_member)
- Press Role Permission create/delete access control
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_role.press_role import (
	PressRole,
	create_user_resource,
	user_has_roles,
)
from press.press.doctype.press_role_permission.press_role_permission import (
	PressRolePermission,
	is_user_part_of_admin_role,
)
from press.press.doctype.team.team import Team, get_team_members
from press.press.doctype.team.test_team import create_test_team

# ─────────────────────────── helpers ────────────────────────────


@contextmanager
def user_context(user: str, team=None):
	"""Switch Frappe session user and optionally pin the current team.

	Important: `frappe.set_user` is patched in before_test.py to also reset
	`frappe.local._current_team`. This context manager re-sets it afterward.
	"""
	prev_user = frappe.session.user
	prev_team = getattr(frappe.local, "_current_team", None)
	try:
		frappe.set_user(user)
		# set_user already resets _current_team; override if we have a team
		if team is not None:
			team_doc = frappe.get_doc("Team", team) if isinstance(team, str) else team
			frappe.local._current_team = team_doc
		yield
	finally:
		frappe.set_user(prev_user)
		frappe.local._current_team = prev_team


@contextmanager
def get_current_team_ctx(team_doc):
	"""
	Patch get_current_team in all consumer modules so that role-guard and
	press-role helpers resolve to the given team regardless of which user
	is currently logged in.
	"""

	def _mock(get_doc=False):
		return team_doc if get_doc else team_doc.name

	with (
		patch("press.guards.role_guard.get_current_team", side_effect=_mock),
		patch("press.press.doctype.press_role.press_role.get_current_team", side_effect=_mock),
		patch("press.utils.get_current_team", side_effect=_mock),
	):
		yield


def _make_press_user(email: str) -> str:
	"""Create a Website User (non-system-manager) with only 'Press User' role.

	Unlike `create_test_user`, which creates System Users, Team.create_user
	creates users with 'Press User' role only. Since 'Press User' has
	desk_access=0, the resulting user_type is 'Website User'.
	`press.utils.user.is_system_manager()` returns False for these users.
	"""
	if not frappe.db.exists("User", email):
		Team.create_user(email.split("@")[0], "User", email)
	return email


def _create_press_role(team: str, *, admin_access: bool = False, title: str | None = None) -> PressRole:
	"""Create a Press Role for the given team (as Administrator)."""
	doc = frappe.new_doc("Press Role")
	doc.title = title or make_autoname("TestRole-.###")
	doc.team = team
	doc.admin_access = 1 if admin_access else 0
	doc.allow_site_creation = 1
	doc.save(ignore_permissions=True)
	return doc


def _add_press_role_user(role: PressRole, user: str) -> None:
	"""Add a user to a Press Role directly (bypassing admin guard)."""
	role.append("users", {"user": user})
	role.save(ignore_permissions=True)


# ═════════════════════════════════════════════════════════════════
# 1. Team Owner / Admin Detection
# ═════════════════════════════════════════════════════════════════


class TestTeamOwnerAndAdminDetection(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.member_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)
		self.team.append("team_members", {"user": self.member_email})
		self.team.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def test_team_owner_is_correctly_identified(self):
		with user_context(self.owner_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			self.assertTrue(team_doc.is_team_owner())

	def test_non_owner_is_not_identified_as_owner(self):
		with user_context(self.member_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			self.assertFalse(team_doc.is_team_owner())

	def test_is_admin_user_returns_false_for_plain_member(self):
		with user_context(self.member_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			self.assertFalse(team_doc.is_admin_user())

	def test_is_admin_user_returns_true_when_member_has_admin_role(self):
		role = _create_press_role(self.team.name, admin_access=True)
		_add_press_role_user(role, self.member_email)
		with user_context(self.member_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			self.assertTrue(team_doc.is_admin_user())

	def test_is_admin_user_returns_false_for_non_admin_role(self):
		role = _create_press_role(self.team.name, admin_access=False)
		_add_press_role_user(role, self.member_email)
		with user_context(self.member_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			self.assertFalse(team_doc.is_admin_user())


# ═════════════════════════════════════════════════════════════════
# 2. Team Member Permission Guards (perm_team_members / perm_relaxed_roles)
# ═════════════════════════════════════════════════════════════════


class TestTeamMemberPermissionGuards(FrappeTestCase):
	"""
	Press permission guards only fire for Website Users.
	System Users (created by frappe's create_test_user) bypass them via
	is_system_manager() which returns True for any System User user_type.
	We use _make_press_user() to create proper Website Users.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.member_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)
		self.team.append("team_members", {"user": self.member_email})
		self.team.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def test_non_admin_member_cannot_add_team_members(self):
		"""A plain member (Website User, no admin role) must NOT be able to modify team_members.

		get_current_team_ctx is needed so that Frappe's has_permission controller
		can resolve the team (returns True for team members), allowing the request
		to reach our custom before_validate check which raises PermissionError.
		"""
		new_user_email = _make_press_user(frappe.mock("email"))
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			team_doc = frappe.get_doc("Team", self.team.name)
			team_doc.append("team_members", {"user": new_user_email})
			with self.assertRaises(frappe.PermissionError):
				team_doc.save()

	def test_team_owner_can_add_team_members(self):
		"""The team owner must be able to add new members."""
		new_user_email = _make_press_user(frappe.mock("email"))
		with user_context(self.owner_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			team_doc.append("team_members", {"user": new_user_email})
			team_doc.save()  # must NOT raise
		self.assertTrue(team_doc.has_member(new_user_email))

	def test_admin_role_member_can_add_team_members(self):
		"""A member with an admin-access Press Role can modify team_members."""
		admin_role = _create_press_role(self.team.name, admin_access=True)
		_add_press_role_user(admin_role, self.member_email)
		new_user_email = _make_press_user(frappe.mock("email"))
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			team_doc = frappe.get_doc("Team", self.team.name)
			team_doc.append("team_members", {"user": new_user_email})
			team_doc.save()  # must NOT raise
		self.assertTrue(frappe.db.exists("Team Member", {"parent": self.team.name, "user": new_user_email}))

	def test_non_admin_member_cannot_change_relaxed_permissions(self):
		"""A plain member must NOT be able to flip relaxed_permissions."""
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			team_doc = frappe.get_doc("Team", self.team.name)
			team_doc.relaxed_permissions = 1
			with self.assertRaises(frappe.PermissionError):
				team_doc.save()

	def test_team_owner_can_change_relaxed_permissions(self):
		"""Team owner must be able to change relaxed_permissions."""
		with user_context(self.owner_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			original = team_doc.relaxed_permissions
			team_doc.relaxed_permissions = 1 - original  # toggle
			team_doc.save()  # must NOT raise


# ═════════════════════════════════════════════════════════════════
# 3. invite_team_member — access control
# ═════════════════════════════════════════════════════════════════


class TestInviteTeamMember(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.member_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)
		self.team.append("team_members", {"user": self.member_email})
		self.team.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def test_non_admin_cannot_invite_team_member(self):
		"""A plain member must NOT be able to invite new users."""
		invite_email = frappe.mock("email")
		with user_context(self.member_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			with self.assertRaises(frappe.ValidationError):
				team_doc.invite_team_member(invite_email, roles=[])

	def test_owner_can_invite_team_member(self):
		"""Team owner must be able to invite new users."""
		invite_email = frappe.mock("email")
		from press.press.doctype.account_request.account_request import AccountRequest

		with user_context(self.owner_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			with patch.object(AccountRequest, "send_verification_email"):
				team_doc.invite_team_member(invite_email, roles=[])
		# An Account Request with team=team and invited_by should be created
		self.assertTrue(frappe.db.exists("Account Request", {"email": invite_email, "team": self.team.name}))

	def test_invite_duplicate_existing_member_raises(self):
		"""Inviting an already-active member must raise a validation error."""
		with user_context(self.owner_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			with self.assertRaises(frappe.ValidationError):
				team_doc.invite_team_member(self.member_email, roles=[])

	def test_invite_invalid_email_raises(self):
		"""Inviting with an invalid email must raise a validation error."""
		with user_context(self.owner_email, team=self.team.name):
			team_doc = frappe.get_doc("Team", self.team.name)
			with self.assertRaises(frappe.ValidationError):
				team_doc.invite_team_member("not-an-email", roles=[])


# ═════════════════════════════════════════════════════════════════
# 4. Duplicate Member Validation
# ═════════════════════════════════════════════════════════════════


class TestDuplicateMemberValidation(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def test_adding_same_member_twice_raises_duplicate_error(self):
		"""Inserting the same user into team_members twice must raise DuplicateEntryError."""
		member_email = _make_press_user(frappe.mock("email"))
		self.team.append("team_members", {"user": member_email})
		self.team.append("team_members", {"user": member_email})
		with self.assertRaises(frappe.DuplicateEntryError):
			self.team.save(ignore_permissions=True)


# ═════════════════════════════════════════════════════════════════
# 5. Member Role Validation
# ═════════════════════════════════════════════════════════════════


class TestMemberRoleValidation(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def test_invalid_role_on_member_raises_validation_error(self):
		"""Assigning an undefined role to a team member must throw a ValidationError."""
		member_email = _make_press_user(frappe.mock("email"))
		self.team.append("team_members", {"user": member_email, "role": "NonExistentRole"})
		with self.assertRaises(frappe.ValidationError):
			self.team.save(ignore_permissions=True)

	def test_valid_roles_are_accepted(self):
		"""Standard roles (Admin, Member, Developer, Viewer) must be accepted."""
		for role in ("Admin", "Member", "Developer", "Viewer"):
			member_email = _make_press_user(frappe.mock("email"))
			team = create_test_team()
			team.append("team_members", {"user": member_email, "role": role})
			team.save(ignore_permissions=True)  # must NOT raise


# ═════════════════════════════════════════════════════════════════
# 6. Press Role — Duplicate Title & Add/Remove Resources
# ═════════════════════════════════════════════════════════════════


class TestPressRoleManagement(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.member_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)
		self.team.append("team_members", {"user": self.member_email})
		self.team.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def _role(self, **kwargs) -> PressRole:
		return _create_press_role(self.team.name, **kwargs)

	# --- duplicate title --------------------------------------------------

	def test_duplicate_role_title_in_same_team_raises(self):
		"""Creating two roles with the same title in the same team must fail."""
		title = make_autoname("DupRole-.###")
		_create_press_role(self.team.name, title=title)
		new_role = frappe.new_doc("Press Role")
		new_role.title = title
		new_role.team = self.team.name
		with self.assertRaises(frappe.DuplicateEntryError):
			new_role.save(ignore_permissions=True)

	def test_same_title_in_different_team_is_allowed(self):
		"""Two teams can have roles with identical titles."""
		title = make_autoname("SharedTitle-.###")
		team2 = create_test_team()
		_create_press_role(self.team.name, title=title)
		_create_press_role(team2.name, title=title)  # must NOT raise

	# --- add_resource / remove_resource (admin-only) ----------------------

	def test_admin_can_add_resource_to_role(self):
		"""An admin must be able to add a resource to a role; guard must not block."""
		role = self._role(admin_access=True)
		_add_press_role_user(role, self.owner_email)
		dummy_site = frappe.mock("name")

		with user_context(self.owner_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			# Patch save to avoid DynamicLink validation for a non-existent document.
			with patch.object(type(press_role), "save", MagicMock()):
				press_role.add_resource([{"document_type": "Site", "document_name": dummy_site}])

		# The resource should have been appended in-memory even if save was mocked.
		self.assertTrue(any(r.document_name == dummy_site for r in press_role.resources))

	def test_adding_duplicate_resource_to_role_raises(self):
		"""Appending the same resource twice to a role must raise ValidationError."""
		role = self._role(admin_access=True)
		_add_press_role_user(role, self.owner_email)
		dummy_site = frappe.mock("name")

		with user_context(self.owner_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			with patch.object(type(press_role), "save", MagicMock()):
				press_role.add_resource([{"document_type": "Site", "document_name": dummy_site}])
				with self.assertRaises(frappe.ValidationError):
					press_role.add_resource([{"document_type": "Site", "document_name": dummy_site}])

	def test_admin_can_remove_resource_from_role(self):
		"""Admin must be able to remove an existing resource from a role.

		We set role.flags.ignore_links = True so Frappe's DynamicLink validator
		accepts the fake document name used as a test fixture.
		"""
		role = self._role(admin_access=True)
		# Add resource, bypassing DynamicLink validation with the document-level flag
		role.append("resources", {"document_type": "Site", "document_name": "test-site-xyz"})
		role.flags.ignore_links = True
		role.save(ignore_permissions=True)

		with user_context(self.owner_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			with patch.object(type(press_role), "save", MagicMock()):
				press_role.remove_resource("Site", "test-site-xyz")

		# Verify resource was removed from the in-memory doc
		self.assertFalse(any(r.document_name == "test-site-xyz" for r in press_role.resources))

	def test_removing_nonexistent_resource_raises(self):
		"""Removing a resource not in the role must raise ValidationError."""
		role = self._role(admin_access=True)

		with user_context(self.owner_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			with self.assertRaises(frappe.ValidationError):
				press_role.remove_resource("Site", "does-not-exist")

	def test_non_admin_cannot_add_resource(self):
		"""A plain member (Website User) without admin access must be blocked by @only_admin."""
		role = self._role(admin_access=False)
		_add_press_role_user(role, self.member_email)
		dummy_site = frappe.mock("name")

		with user_context(self.member_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			with self.assertRaises(frappe.PermissionError):
				press_role.add_resource([{"document_type": "Site", "document_name": dummy_site}])

	# --- add_user / remove_user (admin-only) ------------------------------

	def test_non_admin_cannot_add_user_to_role(self):
		"""A plain member (Website User) must be blocked by @only_admin from add_user."""
		role = self._role(admin_access=False)
		_add_press_role_user(role, self.member_email)
		new_user = _make_press_user(frappe.mock("email"))

		with user_context(self.member_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			with self.assertRaises(frappe.PermissionError):
				press_role.add_user(new_user)

	def test_adding_user_already_in_role_raises(self):
		"""Adding the same user twice to a role must raise ValidationError."""
		role = self._role(admin_access=True)
		_add_press_role_user(role, self.member_email)

		with user_context(self.owner_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			with self.assertRaises(frappe.ValidationError):
				press_role.add_user(self.member_email)

	def test_admin_can_remove_user_from_role(self):
		"""Admin must be able to remove a user from a Press Role."""
		role = self._role(admin_access=True)
		_add_press_role_user(role, self.member_email)

		with user_context(self.owner_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			press_role.remove_user(self.member_email)  # must NOT raise

		self.assertFalse(
			frappe.db.exists("Press Role User", {"parent": role.name, "user": self.member_email})
		)

	def test_removing_user_not_in_role_raises(self):
		"""Removing a user not in a role must raise ValidationError."""
		role = self._role(admin_access=True)

		with user_context(self.owner_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			with self.assertRaises(frappe.ValidationError):
				press_role.remove_user(self.member_email)

	# --- delete (owner-only) ----------------------------------------------

	def test_non_owner_cannot_delete_press_role(self):
		"""Only the team owner may delete a Press Role (@only_owner guard)."""
		role = self._role(admin_access=False)

		with user_context(self.member_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			with self.assertRaises(frappe.PermissionError):
				press_role.delete()

	def test_team_owner_can_delete_press_role(self):
		"""Team owner must be able to delete a Press Role."""
		role = self._role()

		with user_context(self.owner_email, team=self.team.name):
			press_role = frappe.get_doc("Press Role", role.name)
			press_role.delete()  # must NOT raise

		self.assertFalse(frappe.db.exists("Press Role", role.name))


# ═════════════════════════════════════════════════════════════════
# 7. Press Role Permission — create / delete access control
# ═════════════════════════════════════════════════════════════════


class TestPressRolePermissionAccessControl(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.member_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)
		self.team.append("team_members", {"user": self.member_email})
		self.team.save(ignore_permissions=True)
		self.role = _create_press_role(self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def _make_permission_as_admin(self, team: str, role: str, site: str) -> PressRolePermission:
		"""Insert a PressRolePermission as Administrator (bypasses guard and link validation)."""
		doc = frappe.get_doc({"doctype": "Press Role Permission", "role": role, "team": team, "site": site})
		doc.insert(ignore_permissions=True, ignore_links=True)
		return doc

	def test_non_admin_cannot_create_role_permission(self):
		"""A plain member (Website User, no admin role) must NOT create Press Role Permission."""
		dummy_site = frappe.mock("name")
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			perm_doc = frappe.new_doc("Press Role Permission")
			perm_doc.role = self.role.name
			perm_doc.team = self.team.name
			perm_doc.site = dummy_site
			with self.assertRaises(frappe.ValidationError):
				perm_doc.insert()

	def test_team_owner_can_create_role_permission(self):
		"""Team owner must be able to create a Press Role Permission."""
		dummy_site = frappe.mock("name")
		with user_context(self.owner_email, team=self.team.name), get_current_team_ctx(self.team):
			perm_doc = frappe.new_doc("Press Role Permission")
			perm_doc.role = self.role.name
			perm_doc.team = self.team.name
			perm_doc.site = dummy_site
			# ignore_links=True: `site` is a Link to Site; mock value doesn't exist in DB
			perm_doc.insert(ignore_links=True)  # must NOT raise

		self.assertTrue(
			frappe.db.exists(
				"Press Role Permission",
				{"role": self.role.name, "team": self.team.name, "site": dummy_site},
			)
		)

	def test_duplicate_role_permission_raises(self):
		"""Creating a duplicate Press Role Permission must raise an error."""
		dummy_site = frappe.mock("name")
		with user_context(self.owner_email, team=self.team.name), get_current_team_ctx(self.team):
			perm1 = frappe.new_doc("Press Role Permission")
			perm1.role = self.role.name
			perm1.team = self.team.name
			perm1.site = dummy_site
			perm1.insert(ignore_links=True)
			# Attempt duplicate — should raise before link validation
			dup = frappe.new_doc("Press Role Permission")
			dup.role = self.role.name
			dup.team = self.team.name
			dup.site = dummy_site
			with self.assertRaises(frappe.ValidationError):
				dup.insert(ignore_links=True)

	def test_non_admin_cannot_delete_role_permission(self):
		"""A plain member must NOT be able to delete a Press Role Permission."""
		dummy_site = frappe.mock("name")
		perm = self._make_permission_as_admin(self.team.name, self.role.name, dummy_site)
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			perm_doc = frappe.get_doc("Press Role Permission", perm.name)
			with self.assertRaises(frappe.ValidationError):
				perm_doc.delete()

	def test_admin_role_member_can_create_role_permission(self):
		"""A member with admin-access Press Role can create Press Role Permissions."""
		admin_role = _create_press_role(self.team.name, admin_access=True)
		_add_press_role_user(admin_role, self.member_email)
		dummy_site = frappe.mock("name")
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			perm_doc = frappe.new_doc("Press Role Permission")
			perm_doc.role = self.role.name
			perm_doc.team = self.team.name
			perm_doc.site = dummy_site
			perm_doc.insert(ignore_links=True)  # must NOT raise

	def test_is_user_part_of_admin_role_returns_true_for_admin(self):
		admin_role = _create_press_role(self.team.name, admin_access=True)
		_add_press_role_user(admin_role, self.member_email)
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			result = is_user_part_of_admin_role(self.member_email)
		self.assertTrue(result)

	def test_is_user_part_of_admin_role_returns_false_for_plain_member(self):
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			result = is_user_part_of_admin_role(self.member_email)
		self.assertFalse(result)


# ═════════════════════════════════════════════════════════════════
# 8. Role Guard — is_restricted / user_has_roles / roles_enabled
# ═════════════════════════════════════════════════════════════════


class TestRoleGuardHelpers(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.member_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)
		self.team.append("team_members", {"user": self.member_email})
		self.team.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def test_user_has_roles_returns_false_when_no_roles_assigned(self):
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			self.assertFalse(user_has_roles())

	def test_user_has_roles_returns_true_after_role_assignment(self):
		role = _create_press_role(self.team.name)
		_add_press_role_user(role, self.member_email)
		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			self.assertTrue(user_has_roles())

	def test_role_guard_is_restricted_false_for_team_owner(self):
		"""Team owner bypasses is_restricted() even when roles exist."""
		_create_press_role(self.team.name)  # ensure roles_enabled() = True
		from press.guards import role_guard

		with user_context(self.owner_email, team=self.team.name), get_current_team_ctx(self.team):
			self.assertFalse(role_guard.is_restricted())

	def test_role_guard_is_restricted_true_for_plain_member_with_roles_enabled(self):
		"""A member with no role, when roles exist, is restricted."""
		_create_press_role(self.team.name)  # roles_enabled() = True, member has no role
		from press.guards import role_guard

		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			self.assertTrue(role_guard.is_restricted())

	def test_role_guard_is_restricted_false_for_member_with_admin_role(self):
		"""A member with an admin Press Role is NOT restricted."""
		admin_role = _create_press_role(self.team.name, admin_access=True)
		_add_press_role_user(admin_role, self.member_email)
		from press.guards import role_guard

		with user_context(self.member_email, team=self.team.name), get_current_team_ctx(self.team):
			self.assertFalse(role_guard.is_restricted())


# ═════════════════════════════════════════════════════════════════
# 9. create_user_resource — auto-resource creation hook
# ═════════════════════════════════════════════════════════════════


class TestCreateUserResource(FrappeTestCase):
	"""
	When a user with roles (but not admin) creates a document, the system
	should auto-create a Press Role scoped to that user+resource pair.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.member_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)
		self.team.append("team_members", {"user": self.member_email})
		self.team.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def test_create_user_resource_skipped_for_team_owner(self):
		"""Team owner should NOT get an auto-created user resource role."""
		_create_press_role(self.team.name)  # ensure roles_enabled() = True
		mock_doc = frappe._dict(doctype="Site", name=frappe.mock("name"))
		roles_before = frappe.db.count(
			"Press Role",
			{"team": self.team.name, "title": ["like", f"{self.owner_email}%"]},
		)
		with user_context(self.owner_email, team=self.team.name), get_current_team_ctx(self.team):
			create_user_resource(mock_doc, None)
		roles_after = frappe.db.count(
			"Press Role",
			{"team": self.team.name, "title": ["like", f"{self.owner_email}%"]},
		)
		self.assertEqual(roles_before, roles_after)

	def test_create_user_resource_creates_role_for_restricted_member(self):
		"""A member with roles (non-admin) should get an auto-resource Press Role.

		create_user_resource internally saves a PressRole with a resources child
		table containing a DynamicLink that points to our mock document (which
		doesn't exist as a real Site). We patch _validate_links to skip that
		check so the test focuses on the role-creation logic, not link integrity.
		"""
		existing_role = _create_press_role(self.team.name)  # roles_enabled() = True
		_add_press_role_user(existing_role, self.member_email)  # user_has_roles() = True

		mock_doc = frappe._dict(doctype="Site", name=frappe.mock("name"))
		expected_title = f"{self.member_email} / {mock_doc.name}"

		from frappe.model.document import Document

		with (
			user_context(self.member_email, team=self.team.name),
			get_current_team_ctx(self.team),
			patch.object(Document, "_validate_links", MagicMock()),
		):
			create_user_resource(mock_doc, None)
		self.assertTrue(frappe.db.exists("Press Role", {"team": self.team.name, "title": expected_title}))

	def test_create_user_resource_is_idempotent(self):
		"""Calling create_user_resource twice for the same resource must not create duplicates."""
		existing_role = _create_press_role(self.team.name)
		_add_press_role_user(existing_role, self.member_email)

		mock_doc = frappe._dict(doctype="Site", name=frappe.mock("name"))

		from frappe.model.document import Document

		with (
			user_context(self.member_email, team=self.team.name),
			get_current_team_ctx(self.team),
			patch.object(Document, "_validate_links", MagicMock()),
		):
			create_user_resource(mock_doc, None)
			create_user_resource(mock_doc, None)  # second call — must be a no-op

		count = frappe.db.count(
			"Press Role",
			{"team": self.team.name, "title": f"{self.member_email} / {mock_doc.name}"},
		)
		self.assertEqual(count, 1)


# ═════════════════════════════════════════════════════════════════
# 10. Team helper — get_team_members
# ═════════════════════════════════════════════════════════════════


class TestGetTeamMembers(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_get_team_members_returns_members(self):
		member_email = _make_press_user(frappe.mock("email"))
		self.team.append("team_members", {"user": member_email})
		self.team.save(ignore_permissions=True)
		members = get_team_members(self.team.name)
		emails = [m.email for m in members]
		self.assertIn(member_email, emails)

	def test_get_team_members_returns_empty_for_nonexistent_team(self):
		result = get_team_members("does-not-exist-team-xyz")
		self.assertEqual(result, [])

	def test_get_team_members_includes_roles_field(self):
		member_email = _make_press_user(frappe.mock("email"))
		self.team.append("team_members", {"user": member_email})
		self.team.save(ignore_permissions=True)
		members = get_team_members(self.team.name)
		member = next((m for m in members if m.email == member_email), None)
		self.assertIsNotNone(member)
		self.assertIsInstance(member.roles, list)


# ═════════════════════════════════════════════════════════════════
# 11. Banned Team — re-enable rejection
# ═════════════════════════════════════════════════════════════════


class TestBannedTeamReEnableRejection(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_re_enabling_banned_team_raises(self):
		"""A banned team must NOT be re-enabled without lifting the ban first."""
		self.team.banned = 1
		self.team.enabled = 0
		self.team.save(ignore_permissions=True)
		self.team.reload()
		self.team.enabled = 1
		with self.assertRaises(frappe.ValidationError):
			self.team.save(ignore_permissions=True)

	def test_non_banned_team_can_be_disabled_and_re_enabled(self):
		"""A non-banned team may be disabled and then re-enabled freely."""
		self.team.enabled = 0
		self.team.save(ignore_permissions=True)
		self.team.reload()
		self.team.enabled = 1
		self.team.save(ignore_permissions=True)  # must NOT raise


# ═════════════════════════════════════════════════════════════════
# 12. Team guard decorators — only_admin / only_owner / only_member
# ═════════════════════════════════════════════════════════════════


class TestTeamGuardDecorators(FrappeTestCase):
	"""
	Verify that the team_guard decorators correctly enforce access control
	on PressRole methods when the session user is a Website User (Press user).
	team_guard.only_admin / only_owner extract the team from document.team,
	so they do NOT need get_current_team patching.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self.owner_email = _make_press_user(frappe.mock("email"))
		self.member_email = _make_press_user(frappe.mock("email"))
		self.team = create_test_team(self.owner_email)
		self.team.append("team_members", {"user": self.member_email})
		self.team.save(ignore_permissions=True)
		self.role = _create_press_role(self.team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local._current_team = None
		frappe.db.rollback()

	def test_only_admin_blocks_plain_member_from_removing_user(self):
		"""remove_user is @only_admin — a plain Website User member must be blocked."""
		_add_press_role_user(self.role, self.member_email)

		with user_context(self.member_email, team=self.team.name):
			role_doc = frappe.get_doc("Press Role", self.role.name)
			with self.assertRaises(frappe.PermissionError):
				role_doc.remove_user(self.member_email)

	def test_only_owner_blocks_member_from_deleting_press_role(self):
		"""delete() is @only_owner — a non-owner Website User must be blocked."""
		with user_context(self.member_email, team=self.team.name):
			role_doc = frappe.get_doc("Press Role", self.role.name)
			with self.assertRaises(frappe.PermissionError):
				role_doc.delete()

	def test_only_owner_allows_team_owner_to_delete_press_role(self):
		"""Team owner must be able to delete a Press Role via @only_owner guard."""
		with user_context(self.owner_email, team=self.team.name):
			role_doc = frappe.get_doc("Press Role", self.role.name)
			role_doc.delete()  # must NOT raise

		self.assertFalse(frappe.db.exists("Press Role", self.role.name))

	def test_only_admin_allows_admin_role_member_to_remove_user(self):
		"""A member with an admin Press Role must pass the @only_admin guard."""
		admin_role = _create_press_role(self.team.name, admin_access=True)
		_add_press_role_user(admin_role, self.member_email)
		_add_press_role_user(self.role, self.member_email)

		with user_context(self.member_email, team=self.team.name):
			role_doc = frappe.get_doc("Press Role", self.role.name)
			role_doc.remove_user(self.member_email)  # must NOT raise

	def test_only_member_blocks_non_member_from_being_added_to_role(self):
		"""add_user has @only_member guard — a user not in the team cannot be added."""
		outsider_email = _make_press_user(frappe.mock("email"))
		# outsider is NOT in team_members; add_user validates that the user being added is a member

		with user_context(self.owner_email, team=self.team.name):
			role_doc = frappe.get_doc("Press Role", self.role.name)
			with self.assertRaises(frappe.PermissionError):
				role_doc.add_user(outsider_email)
