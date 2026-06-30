from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe
from frappe.tests.ui_test_helpers import create_test_user

from press.api.account import accept_team_invite, logout_from_all_devices, signup, validate_pincode
from press.press.doctype.account_request.account_request import AccountRequest
from press.press.doctype.team.test_team import create_test_team


@contextmanager
def user_context(user: str):
	"""Run the wrapped block as `user`, restoring the session afterwards."""
	session_user = frappe.session.user
	session_sid = frappe.session.sid
	session_data = frappe.session.data.copy()
	try:
		frappe.set_user(user)
		yield
	finally:
		frappe.set_user(session_user)
		frappe.session.sid = session_sid
		frappe.session.data = session_data


class TestAccountApi(TestCase):
	"""End-to-End Tests for account/team creation via API"""

	def tearDown(self):
		frappe.db.rollback()

	def _create_invite(self, team, email):
		"""Create a pending team invitation (Account Request) and return its key."""
		key = frappe.generate_hash(length=32)
		frappe.get_doc(
			{
				"doctype": "Account Request",
				"team": team.name,
				"email": email,
				"invited_by": team.user,
				"request_key": key,
				"request_key_expiration_time": frappe.utils.add_days(frappe.utils.now_datetime(), 1),
			}
		).insert(ignore_permissions=True)
		return key

	def _fake_signup(self, email: str | None = None) -> Mock:
		"""Call press.api.account.signup without sending verification mail."""
		email = email or frappe.mock("email")
		with patch.object(AccountRequest, "send_verification_email") as mock_send_email:
			signup(email)
		return mock_send_email

	def _create_session(self, user: str, sid: str | None = None) -> str:
		sid = sid or frappe.generate_hash(length=32)
		sessions = frappe.qb.DocType("Sessions")

		(
			frappe.qb.into(sessions)
			.columns(sessions.sessiondata, sessions.user, sessions.lastupdate, sessions.sid, sessions.status)
			.insert((frappe.as_json({"user": user}), user, frappe.utils.now(), sid, "Active"))
		).run()

		return sid

	def _delete_session_without_commit(self, sid=None, **_kwargs):
		frappe.db.delete("Sessions", {"sid": sid})

	def test_account_request_is_created_from_signup(self):
		acc_req_count_before = frappe.db.count("Account Request")
		self._fake_signup()
		acc_req_count_after = frappe.db.count("Account Request")
		self.assertGreater(acc_req_count_after, acc_req_count_before)

	def test_logout_from_all_devices_clears_other_sessions_and_keeps_current(self):
		user = frappe.mock("email")
		create_test_user(user)
		frappe.db.set_value("User", user, "simultaneous_sessions", 3)
		current_sid = self._create_session(user)
		other_sid = self._create_session(user)
		another_sid = self._create_session(user)

		with (
			user_context(user),
			patch("frappe.sessions.delete_session", side_effect=self._delete_session_without_commit),
		):
			frappe.session.sid = current_sid

			logout_from_all_devices()

			self.assertTrue(frappe.db.exists("Sessions", {"sid": current_sid}))
			self.assertFalse(frappe.db.exists("Sessions", {"sid": other_sid}))
			self.assertFalse(frappe.db.exists("Sessions", {"sid": another_sid}))
			self.assertEqual(frappe.session.user, user)

	def test_logout_from_all_devices_with_only_current_session_does_not_error(self):
		user = frappe.mock("email")
		create_test_user(user)
		current_sid = self._create_session(user)

		with (
			user_context(user),
			patch("frappe.sessions.delete_session", side_effect=self._delete_session_without_commit),
		):
			frappe.session.sid = current_sid

			logout_from_all_devices()

			self.assertTrue(frappe.db.exists("Sessions", {"sid": current_sid}))
			self.assertEqual(frappe.db.count("Sessions", {"user": user}), 1)

	def test_logout_from_all_devices_rejects_guest_call(self):
		from frappe.handler import execute_cmd

		request = getattr(frappe.local, "request", None)
		form_dict = frappe.local.form_dict

		try:
			with user_context("Guest"):
				frappe.local.request = frappe._dict(method="POST")
				frappe.local.form_dict = frappe._dict(cmd="press.api.account.logout_from_all_devices")

				with self.assertRaises(frappe.PermissionError):
					execute_cmd(frappe.local.form_dict.cmd)
		finally:
			frappe.local.request = request
			frappe.local.form_dict = form_dict

	def test_accept_team_invite_with_blank_existing_member_role(self):
		team = create_test_team()
		existing_member = frappe.mock("email")
		create_test_user(existing_member)
		team.append("team_members", {"user": existing_member})
		team.save(ignore_permissions=True)
		member = frappe.db.get_value(
			"Team Member",
			{"parent": team.name, "user": existing_member},
			"name",
		)
		frappe.db.set_value("Team Member", member, "role", "")

		invited_member = frappe.mock("email")
		create_test_user(invited_member)
		key = frappe.generate_hash(length=32)
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"team": team.name,
				"email": invited_member,
				"invited_by": team.user,
				"request_key": key,
				"request_key_expiration_time": frappe.utils.add_days(frappe.utils.now_datetime(), 1),
			}
		).insert(ignore_permissions=True)

		with user_context(invited_member):
			accept_team_invite(key)

		self.assertTrue(frappe.db.exists("Team Member", {"parent": team.name, "user": invited_member}))
		self.assertEqual(frappe.db.get_value("Team Member", member, "role"), "Member")
		self.assertFalse(frappe.db.get_value("Account Request", account_request.name, "request_key"))

	def test_invite_team_member_accepts_custom_role_by_press_role_name(self):
		"""The invite dialog sends the Press Role document name (a hash) for
		custom roles, not the title. invite_team_member must accept it and store
		it as press_role."""
		from press.press.doctype.press_role.test_press_role import create_permission_role

		team = create_test_team()
		custom_role = create_permission_role(team.name)
		invited_member = frappe.mock("email")

		with user_context(team.user), patch.object(AccountRequest, "send_verification_email"):
			team.invite_team_member(invited_member, roles=f'["{custom_role.name}"]')

		self.assertEqual(
			frappe.db.get_value(
				"Account Request",
				{"team": team.name, "email": invited_member},
				"press_role",
			),
			custom_role.name,
		)

	def _invite(self, team, email, roles):
		"""Invite a member as the team owner, return the generated request key."""
		with user_context(team.user), patch.object(AccountRequest, "send_verification_email"):
			team.invite_team_member(email, roles=roles)
		return frappe.db.get_value("Account Request", {"team": team.name, "email": email}, "request_key")

	def _accept(self, email, key):
		"""Accept the invite as the invited user (the existing-user flow)."""
		with user_context(email):
			accept_team_invite(key)

	def test_invite_and_accept_predefined_role_adds_member_with_that_role(self):
		for role in ["Admin", "Developer", "Member", "Viewer"]:
			with self.subTest(role=role):
				team = create_test_team()
				invited = frappe.mock("email")
				create_test_user(invited)

				key = self._invite(team, invited, roles=f'["{role}"]')
				self._accept(invited, key)

				self.assertEqual(
					frappe.db.get_value("Team Member", {"parent": team.name, "user": invited}, "role"),
					role,
				)
				self.assertFalse(
					frappe.db.get_value(
						"Account Request", {"team": team.name, "email": invited}, "request_key"
					)
				)

	def test_invite_and_accept_custom_role_sets_member_role_to_role_title(self):
		from press.press.doctype.press_role.test_press_role import create_permission_role

		team = create_test_team()
		custom_role = create_permission_role(team.name)
		invited = frappe.mock("email")
		create_test_user(invited)

		key = self._invite(team, invited, roles=f'["{custom_role.name}"]')
		self._accept(invited, key)

		# invite_role_label resolves the Press Role name to its title for the
		# Team Member.role string field.
		self.assertEqual(
			frappe.db.get_value("Team Member", {"parent": team.name, "user": invited}, "role"),
			custom_role.title,
		)

	def test_accept_team_invite_is_idempotent_for_existing_member(self):
		"""If the user is already on the team, accepting the invite clears the
		key and is a no-op instead of throwing a duplicate-member error."""
		team = create_test_team()
		invited = frappe.mock("email")
		create_test_user(invited)
		team.append("team_members", {"user": invited, "role": "Member"})
		team.save(ignore_permissions=True)

		key = frappe.generate_hash(length=32)
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"team": team.name,
				"email": invited,
				"invited_by": team.user,
				"request_key": key,
				"request_key_expiration_time": frappe.utils.add_days(frappe.utils.now_datetime(), 1),
			}
		).insert(ignore_permissions=True)

		members_before = frappe.db.count("Team Member", {"parent": team.name, "user": invited})
		self._accept(invited, key)
		members_after = frappe.db.count("Team Member", {"parent": team.name, "user": invited})

		self.assertEqual(members_before, members_after, "should not duplicate the membership")
		self.assertFalse(frappe.db.get_value("Account Request", account_request.name, "request_key"))

	def test_accept_team_invite_rejected_when_session_user_is_not_invitee(self):
		team = create_test_team()
		invited = frappe.mock("email")
		create_test_user(invited)
		intruder = frappe.mock("email")
		create_test_user(intruder)

		key = self._invite(team, invited, roles='["Member"]')

		with user_context(intruder), self.assertRaises(frappe.ValidationError) as cm:
			accept_team_invite(key)
		self.assertIn("can't be accepted with the current account", str(cm.exception))
		self.assertFalse(frappe.db.exists("Team Member", {"parent": team.name, "user": intruder}))

	def test_accept_team_invite_recovers_from_quoted_printable_break_in_key(self):
		"""The invite URL is long enough that email transport wraps it with a
		quoted-printable soft break ("=" + newline). If that artifact leaks into
		the key (e.g. the recipient copies the link instead of clicking), accept
		must still resolve the right Account Request and add the member."""
		team = create_test_team()
		invited = frappe.mock("email")
		create_test_user(invited)

		key = self._create_invite(team, invited)
		# Soft break landing inside the key, as it appears in an undecoded link.
		corrupted_key = key[:3] + "=\n" + key[3:]

		with user_context(invited):
			accept_team_invite(corrupted_key)

		self.assertTrue(frappe.db.exists("Team Member", {"parent": team.name, "user": invited}))
		self.assertFalse(
			frappe.db.get_value("Account Request", {"team": team.name, "email": invited}, "request_key")
		)

	def test_pincode_is_correctly_set(self):
		"""Test if pincode is correctly set on account creation."""
		test_billing_details = frappe._dict(
			{
				"billing_name": "John Doe",
				"address": "Rose Street",
				"city": "Mumbai",
				"state": "Maharashtra",
				"postal_code": "40004",
				"country": "India",
			}
		)

		self.assertRaises(frappe.ValidationError, validate_pincode, test_billing_details)

		test_billing_details["postal_code"] = "400001"
		test_billing_details["state"] = "Karnataka"
		self.assertRaisesRegex(
			frappe.ValidationError,
			f"Postal Code {test_billing_details.postal_code} is not associated with {test_billing_details.state}",
			validate_pincode,
			test_billing_details,
		)
