# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for press_role_permission/press_role_permission.py.

is_user_part_of_admin_role() — pure DB-lookup helper, tested with mocked get_all.
PressRolePermission.before_insert() — permission + duplicate guards, tested with mocks.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_role_permission.press_role_permission import (
	PressRolePermission,
	is_user_part_of_admin_role,
)

_MODULE = "press.press.doctype.press_role_permission.press_role_permission"

# ══════════════════════════════════════════════════════════════════════════════
# is_user_part_of_admin_role
# ══════════════════════════════════════════════════════════════════════════════


class TestIsUserPartOfAdminRole(FrappeTestCase):
	"""is_user_part_of_admin_role() returns True iff the user belongs to an admin role."""

	def _patch(self, admin_roles, role_users):
		"""Helper: patch frappe.get_all to return given admin_roles and role_users."""

		def _get_all(doctype, *args, **kwargs):
			if doctype == "Press Role":
				return admin_roles
			if doctype == "Press Role User":
				return role_users
			return []

		return patch(f"{_MODULE}.frappe.get_all", side_effect=_get_all)

	@patch(f"{_MODULE}.get_current_team", return_value="team-1")
	def test_returns_true_when_user_in_admin_role(self, _mock_team):
		admin_roles = [SimpleNamespace(name="role-admin")]
		role_users = [SimpleNamespace(name="pru-1")]
		with self._patch(admin_roles, role_users):
			result = is_user_part_of_admin_role("alice@example.com")
		self.assertTrue(result)

	@patch(f"{_MODULE}.get_current_team", return_value="team-1")
	def test_returns_false_when_user_not_in_any_admin_role(self, _mock_team):
		admin_roles = [SimpleNamespace(name="role-admin")]
		role_users = []
		with self._patch(admin_roles, role_users):
			result = is_user_part_of_admin_role("outsider@example.com")
		self.assertFalse(result)

	@patch(f"{_MODULE}.get_current_team", return_value="team-1")
	def test_returns_false_when_no_admin_roles_exist(self, _mock_team):
		"""If the team has no admin roles, no user can be admin."""
		with self._patch([], []):
			result = is_user_part_of_admin_role("alice@example.com")
		self.assertFalse(result)

	@patch(f"{_MODULE}.get_current_team", return_value="team-1")
	def test_uses_session_user_when_no_user_supplied(self, _mock_team):
		"""Calling without user= falls back to frappe.session.user."""
		admin_roles = [SimpleNamespace(name="role-admin")]
		role_users = [SimpleNamespace(name="pru-2")]
		with (
			self._patch(admin_roles, role_users),
			patch.object(frappe, "session", SimpleNamespace(user="current@example.com")),
		):
			result = is_user_part_of_admin_role()
		self.assertTrue(result)


# ══════════════════════════════════════════════════════════════════════════════
# PressRolePermission.before_insert — permission guard
# ══════════════════════════════════════════════════════════════════════════════


class TestPressRolePermissionBeforeInsert(FrappeTestCase):
	"""before_insert() raises if caller is not authorised or if duplicate exists."""

	def _doc(self, team="team-1", role="role-x", site=None, release_group=None, server=None):
		return SimpleNamespace(
			team=team,
			role=role,
			site=site,
			release_group=release_group,
			server=server,
		)

	def test_system_user_can_insert(self):
		"""A system (Administrator) user bypasses the ownership check."""
		doc = self._doc()
		with (
			patch(f"{_MODULE}.frappe.local.system_user", return_value=True),
			patch(f"{_MODULE}.frappe.db.exists", return_value=False),
		):
			PressRolePermission.before_insert(doc)  # must not raise

	def test_team_owner_can_insert(self):
		"""The team owner (matching session.user) can insert without being admin."""
		doc = self._doc(team="team-1")
		with (
			patch(f"{_MODULE}.frappe.local.system_user", return_value=False),
			patch(f"{_MODULE}.frappe.session", SimpleNamespace(user="owner@example.com")),
			patch(f"{_MODULE}.frappe.db.get_value", return_value="owner@example.com"),
			patch(f"{_MODULE}.frappe.db.exists", return_value=False),
		):
			PressRolePermission.before_insert(doc)  # must not raise

	def test_non_owner_without_admin_role_raises(self):
		"""A non-owner without admin role cannot insert."""
		doc = self._doc(team="team-1")
		with (
			patch(f"{_MODULE}.frappe.local.system_user", return_value=False),
			patch(f"{_MODULE}.frappe.session", SimpleNamespace(user="other@example.com")),
			patch(f"{_MODULE}.frappe.db.get_value", return_value="owner@example.com"),
			patch(f"{_MODULE}.is_user_part_of_admin_role", return_value=False),
			patch(f"{_MODULE}.frappe.db.exists", return_value=False),
			self.assertRaises(frappe.ValidationError),
		):
			PressRolePermission.before_insert(doc)

	def test_non_owner_with_admin_role_can_insert(self):
		"""A non-owner who is part of an admin role CAN insert."""
		doc = self._doc(team="team-1")
		with (
			patch(f"{_MODULE}.frappe.local.system_user", return_value=False),
			patch(f"{_MODULE}.frappe.session", SimpleNamespace(user="admin@example.com")),
			patch(f"{_MODULE}.frappe.db.get_value", return_value="owner@example.com"),
			patch(f"{_MODULE}.is_user_part_of_admin_role", return_value=True),
			patch(f"{_MODULE}.frappe.db.exists", return_value=False),
		):
			PressRolePermission.before_insert(doc)  # must not raise

	def test_duplicate_raises(self):
		"""before_insert() raises when an identical permission already exists."""
		doc = self._doc()
		with (
			patch(f"{_MODULE}.frappe.local.system_user", return_value=True),
			patch(f"{_MODULE}.frappe.db.exists", return_value=True),
			self.assertRaises(frappe.ValidationError),
		):
			PressRolePermission.before_insert(doc)
