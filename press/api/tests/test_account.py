from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe
from frappe.tests.ui_test_helpers import create_test_user

from press.api.account import accept_team_invite, leave_team, signup, validate_pincode
from press.press.doctype.account_request.account_request import AccountRequest
from press.press.doctype.team.team_members import get_invitations
from press.press.doctype.team.test_team import (
	create_test_press_admin_team,
	create_test_team,
)


@contextmanager
def user_context(user: str):
	"""Run the wrapped block as `user`, restoring the session afterwards."""
	session_user = frappe.session.user
	session_data = frappe.session.data.copy()
	try:
		frappe.set_user(user)
		yield
	finally:
		frappe.set_user(session_user)
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

	def test_account_request_is_created_from_signup(self):
		acc_req_count_before = frappe.db.count("Account Request")
		self._fake_signup()
		acc_req_count_after = frappe.db.count("Account Request")
		self.assertGreater(acc_req_count_after, acc_req_count_before)

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

	def test_invite_team_member_blocked_while_unexpired_invitation_pending(self):
		team = create_test_team()
		invited = frappe.mock("email")
		self._invite(team, invited, roles=None)

		with (
			user_context(team.user),
			patch.object(AccountRequest, "send_verification_email"),
			self.assertRaises(frappe.ValidationError) as cm,
		):
			team.invite_team_member(invited)
		self.assertIn("already been invited", str(cm.exception))

	def test_invite_team_member_allowed_after_previous_invitation_expired(self):
		"""The expire_request_key scheduler blanks lapsed keys only after the
		fact; an invite whose expiration time has passed but whose key is still
		set must not block re-inviting."""
		team = create_test_team()
		invited = frappe.mock("email")
		self._create_invite(team, invited)
		self._expire_invitations(team, invited)

		self._invite(team, invited, roles=None)

		self.assertEqual(len(get_invitations(team.name)), 1)

	def test_cancel_invitation_removes_pending_invitation_and_allows_reinvite(self):
		team = create_test_team()
		invited = frappe.mock("email")
		self._invite(team, invited, roles=None)

		with user_context(team.user):
			team.cancel_invitation(invited)

		self.assertEqual(len(get_invitations(team.name)), 0)
		self._invite(team, invited, roles=None)
		self.assertEqual(len(get_invitations(team.name)), 1)

	def test_cancel_invitation_without_pending_invitation_throws(self):
		team = create_test_team()
		uninvited = frappe.mock("email")

		with user_context(team.user), self.assertRaises(frappe.ValidationError) as cm:
			team.cancel_invitation(uninvited)
		self.assertIn("No pending invitation found", str(cm.exception))

	def _expire_invitations(self, team, email):
		frappe.db.set_value(
			"Account Request",
			{"team": team.name, "email": email},
			"request_key_expiration_time",
			frappe.utils.add_days(frappe.utils.now_datetime(), -1),
			update_modified=False,
		)

	def test_cancel_invitation_cancels_the_active_invitation_when_an_expired_one_coexists(self):
		"""A re-invite after expiry leaves two Account Requests with request_key
		set until the expiry scheduler runs; cancelling must invalidate the
		active one, not just the lapsed one."""
		team = create_test_team()
		invited = frappe.mock("email")
		self._invite(team, invited, roles=None)
		self._expire_invitations(team, invited)
		self._invite(team, invited, roles=None)

		with user_context(team.user):
			team.cancel_invitation(invited)

		self.assertEqual(len(get_invitations(team.name)), 0)

	def test_cancel_invitation_throws_when_only_an_expired_invitation_exists(self):
		"""An invite past its expiry is no longer pending (it's not listed and
		doesn't block re-inviting), so there is nothing to cancel — even while
		its request_key is still set awaiting the expiry scheduler."""
		team = create_test_team()
		invited = frappe.mock("email")
		self._invite(team, invited, roles=None)
		self._expire_invitations(team, invited)

		with user_context(team.user), self.assertRaises(frappe.ValidationError) as cm:
			team.cancel_invitation(invited)
		self.assertIn("No pending invitation found", str(cm.exception))

	def test_cancel_invitation_rejected_for_user_who_is_neither_owner_nor_admin(self):
		team = create_test_team()
		invited = frappe.mock("email")
		self._invite(team, invited, roles=None)
		# A Press User (not a System Manager) from another team; create_test_user
		# grants all roles, which would sneak past the is_system_manager check.
		outsider = create_test_press_admin_team().user

		with user_context(outsider), self.assertRaises(frappe.PermissionError) as cm:
			team.cancel_invitation(invited)
		self.assertIn("Only team admin", str(cm.exception))
		self.assertEqual(len(get_invitations(team.name)), 1, "invitation should remain pending")

	def test_cancel_invitation_allowed_for_team_member_with_admin_access(self):
		from press.press.doctype.press_role.test_press_role import create_permission_role

		team = create_test_team()
		invited = frappe.mock("email")
		self._invite(team, invited, roles=None)

		admin_member = self._add_plain_member(team)
		admin_role = create_permission_role(team.name)
		admin_role.admin_access = 1
		admin_role.append("users", {"user": admin_member})
		admin_role.save(ignore_permissions=True)

		with user_context(admin_member):
			team.cancel_invitation(invited)
		self.assertEqual(len(get_invitations(team.name)), 0)

	def _add_plain_member(self, team, email=None):
		"""Add a Press User (not a System Manager) as a regular team member."""
		member = create_test_press_admin_team(email).user
		team.append("team_members", {"user": member, "role": ""})
		team.save(ignore_permissions=True)
		# save(ignore_permissions=True) leaves the flag on the doc, which would
		# bypass the only_admin guard and mask a broken admin check.
		team.flags.ignore_permissions = False
		return member

	def test_remove_team_member_rejected_for_member_without_admin_access(self):
		team = create_test_team()
		plain_member = self._add_plain_member(team)
		other_member = self._add_plain_member(team)

		with user_context(plain_member), self.assertRaises(frappe.PermissionError) as cm:
			team.remove_team_member(other_member)
		self.assertIn("Only team admin", str(cm.exception))
		self.assertTrue(
			frappe.db.exists("Team Member", {"parent": team.name, "user": other_member}),
			"membership should remain intact",
		)

	def test_remove_team_member_allowed_for_team_member_with_admin_access(self):
		from press.press.doctype.press_role.test_press_role import create_permission_role

		team = create_test_team()
		admin_member = self._add_plain_member(team)
		other_member = self._add_plain_member(team)
		admin_role = create_permission_role(team.name)
		admin_role.admin_access = 1
		admin_role.append("users", {"user": admin_member})
		admin_role.save(ignore_permissions=True)

		with user_context(admin_member):
			team.remove_team_member(other_member)
		self.assertFalse(frappe.db.exists("Team Member", {"parent": team.name, "user": other_member}))

	def test_member_without_admin_access_can_still_leave_team(self):
		team = create_test_team()
		plain_member = self._add_plain_member(team)

		with user_context(plain_member):
			leave_team(team.name)
		self.assertFalse(frappe.db.exists("Team Member", {"parent": team.name, "user": plain_member}))

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

	def test_invite_and_accept_custom_role_adds_member_to_press_role(self):
		"""The invite stores the selected role in Account Request.press_role.
		Accepting must assign that Press Role to the member — otherwise they
		join role-less and lose access to the team's sites."""
		from press.press.doctype.press_role.test_press_role import create_permission_role

		team = create_test_team()
		custom_role = create_permission_role(team.name)
		invited = frappe.mock("email")
		create_test_user(invited)

		key = self._invite(team, invited, roles=f'["{custom_role.name}"]')
		self._accept(invited, key)

		self.assertTrue(
			frappe.db.exists("Press Role User", {"parent": custom_role.name, "user": invited}),
			"accepted member should be added to the invited Press Role",
		)

	def test_accept_legacy_invite_with_press_roles_child_table_adds_member_to_press_role(self):
		"""Pending invites created before the invite rework stored roles in the
		press_roles child table instead of the press_role field. Accepting those
		must still assign the Press Role."""
		from press.press.doctype.press_role.test_press_role import create_permission_role

		team = create_test_team()
		custom_role = create_permission_role(team.name)
		invited = frappe.mock("email")
		create_test_user(invited)

		key = frappe.generate_hash(length=32)
		frappe.get_doc(
			{
				"doctype": "Account Request",
				"team": team.name,
				"email": invited,
				"invited_by": team.user,
				"request_key": key,
				"request_key_expiration_time": frappe.utils.add_days(frappe.utils.now_datetime(), 1),
				"press_roles": [{"press_role": custom_role.name}],
			}
		).insert(ignore_permissions=True)
		self._accept(invited, key)

		self.assertTrue(
			frappe.db.exists("Press Role User", {"parent": custom_role.name, "user": invited}),
			"accepted member should be added to the Press Role from the legacy child table",
		)

	def test_accept_team_invite_is_idempotent_for_existing_member(self):
		"""If the user is already on the team, accepting the invite clears the
		key and is a no-op instead of throwing a duplicate-member error."""
		team = create_test_team()
		invited = frappe.mock("email")
		create_test_user(invited)
		team.append("team_members", {"user": invited, "role": ""})
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

		key = self._invite(team, invited, roles=None)

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
