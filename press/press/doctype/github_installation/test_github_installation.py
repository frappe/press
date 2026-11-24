# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_team


def make_installation(installation_id: int, account_id: int, login: str) -> dict:
	return {
		"id": installation_id,
		"html_url": f"https://github.com/organizations/{login}/settings/installations/{installation_id}",
		"account": {
			"id": account_id,
			"login": login,
			"type": "Organization",
			"avatar_url": f"https://avatars.githubusercontent.com/u/{account_id}",
		},
	}


def make_response(data: dict, ok: bool = True) -> Mock:
	return Mock(ok=ok, json=Mock(return_value=data))


class TestGitHubInstallation(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()
		frappe.db.set_value("Team", self.team.name, "github_installations_enabled", 1)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_oauth_for_flagged_team_links_every_visible_installation_and_drops_token(self):
		self._save_access_token(
			self.team.name, [make_installation(11, 101, "acme"), make_installation(12, 102, "beta")]
		)

		self.assertEqual(self._linked(self.team.name), {("11", "acme", 1), ("12", "beta", 1)})
		self.assertFalse(frappe.db.get_value("Team", self.team.name, "github_access_token"))

	def test_oauth_for_team_without_flag_keeps_token_on_team_and_links_nothing(self):
		frappe.db.set_value("Team", self.team.name, "github_installations_enabled", 0)
		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])

		self.assertEqual(frappe.db.get_value("Team", self.team.name, "github_access_token"), "user-token")
		self.assertEqual(self._linked(self.team.name), set())

	def test_relinking_same_account_after_reinstall_updates_row_instead_of_adding_one(self):
		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])
		self._save_access_token(self.team.name, [make_installation(21, 101, "acme")])

		self.assertEqual(self._linked(self.team.name), {("21", "acme", 1)})

	def test_same_account_cannot_be_linked_twice_to_one_team(self):
		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])
		duplicate = frappe.get_doc(
			{"doctype": "GitHub Installation", "team": self.team.name, "account_id": "101"}
		)
		duplicate.update_from_github(make_installation(11, 101, "acme"))

		with self.assertRaisesRegex(frappe.ValidationError, "GitHub account acme is already linked"):
			duplicate.insert(ignore_permissions=True)

	def test_suspend_and_delete_webhooks_disable_the_linked_rows(self):
		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])

		for action in ("suspend", "deleted"):
			frappe.db.set_value("GitHub Installation", {"team": self.team.name}, "enabled", 1)
			self._send_installation_webhook(action, make_installation(11, 101, "acme"))
			self.assertEqual(self._linked(self.team.name), {("11", "acme", 0)})

	def test_reinstall_webhook_reenables_row_with_new_installation_id(self):
		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])
		self._send_installation_webhook("deleted", make_installation(11, 101, "acme"))
		self._send_installation_webhook("created", make_installation(21, 101, "acme"))

		self.assertEqual(self._linked(self.team.name), {("21", "acme", 1)})

	def test_install_webhook_for_unlinked_account_links_no_team(self):
		self._send_installation_webhook("created", make_installation(31, 301, "stranger"))

		self.assertFalse(frappe.db.exists("GitHub Installation", {"account_id": "301"}))

	def test_options_lists_enabled_installations_with_repos_from_installation_token(self):
		from press.api.github import options

		self._save_access_token(
			self.team.name, [make_installation(11, 101, "acme"), make_installation(12, 102, "beta")]
		)
		frappe.db.set_value(
			"GitHub Installation", {"team": self.team.name, "account_id": "102"}, "enabled", 0
		)
		repository = {"id": 1, "name": "app", "private": True, "html_url": "url", "default_branch": "main"}

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.get_access_token", return_value="installation-token") as get_access_token,
			patch(
				"press.api.github.requests.get", return_value=make_response({"repositories": [repository]})
			) as get,
		):
			data = options()

		get_access_token.assert_called_once_with("11")
		self.assertEqual(get.call_args.args[0], "https://api.github.com/installation/repositories")
		self.assertTrue(data["authorized"])
		self.assertEqual([installation["login"] for installation in data["installations"]], ["acme"])
		self.assertEqual(data["installations"][0]["repos"][0]["name"], "app")

	def test_options_for_flagged_team_without_installations_asks_to_connect(self):
		from press.api.github import options

		with patch("press.api.github.get_current_team", return_value=self.team.name):
			self.assertEqual(options(), {"authorized": False, "installations": []})

	def test_branches_rejects_installation_not_linked_to_flagged_team(self):
		from press.api.github import branches

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.get_branches") as get_branches,
			self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"),
		):
			branches("someone-else", "private-app", installation="999")

		get_branches.assert_not_called()

	def test_branches_allows_linked_installation_for_flagged_team(self):
		from press.api.github import branches

		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])
		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.get_branches", return_value=[]) as get_branches,
		):
			branches("acme", "app", installation="11")

		get_branches.assert_called_once_with("acme", "app", "11")

	def test_new_app_rejects_installation_not_linked_to_flagged_team(self):
		from press.api.app import new

		with (
			patch("press.api.app.ensure_can_manage_apps"),
			patch("press.api.app.get_current_team", return_value=self.team.name),
			self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"),
		):
			new({"name": "private_app", "group": "group", "github_installation_id": "999"})

		self.assertFalse(frappe.db.exists("App", "private_app"))

	def test_install_from_github_without_state_starts_authorization_for_flagged_team(self):
		from press.api.github import GITHUB_OAUTH_AUTHORIZE_URL
		from press.www.github.authorize import get_context

		frappe.set_user(self.team.user)
		frappe.local.form_dict = frappe._dict(installation_id="11", setup_action="install")
		with (
			patch("press.www.github.authorize.get_current_team", return_value=self.team.name),
			patch("press.api.github.frappe.db.get_single_value", return_value="client-id"),
			self.assertRaises(frappe.Redirect),
		):
			get_context(None)

		self.assertTrue(frappe.flags.redirect_location.startswith(GITHUB_OAUTH_AUTHORIZE_URL))

	def _save_access_token(self, team: str, installations: list[dict]):
		from press.www.github.authorize import save_access_token

		response = make_response({"installations": installations})
		with patch("press.api.github.requests.get", return_value=response):
			save_access_token(team, "user-token")

	def _send_installation_webhook(self, action: str, installation: dict):
		payload = {"action": action, "installation": installation}
		frappe.get_doc(
			{"doctype": "GitHub Webhook Log", "event": "installation", "payload": json.dumps(payload)}
		).handle_installation_event()

	def _linked(self, team: str) -> set[tuple]:
		rows = frappe.get_all(
			"GitHub Installation",
			{"team": team},
			["installation_id", "account_login", "enabled"],
			as_list=True,
		)
		return {tuple(row) for row in rows}
