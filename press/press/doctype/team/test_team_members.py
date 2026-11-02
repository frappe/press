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

	def test_get_invitations_excludes_accepted_invitations_with_cleared_request_key(self):
		"""Acceptance nulls request_key but leaves the expiration time in the
		future, so the invite must not keep showing as pending."""
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			accepted_email = frappe.mock("email")
			create_account_request(team, accepted_email, invited_by=team)
			frappe.db.set_value("Account Request", {"email": accepted_email}, "request_key", None)
			invitations = get_invitations(team)
			self.assertEqual(len(invitations), 0)

	def test_get_invitations_excludes_invitations_with_blanked_request_key(self):
		"""The expire_request_key scheduled job blanks request_key to an empty
		string; such invites must not show as pending either."""
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			invalidated_email = frappe.mock("email")
			create_account_request(team, invalidated_email, invited_by=team)
			frappe.db.set_value("Account Request", {"email": invalidated_email}, "request_key", "")
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

	def test_get_roles_returns_empty_when_no_team(self):
		"""When no team is provided, an empty list should be returned."""
		roles = get_roles(None)
		self.assertEqual(roles, [])

	def test_get_roles_accepts_team_parameter(self):
		"""get_roles should accept a team parameter and return a list of roles."""
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
			roles = get_roles(team)
			self.assertIsNotNone(roles)
			self.assertIsInstance(roles, list)

	def test_get_roles_includes_custom_press_roles_for_team(self):
		"""When a team has custom Press Roles, they should be returned."""
		team = create_test_team_for_members()
		team_user = frappe.get_value("Team", team, "user")
		with user_context(team_user):
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
			self.assertEqual(len(roles), 1)
			self.assertEqual(roles[0]["label"], "Custom Role")
			self.assertEqual(roles[0]["value"], "Custom Role")
			self.assertIsNotNone(roles[0]["name"])
			for field in PERMISSION_FIELDS:
				self.assertIn(field, roles[0])
			self.assertTrue(roles[0]["allow_billing"])
			self.assertTrue(roles[0]["allow_apps"])
			self.assertFalse(roles[0]["admin_access"])
			self.assertFalse(roles[0]["allow_site_creation"])

	def test_get_roles_excludes_custom_roles_from_other_teams(self):
		"""Custom Press Roles from other teams should not be included."""
		team1 = create_test_team_for_members()
		team2 = create_test_team_for_members()
		team1_user = frappe.get_value("Team", team1, "user")
		with user_context(team1_user):
			frappe.get_doc(
				{
					"doctype": "Press Role",
					"title": "Team1 Role",
					"team": team1,
				}
			).insert(ignore_permissions=True)
			frappe.get_doc(
				{
					"doctype": "Press Role",
					"title": "Team2 Role",
					"team": team2,
				}
			).insert(ignore_permissions=True)

			roles = get_roles(team1)
			labels = [r["label"] for r in roles]
			self.assertIn("Team1 Role", labels)
			self.assertNotIn("Team2 Role", labels)
