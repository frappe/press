# Copyright (c) 2026, Frappe and Contributors
# See license.txt
import frappe

from press.press.doctype.team.test_team import create_test_team
from press.tests.dashboard_request import DashboardRequestTestCase


class TestAcceptTeamInviteRequest(DashboardRequestTestCase):
	def setUp(self):
		super().setUp()
		self.invitee = self.create_press_user()
		create_test_team(self.invitee)
		self.key = frappe.generate_hash(length=32)
		frappe.get_doc(
			{
				"doctype": "Account Request",
				"team": self.team.name,
				"email": self.invitee,
				"invited_by": self.team.user,
				"request_key": self.key,
				"request_key_expiration_time": frappe.utils.add_days(frappe.utils.now_datetime(), 1),
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()

	def test_invitee_joins_the_team_and_is_still_logged_in_after_accepting_the_invite(self):
		self.login(self.invitee)

		self.assertSucceeded(self.post("press.api.account.accept_team_invite", {"key": self.key}))

		self.assertTrue(frappe.db.exists("Team Member", {"parent": self.team.name, "user": self.invitee}))
		self.assertStillLoggedIn(self.invitee)

