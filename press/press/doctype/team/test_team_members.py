# Copyright (c) 2024, Frappe and Contributors
# See license.txt
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.team_members import (
	PERMISSION_FIELDS,
	PREDEFINED_ROLES,
	get_invitations,
	get_roles,
)

if TYPE_CHECKING:
	from collections.abc import Generator


@contextmanager
def user_context(user: str) -> Generator[None, None, None]:
	"""Context manager to temporarily switch the user context."""
	session_user = frappe.session.user
	session_data = frappe.session.data.copy()
	if session_user == user:
		yield
		return
	try:
		frappe.set_user(user)
		yield
	finally:
		frappe.set_user(session_user)
		frappe.session.data = session_data


def create_test_team_for_members() -> str:
	email = frappe.mock("email")
	create_test_user(email)
	with user_context(email):
		team = frappe.get_doc(
			{
				"doctype": "Team",
				"user": email,
				"enabled": 1,
				"country": "India",
				"currency": "INR",
				"billing_name": "Test Team",
			}
		).insert(ignore_if_duplicate=True)
		return team.name


def add_team_member(team: str, user_email: str) -> str:
	create_test_user(user_email)
	user = frappe.get_value("User", {"email": user_email}, "name")
	team_doc = frappe.get_doc("Team", team)
	team_doc.append("team_members", {"user": user})
	team_doc.save()
	return team


def create_account_request(
	team: str,
	email: str,
	invited_by: str | None = None,
	expiry_days: int = 7,
):
	expiry = frappe.utils.add_days(frappe.utils.now_datetime(), expiry_days)
	doc = frappe.get_doc(
		{
			"doctype": "Account Request",
			"team": team,
			"email": email,
			"request_key": "test-key-for-invitations",
		}
	)
	if invited_by:
		doc.invited_by = invited_by
	doc.request_key_expiration_time = expiry
	doc.insert(ignore_if_duplicate=True)


class TestTeamMembers(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_get_invitations_returns_pending_invitations(self):
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			invited_email = frappe.mock("email")
			create_account_request(team, invited_email, invited_by=team)
			invitations = get_invitations(team)
			self.assertEqual(len(invitations), 1)
			self.assertEqual(invitations[0].email, invited_email)
			self.assertEqual(invitations[0].status, "Pending")

	def test_get_invitations_excludes_expired_invitations(self):
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			expired_email = frappe.mock("email")
			create_account_request(team, expired_email, invited_by=team, expiry_days=-1)
			invitations = get_invitations(team)
			self.assertEqual(len(invitations), 0)

	def test_get_invitations_excludes_uninvited_requests(self):
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			uninvited_email = frappe.mock("email")
			create_account_request(team, uninvited_email, invited_by=None)
			invitations = get_invitations(team)
			self.assertEqual(len(invitations), 0)

	def test_get_invitations_returns_empty_for_team_without_invitations(self):
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			invitations = get_invitations(team)
			self.assertEqual(len(invitations), 0)

	def test_get_roles_returns_all_predefined_roles_when_no_team(self):
		"""When no team is provided, only predefined roles should be returned."""
		roles = get_roles(None)
		self.assertEqual(len(roles), len(PREDEFINED_ROLES))

	def test_get_roles_returns_correct_role_labels_and_values(self):
		"""Predefined roles should have correct label/value and all permission fields."""
		roles = get_roles(frappe.mock("email"))
		for role in roles:
			self.assertIn(role["label"], ["Admin", "Developer", "Member", "Viewer"])
			self.assertEqual(role["label"], role["value"])
			self.assertTrue(role["is_predefined"])
			# Verify all permission fields are present
			for field in PERMISSION_FIELDS:
				self.assertIn(field, role)
				self.assertIsInstance(role[field], bool)

	def test_get_roles_predefined_role_permissions(self):
		"""Verify specific permission configurations for each predefined role."""
		roles = get_roles(frappe.mock("email"))
		roles_by_label = {r["label"]: r for r in roles}

		# Admin should have most permissions enabled
		admin = roles_by_label["Admin"]
		self.assertTrue(admin["admin_access"])
		self.assertTrue(admin["allow_billing"])
		self.assertTrue(admin["allow_site_creation"])
		self.assertTrue(admin["allow_bench_creation"])
		self.assertTrue(admin["allow_server_creation"])
		self.assertTrue(admin["allow_apps"])
		self.assertTrue(admin["allow_webhook_configuration"])

		# Member should have very few permissions
		member = roles_by_label["Member"]
		self.assertFalse(member["admin_access"])
		self.assertFalse(member["allow_billing"])
		self.assertFalse(member["allow_site_creation"])

		# Viewer should have no permissions at all
		viewer = roles_by_label["Viewer"]
		for field in PERMISSION_FIELDS:
			self.assertFalse(viewer[field])

	def test_get_roles_accepts_team_parameter(self):
		"""get_roles should accept a team parameter and return a list of roles."""
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			roles = get_roles(team)
			self.assertIsNotNone(roles)
			self.assertIsInstance(roles, list)

	def test_get_roles_returns_predefined_roles_with_team_param(self):
		"""When a team is provided, predefined roles should still be included."""
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			roles = get_roles(team)
			predefined = [r for r in roles if r["is_predefined"]]
			self.assertEqual(len(predefined), len(PREDEFINED_ROLES))

	def test_get_roles_includes_custom_press_roles_for_team(self):
		"""When a team has custom Press Roles, they should be included in the result."""
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			# Create a custom Press Role for this team
			frappe.get_doc(
				{
					"doctype": "Press Role",
					"title": "Custom Role",
					"team": team,
					"admin_access": 0,
					"allow_billing": 1,
					"allow_apps": 1,
					"allow_site_creation": 0,
				}
			).insert(ignore_permissions=True)

			roles = get_roles(team)
			custom_roles = [r for r in roles if not r["is_predefined"]]
			self.assertEqual(len(custom_roles), 1)
			self.assertEqual(custom_roles[0]["label"], "Custom Role")
			self.assertEqual(custom_roles[0]["value"], "Custom Role")
			self.assertIsNotNone(custom_roles[0]["name"])
			self.assertFalse(custom_roles[0]["is_predefined"])
			# Verify permission fields from Press Role are included
			self.assertTrue(custom_roles[0]["allow_billing"])
			self.assertTrue(custom_roles[0]["allow_apps"])
			self.assertFalse(custom_roles[0]["admin_access"])
			self.assertFalse(custom_roles[0]["allow_site_creation"])

	def test_get_roles_excludes_custom_roles_from_other_teams(self):
		"""Custom Press Roles from other teams should not be included."""
		team1 = create_test_team_for_members()
		team2 = create_test_team_for_members()
		team1_user = frappe.get_value("Team", team1, "user")
		with user_context(team1_user):
			# Create a Press Role for team1
			frappe.get_doc(
				{
					"doctype": "Press Role",
					"title": "Team1 Role",
					"team": team1,
				}
			).insert(ignore_permissions=True)
			# Create a Press Role for team2
			frappe.get_doc(
				{
					"doctype": "Press Role",
					"title": "Team2 Role",
					"team": team2,
				}
			).insert(ignore_permissions=True)

			roles = get_roles(team1)
			custom_labels = [r["label"] for r in roles if not r["is_predefined"]]
			self.assertIn("Team1 Role", custom_labels)
			self.assertNotIn("Team2 Role", custom_labels)
