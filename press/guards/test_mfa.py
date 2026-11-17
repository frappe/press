# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from contextlib import contextmanager

import frappe
import pyotp
from frappe.tests.utils import FrappeTestCase

from press.api.account import enable_2fa, get_2fa_qr_code_url
from press.press.doctype.press_role.test_press_role import create_user
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.user_2fa.test_user_2fa import create_test_user_2fa
from press.utils import get_current_team
from press.www.dashboard import get_boot

TEAM_2FA_REQUIRED = "requires two-factor authentication"


class TestTeam2FAEnforcement(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		self.team.db_set("enforce_2fa", 1)
		member = create_user(f"{frappe.generate_hash(length=8)}@example.com")
		member.add_roles("Press User")
		self.member = member.name
		self.team.append("team_members", {"user": self.member})
		self.team.save()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	@contextmanager
	def as_user(self, user: str, team: str | None = None, sessionless: bool = False, **form):
		frappe.set_user(user)
		if not sessionless:
			# frappe.set_user sets the sid to the user, which is what API key logins look like
			frappe.session.sid = frappe.generate_hash()
		frappe.form_dict.update(form)
		headers = {"X-Press-Team": team} if team else {}
		frappe.local.request = frappe._dict(method="POST", headers=headers)
		try:
			yield
		finally:
			del frappe.local.request
			frappe.set_user("Administrator")

	def test_member_without_2fa_is_refused_by_a_team_that_enforces_it(self):
		with self.as_user(self.member, self.team.name):
			self.assertRaisesRegex(frappe.PermissionError, TEAM_2FA_REQUIRED, get_current_team)

	def test_owner_without_2fa_is_refused_their_own_team_when_it_enforces_it(self):
		with self.as_user(self.team.user):
			self.assertRaisesRegex(frappe.PermissionError, TEAM_2FA_REQUIRED, get_current_team)

	def test_member_with_2fa_gets_the_team_that_enforces_it(self):
		create_test_user_2fa(self.member)
		with self.as_user(self.member, self.team.name):
			self.assertEqual(get_current_team(), self.team.name)

	def test_member_without_2fa_gets_a_team_that_does_not_enforce_it(self):
		self.team.db_set("enforce_2fa", 0)
		with self.as_user(self.member, self.team.name):
			self.assertEqual(get_current_team(), self.team.name)

	def test_api_key_request_is_not_refused_by_a_team_that_enforces_2fa(self):
		with self.as_user(self.member, self.team.name, sessionless=True):
			self.assertEqual(get_current_team(), self.team.name)

	def test_member_without_2fa_can_read_the_team_doc_to_set_up_2fa(self):
		with self.as_user(self.member, self.team.name, cmd="press.api.client.get", doctype="Team"):
			self.assertEqual(get_current_team(), self.team.name)

	def test_member_without_2fa_can_enable_it_while_the_team_enforces_it(self):
		with self.as_user(self.member, self.team.name):
			secret = get_2fa_qr_code_url().split("secret=")[1].split("&")[0]
			enable_2fa(pyotp.TOTP(secret).now())
			self.assertEqual(get_current_team(), self.team.name)

	def test_dashboard_boots_for_member_without_2fa_when_chat_is_enabled(self):
		frappe.db.set_single_value("Press Settings", "enable_chat", 1)
		with self.as_user(self.member):
			boot = get_boot()
		self.assertEqual(boot.default_team, self.team.name)
		self.assertTrue(boot.chat_enabled)

	def test_member_without_2fa_cannot_read_other_docs_of_a_team_that_enforces_it(self):
		with self.as_user(self.member, self.team.name, cmd="press.api.client.get", doctype="Site"):
			self.assertRaisesRegex(frappe.PermissionError, TEAM_2FA_REQUIRED, get_current_team)
