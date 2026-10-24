# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.account_request.account_request import AccountRequest
from press.press.doctype.team.team_members import get_invitations
from press.tests.dashboard_request import DashboardRequestTestCase


@patch.object(AccountRequest, "send_verification_email", new=Mock())
class TestTeamMemberRequests(DashboardRequestTestCase):
	def setUp(self):
		super().setUp()
		self.invitee = frappe.mock("email")

	def add_member(self) -> str:
		member = self.create_press_user()
		self.team.append("team_members", {"user": member, "role": ""})
		self.team.save(ignore_permissions=True)
		frappe.db.commit()
		return member

	def invite(self, email: str):
		return self.run_doc_method(self.team, "invite_team_member", {"email": email})

	def test_owner_invites_a_member_and_is_still_logged_in(self):
		self.login()

		self.assertSucceeded(self.invite(self.invitee))

		self.assertEqual([i.email for i in get_invitations(self.team.name)], [self.invitee])
		self.assertStillLoggedIn()

	def test_owner_cancels_an_invitation_and_is_still_logged_in(self):
		self.login()
		self.assertSucceeded(self.invite(self.invitee))

		cancel = self.run_doc_method(self.team, "cancel_invitation", {"email": self.invitee})

		self.assertSucceeded(cancel)
		self.assertEqual(get_invitations(self.team.name), [])
		self.assertStillLoggedIn()

	def test_owner_removes_a_member_and_is_still_logged_in(self):
		member = self.add_member()
		self.login()

		self.assertSucceeded(self.run_doc_method(self.team, "remove_team_member", {"member": member}))

		self.assertFalse(frappe.db.exists("Team Member", {"parent": self.team.name, "user": member}))
		self.assertStillLoggedIn()

	def test_member_without_admin_access_cannot_remove_another_member_and_stays_logged_in(self):
		member = self.add_member()
		other_member = self.add_member()
		self.login(member)

		remove = self.run_doc_method(self.team, "remove_team_member", {"member": other_member})

		self.assertEqual(remove.status_code, 403, remove.json)
		self.assertIn("Only team admin", remove.json["_server_messages"])
		self.assertTrue(frappe.db.exists("Team Member", {"parent": self.team.name, "user": other_member}))
		self.assertStillLoggedIn(member)
