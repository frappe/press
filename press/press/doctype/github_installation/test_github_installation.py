# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.app_source.test_app_source import create_test_app_source
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

	def test_reinstall_and_unsuspend_webhooks_keep_rows_disabled_until_team_reconnects(self):
		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])
		self._send_installation_webhook("deleted", make_installation(11, 101, "acme"))
		self._send_installation_webhook("created", make_installation(21, 101, "acme"))
		self._send_installation_webhook("unsuspend", make_installation(21, 101, "acme"))
		self.assertEqual(self._linked(self.team.name), {("11", "acme", 0)})

		self._save_access_token(self.team.name, [make_installation(21, 101, "acme")])
		self.assertEqual(self._linked(self.team.name), {("21", "acme", 1)})

	def test_oauth_link_failure_midway_leaves_no_installation_linked(self):
		broken = make_installation(12, 102, "beta")
		del broken["html_url"]

		with self.assertRaises(KeyError):
			self._save_access_token(self.team.name, [make_installation(11, 101, "acme"), broken])

		self.assertEqual(self._linked(self.team.name), set())

	def test_install_webhook_for_unlinked_account_links_no_team(self):
		self._send_installation_webhook("created", make_installation(31, 301, "stranger"))

		self.assertFalse(frappe.db.exists("GitHub Installation", {"account_id": "301"}))

	def test_options_lists_enabled_installations_without_calling_github(self):
		from press.api.github import options

		self._save_access_token(
			self.team.name, [make_installation(11, 101, "acme"), make_installation(12, 102, "beta")]
		)
		frappe.db.set_value(
			"GitHub Installation", {"team": self.team.name, "account_id": "102"}, "enabled", 0
		)

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.get_access_token") as get_access_token,
			patch("press.api.github.requests.get") as get,
		):
			data = options()

		get_access_token.assert_not_called()
		get.assert_not_called()
		self.assertTrue(data["authorized"])
		self.assertEqual([installation["login"] for installation in data["installations"]], ["acme"])
		self.assertNotIn("repos", data["installations"][0])

	def test_options_for_team_without_flag_lists_installations_with_one_call_and_no_repos(self):
		from press.api.github import options

		frappe.db.set_value("Team", self.team.name, "github_installations_enabled", 0)
		frappe.db.set_value("Team", self.team.name, "github_access_token", "user-token")
		response = make_response({"installations": [make_installation(11, 101, "acme")]})

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.requests.get", return_value=response) as get,
		):
			data = options()

		get.assert_called_once()
		self.assertEqual(data["installations"][0]["login"], "acme")
		self.assertNotIn("repos", data["installations"][0])

	def test_installation_repositories_lists_repos_with_installation_token_for_linked_installation(self):
		from press.api.github import installation_repositories

		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])
		repository = {"id": 1, "name": "app", "private": True, "html_url": "url", "default_branch": "main"}

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.get_access_token", return_value="installation-token") as get_access_token,
			patch(
				"press.api.github.requests.get", return_value=make_response({"repositories": [repository]})
			) as get,
		):
			repositories = installation_repositories("11")

		get_access_token.assert_called_once_with("11")
		self.assertEqual(get.call_args.args[0], "https://api.github.com/installation/repositories")
		self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "token installation-token")
		self.assertEqual(
			repositories,
			[{"id": 1, "name": "app", "private": True, "url": "url", "default_branch": "main"}],
		)

	def test_installation_repositories_rejects_installation_not_linked_to_flagged_team(self):
		from press.api.github import installation_repositories

		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])
		frappe.db.set_value("GitHub Installation", {"team": self.team.name}, "enabled", 0)

		for installation in ("11", "999"):
			with (
				patch("press.api.github.get_current_team", return_value=self.team.name),
				patch("press.api.github.get_access_token") as get_access_token,
				self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"),
			):
				installation_repositories(installation)

			get_access_token.assert_not_called()

	def test_installation_repositories_fails_when_github_mints_no_token(self):
		from press.api.github import installation_repositories

		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.get_access_token", return_value=None),
			patch("press.api.github.requests.get") as get,
			self.assertRaisesRegex(frappe.ValidationError, "GitHub gave no access token for installation 11"),
		):
			installation_repositories("11")

		get.assert_not_called()

	def test_installation_repositories_fails_with_githubs_message_when_listing_is_refused(self):
		from press.api.github import installation_repositories

		self._save_access_token(self.team.name, [make_installation(11, 101, "acme")])
		refused = make_response({"message": "Resource not accessible by integration"}, ok=False)

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.get_access_token", return_value="installation-token"),
			patch("press.api.github.requests.get", return_value=refused),
			self.assertRaisesRegex(
				frappe.ValidationError, "Error fetching repositories from GitHub: Resource not accessible"
			),
		):
			installation_repositories("11")

	def test_installation_repositories_for_team_without_flag_uses_the_teams_user_token(self):
		from press.api.github import installation_repositories

		frappe.db.set_value("Team", self.team.name, "github_installations_enabled", 0)
		frappe.db.set_value("Team", self.team.name, "github_access_token", "user-token")

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.requests.get", return_value=make_response({"repositories": []})) as get,
		):
			installation_repositories("11")

		self.assertEqual(get.call_args.args[0], "https://api.github.com/user/installations/11/repositories")
		self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "token user-token")

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

	@patch.object(AppSource, "create_release", create_test_app_release)
	def test_branches_rejects_another_teams_private_app_source(self):
		from press.api.github import branches

		source = self._create_app_source(create_test_team().name)
		frappe.db.set_value("User", self.team.user, "user_type", "Website User")
		frappe.set_user(self.team.user)
		with (
			patch("press.api.github.get_branches") as get_branches,
			self.assertRaisesRegex(frappe.PermissionError, "don't have access to this app source"),
		):
			branches("frappe", "erpnext", app_source=source.name)

		get_branches.assert_not_called()

	@patch.object(AppSource, "create_release", create_test_app_release)
	def test_branches_with_app_source_uses_the_sources_repository_not_the_clients(self):
		from press.api.github import branches

		source = self._create_app_source(self.team.name)
		with patch("press.api.github.get_branches", return_value=[]) as get_branches:
			branches("someone-else", "private-app", app_source=source.name)

		get_branches.assert_called_once_with("frappe", "erpnext", "11")

	def test_get_frappe_branch_major_version_rejects_installation_not_linked_to_flagged_team(self):
		from press.api.github import get_frappe_branch_major_version

		with (
			patch("press.api.github.get_current_team", return_value=self.team.name),
			patch("press.api.github.fetch_frappe_branch_major_version") as fetch,
			self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"),
		):
			get_frappe_branch_major_version("someone-else", "private-app", "main", installation="999")

		fetch.assert_not_called()

	def test_release_group_add_app_rejects_installation_not_linked_to_flagged_team(self):
		group = frappe.get_doc({"doctype": "Release Group", "team": self.team.name})
		app = {
			"name": "private_app",
			"title": "Private App",
			"repository_url": "https://github.com/someone-else/private-app",
			"branch": "main",
			"github_installation_id": "999",
		}

		with self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"):
			group.add_app(app)

		self.assertFalse(frappe.db.exists("App", "private_app"))

	def test_marketplace_app_insert_rejects_installation_not_linked_to_flagged_team(self):
		marketplace_app = frappe.get_doc(
			{
				"doctype": "Marketplace App",
				"name": "private_app",
				"title": "Private App",
				"team": self.team.name,
				"repository_url": "https://github.com/someone-else/private-app",
				"branch": "main",
				"frappe_version": "Version 14",
				"github_installation_id": "999",
			}
		)

		with self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"):
			marketplace_app.insert()

		self.assertFalse(frappe.db.exists("Marketplace App", "private_app"))

	@patch.object(AppSource, "create_release", create_test_app_release)
	def test_marketplace_app_insert_rejects_source_whose_installation_is_not_linked(self):
		source = self._create_app_source(self.team.name)
		marketplace_app = frappe.get_doc(
			{
				"doctype": "Marketplace App",
				"app": source.app,
				"title": "Frappe",
				"team": self.team.name,
				"sources": [{"version": "Version 14", "source": source.name}],
			}
		)

		with self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"):
			marketplace_app.insert()

		self.assertFalse(frappe.db.exists("Marketplace App", {"app": source.app, "team": self.team.name}))

	@patch.object(AppSource, "create_release", create_test_app_release)
	def test_adding_source_with_unlinked_installation_to_existing_listing_is_rejected(self):
		listing = self._create_listing()
		new_source = self._create_listing_source("develop")
		frappe.db.set_value("App Source", new_source.name, "github_installation_id", "11")
		listing.append("sources", {"version": "Version 14", "source": new_source.name})

		with self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"):
			listing.save()

	@patch.object(AppSource, "create_release", create_test_app_release)
	def test_listing_whose_older_source_lost_its_installation_can_still_be_edited(self):
		listing = self._create_listing()
		frappe.db.set_value("App Source", listing.sources[0].source, "github_installation_id", "11")
		listing.description = "Still editable"

		listing.save()

		self.assertEqual(
			frappe.db.get_value("Marketplace App", listing.name, "description"), "Still editable"
		)

	@patch.object(AppSource, "create_release", create_test_app_release)
	def test_moving_listing_to_team_without_its_sources_installation_is_rejected(self):
		listing = self._create_listing(create_test_team().name)
		frappe.db.set_value("App Source", listing.sources[0].source, "github_installation_id", "11")
		listing.team = self.team.name

		with self.assertRaisesRegex(frappe.PermissionError, "isn't connected to your team"):
			listing.save()

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

	def _create_app_source(self, team: str) -> AppSource:
		source = create_test_app_source("Version 14", create_test_app(), team=team)
		frappe.db.set_value("App Source", source.name, "github_installation_id", "11")
		return source

	def _create_listing_source(self, branch: str, team: str | None = None) -> AppSource:
		app = create_test_app("listed_app", "Listed App")
		return create_test_app_source(
			"Version 14",
			app,
			"https://github.com/acme/listed_app",
			branch=branch,
			team=team or self.team.name,
		)

	def _create_listing(self, team: str | None = None):
		from press.press.doctype.marketplace_app.test_marketplace_app import create_test_marketplace_app

		team = team or self.team.name
		source = self._create_listing_source("main", team)
		return create_test_marketplace_app(
			"listed_app", team, [{"version": "Version 14", "source": source.name}]
		)

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
