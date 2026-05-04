# Copyright (c) 2024, Frappe and Contributors
# See license.txt
from __future__ import annotations

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.team_members import (
	get_invitations,
	get_members,
	get_roles,
	remove_member,
)


def create_test_team_for_members() -> str:
	email = frappe.mock("email")
	create_test_user(email)
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

	def test_get_members_returns_active_members(self):
		team = create_test_team_for_members()
		member_email = frappe.mock("email")
		add_team_member(team, member_email)
		members = get_members(team)
		self.assertEqual(len(members), 1)
		self.assertEqual(members[0].email, member_email)
		self.assertEqual(members[0].status, "Active")
		self.assertEqual(members[0].role, "Developer")

	def test_get_members_returns_empty_for_team_without_members(self):
		team = create_test_team_for_members()
		members = get_members(team)
		self.assertEqual(len(members), 0)

	def test_get_members_includes_user_details(self):
		team = create_test_team_for_members()
		member_email = frappe.mock("email")
		add_team_member(team, member_email)
		members = get_members(team)
		self.assertIsNotNone(members[0].full_name)
		self.assertIn("user_image", members[0])

	def test_get_invitations_returns_pending_invitations(self):
		team = create_test_team_for_members()
		invited_email = frappe.mock("email")
		create_account_request(team, invited_email, invited_by=team)
		invitations = get_invitations(team)
		self.assertEqual(len(invitations), 1)
		self.assertEqual(invitations[0].email, invited_email)
		self.assertEqual(invitations[0].status, "Pending")

	def test_get_invitations_excludes_expired_invitations(self):
		team = create_test_team_for_members()
		expired_email = frappe.mock("email")
		create_account_request(team, expired_email, invited_by=team, expiry_days=-1)
		invitations = get_invitations(team)
		self.assertEqual(len(invitations), 0)

	def test_get_invitations_excludes_uninvited_requests(self):
		team = create_test_team_for_members()
		uninvited_email = frappe.mock("email")
		create_account_request(team, uninvited_email, invited_by=None)
		invitations = get_invitations(team)
		self.assertEqual(len(invitations), 0)

	def test_get_invitations_returns_empty_for_team_without_invitations(self):
		team = create_test_team_for_members()
		invitations = get_invitations(team)
		self.assertEqual(len(invitations), 0)

	def test_get_roles_returns_all_available_roles(self):
		roles = get_roles(frappe.mock("email"))
		expected_roles = [
			{"label": "Admin", "value": "Admin"},
			{"label": "Member", "value": "Member"},
			{"label": "Developer", "value": "Developer"},
			{"label": "Viewer", "value": "Viewer"},
		]
		self.assertEqual(len(roles), 4)
		self.assertEqual(roles, expected_roles)

	def test_get_roles_accepts_team_parameter(self):
		team = create_test_team_for_members()
		roles = get_roles(team)
		self.assertIsNotNone(roles)
		self.assertIsInstance(roles, list)

	def test_remove_member_deletes_team_member(self):
		team = create_test_team_for_members()
		member_email = frappe.mock("email")
		add_team_member(team, member_email)
		member = frappe.db.get_value("Team Member", {"parent": team, "user": member_email}, "name")
		remove_member(team, member)
		self.assertFalse(frappe.db.exists("Team Member", {"parent": team, "user": member_email}))

	def test_remove_member_handles_nonexistent_member(self):
		team = create_test_team_for_members()
		nonexistent_member = frappe.generate_hash(length=10)
		remove_member(team, nonexistent_member)
		self.assertTrue(True)

	def test_remove_member_only_removes_specific_member(self):
		team = create_test_team_for_members()
		member1_email = frappe.mock("email")
		member2_email = frappe.mock("email")
		add_team_member(team, member1_email)
		add_team_member(team, member2_email)
		member1 = frappe.db.get_value("Team Member", {"parent": team, "user": member1_email}, "name")
		remove_member(team, member1)
		self.assertFalse(frappe.db.exists("Team Member", {"parent": team, "user": member1_email}))
		self.assertTrue(frappe.db.exists("Team Member", {"parent": team, "user": member2_email}))
