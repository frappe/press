from __future__ import annotations

import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from unittest.mock import Mock, patch
from urllib.parse import urlencode

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase


class TestGitHubAuthorization(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = self._create_test_team()
		self._ensure_team_membership(self.team, self.team.user)
		frappe.set_user(self.team.user)
		self._set_form_dict()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_encode_github_oauth_state_binds_redirect_and_user(self):
		state = self._encode_github_oauth_state(
			self.team.name,
			f"{frappe.utils.get_url()}/dashboard/sites?tab=apps#new",
		)

		payload = self._decode_github_oauth_state(state)

		self.assertEqual(payload["team"], self.team.name)
		self.assertEqual(payload["redirect_url"], "/dashboard/sites?tab=apps#new")

	def test_decode_github_oauth_state_allows_same_user_after_session_change(self):
		state = self._encode_github_oauth_state(self.team.name, "/dashboard/sites")
		original_sid = frappe.session.sid
		frappe.session.sid = frappe.generate_hash(length=10)

		try:
			payload = self._decode_github_oauth_state(state)
		finally:
			frappe.session.sid = original_sid

		self.assertEqual(payload["team"], self.team.name)
		self.assertEqual(payload["redirect_url"], "/dashboard/sites")

	def test_get_context_redirects_guest_to_login_with_callback(self):
		state = self._encode_github_oauth_state(self.team.name, "/dashboard/sites")
		frappe.set_user("Guest")
		self._set_form_dict(code="oauth-code", state=state)
		callback_url = f"/github/authorize?{urlencode({'code': 'oauth-code', 'state': state})}"
		login_url = frappe.utils.get_url(
			f"/dashboard/login?{urlencode({'redirect': callback_url})}"
		)

		with self.assertRaises(frappe.Redirect):
			self._get_context()(None)

		self.assertEqual(frappe.flags.redirect_location, login_url)

	def test_get_context_rejects_tampered_state(self):
		state = self._encode_github_oauth_state(self.team.name, "/dashboard/sites")
		payload = self._decode_state_payload(state)
		payload["team"] = self._create_test_team().name
		tampered_state = self._replace_state_payload(state, payload)

		self._set_form_dict(code="oauth-code", state=tampered_state)

		with (
			self.assertRaises(frappe.Redirect),
			patch("press.www.github.authorize.obtain_access_token") as obtain_access_token,
			patch("press.www.github.authorize.log_error") as log_error,
			patch("press.www.github.authorize.frappe.db.commit", new=Mock()),
		):
			self._get_context()(None)

		obtain_access_token.assert_not_called()
		log_error.assert_called_once()
		self.assertNotIn("code", log_error.call_args.kwargs)
		self.assertEqual(frappe.flags.redirect_location, frappe.utils.get_url("/dashboard"))

	def test_get_context_rejects_team_removed_after_state_was_issued(self):
		shared_team = self._create_test_team()
		self._ensure_team_membership(shared_team, shared_team.user)
		self._ensure_team_membership(shared_team, self.team.user)
		self.assertIn(
			shared_team.name,
			{team_doc["name"] for team_doc in self._get_valid_teams_for_user(self.team.user)},
		)

		state = self._encode_github_oauth_state(shared_team.name, "/dashboard/sites")
		self._remove_team_member(shared_team, self.team.user)
		self._set_form_dict(code="oauth-code", state=state)

		with (
			self.assertRaises(frappe.Redirect),
			patch("press.www.github.authorize.obtain_access_token") as obtain_access_token,
			patch("press.www.github.authorize.log_error") as log_error,
			patch("press.www.github.authorize.frappe.db.commit", new=Mock()),
		):
			self._get_context()(None)

		obtain_access_token.assert_not_called()
		log_error.assert_called_once()
		self.assertNotIn("code", log_error.call_args.kwargs)
		self.assertEqual(frappe.flags.redirect_location, frappe.utils.get_url("/dashboard"))

	def test_obtain_access_token_redacts_oauth_code_and_token_from_logs(self):
		response = {
			"access_token": "secret-token",
			"scope": "repo",
			"token_type": "bearer",
		}

		with (
			patch("press.www.github.authorize.requests.post") as post,
			patch("press.www.github.authorize.log_error") as log_error,
			patch(
				"press.www.github.authorize.frappe.db.get_single_value",
				side_effect=["client-id", "client-secret"],
			),
			patch(
				"press.www.github.authorize.frappe.db.set_value",
				side_effect=RuntimeError("db failure"),
			),
		):
			post.return_value.json.return_value = response
			self._obtain_access_token()("oauth-code", self.team.name)

		log_error.assert_called_once()
		self.assertNotIn("code", log_error.call_args.kwargs)
		self.assertEqual(
			log_error.call_args.kwargs["response"],
			{
				"error": None,
				"error_description": None,
				"error_uri": None,
				"has_access_token": True,
				"scope": "repo",
				"token_type": "bearer",
			},
		)

	def _decode_state_payload(self, state: str) -> dict[str, str]:
		encoded_payload = state.rsplit(".", 1)[0]
		padding = "=" * (-len(encoded_payload) % 4)
		return json.loads(urlsafe_b64decode(f"{encoded_payload}{padding}").decode())

	def _decode_github_oauth_state(self, state: str) -> dict[str, str]:
		from press.api.github import decode_github_oauth_state

		return decode_github_oauth_state(state)

	def _encode_github_oauth_state(self, team: str, redirect_url: str) -> str:
		from press.api.github import encode_github_oauth_state

		return encode_github_oauth_state(team, redirect_url)

	def _ensure_team_membership(self, team, user: str):
		if frappe.db.exists("Team Member", {"parent": team.name, "user": user}):
			return

		now = frappe.utils.now()
		frappe.db.sql(
			"""
			INSERT INTO `tabTeam Member`
				(name, creation, modified, modified_by, owner, docstatus, idx, parent, parentfield, parenttype, user)
			VALUES
				(%s, %s, %s, %s, %s, 0, 1, %s, %s, %s, %s)
			""",
			(
				frappe.generate_hash(length=10),
				now,
				now,
				"Administrator",
				"Administrator",
				team.name,
				"team_members",
				"Team",
				user,
			),
		)

	def _create_test_team(self):
		user = frappe.mock("email")
		create_test_user(user)
		now = frappe.utils.now()
		team = frappe._dict(name=frappe.generate_hash(length=10), user=user)
		frappe.db.sql(
			"""
			INSERT INTO `tabTeam`
				(name, creation, modified, modified_by, owner, docstatus, idx, enabled, user, country, currency, billing_name)
			VALUES
				(%s, %s, %s, %s, %s, 0, 0, 1, %s, %s, %s, %s)
			""",
			(
				team.name,
				now,
				now,
				"Administrator",
				"Administrator",
				team.user,
				"India",
				"INR",
				team.user,
			),
		)
		return team

	def _get_context(self):
		from press.www.github.authorize import get_context

		return get_context

	def _obtain_access_token(self):
		from press.www.github.authorize import obtain_access_token

		return obtain_access_token

	def _get_valid_teams_for_user(self, user: str):
		from press.utils import get_valid_teams_for_user

		return get_valid_teams_for_user(user)

	def _remove_team_member(self, team, user: str):
		frappe.db.delete("Team Member", {"parent": team.name, "user": user})

	def _replace_state_payload(self, state: str, payload: dict[str, str]) -> str:
		encoded_payload, signature = state.rsplit(".", 1)
		encoded_payload = urlsafe_b64encode(
			json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
		).decode().rstrip("=")
		return f"{encoded_payload}.{signature}"

	def _set_form_dict(self, **kwargs):
		frappe.flags.redirect_location = None
		frappe.local.form_dict = frappe._dict(kwargs)
