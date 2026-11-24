# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from press.utils import log_error

INSTALLATION_REPOSITORIES_URL = "https://api.github.com/installation/repositories"


class GitHubInstallation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_avatar_url: DF.Data | None
		account_id: DF.Data
		account_login: DF.Data | None
		account_type: DF.Literal["Organization", "User"]
		enabled: DF.Check
		installation_id: DF.Data
		installation_url: DF.Data | None
		team: DF.Link
	# end: auto-generated types

	def validate(self):
		self.validate_account_is_unique_for_team()

	def validate_account_is_unique_for_team(self):
		filters = {"team": self.team, "account_id": self.account_id, "name": ("!=", self.name)}
		if frappe.db.exists("GitHub Installation", filters):
			frappe.throw(
				_("GitHub account {0} is already linked to team {1}").format(self.account_login, self.team)
			)

	def update_from_github(self, installation: dict):
		account = installation["account"]
		self.update(
			{
				"installation_id": str(installation["id"]),
				"account_login": account["login"],
				"account_type": account["type"],
				"account_avatar_url": account["avatar_url"],
				"installation_url": installation["html_url"],
				"enabled": 1,
			}
		)

	def as_selector_option(self) -> dict | None:
		"""None when GitHub refuses this installation, so the team's other installations still show."""
		try:
			repositories = self.fetch_repositories()
		except Exception:
			log_error("GitHub Installation Repositories Error", doc=self)
			return None

		return {
			"id": self.installation_id,
			"login": self.account_login,
			"url": self.installation_url,
			"image": self.account_avatar_url,
			"repos": repositories,
		}

	def fetch_repositories(self) -> list[dict]:
		from press.api.github import fetch_repositories, get_access_token

		# GitHub mints no token for a suspended or removed installation
		if not (token := get_access_token(self.installation_id)):
			frappe.throw(_("GitHub gave no access token for installation {0}").format(self.installation_id))
		return fetch_repositories(INSTALLATION_REPOSITORIES_URL, token)


def is_enabled_for_team(team: str) -> bool:
	return bool(frappe.db.get_value("Team", team, "github_installations_enabled"))


def get_selector_options(team: str) -> dict:
	rows = frappe.get_all("GitHub Installation", {"team": team, "enabled": 1}, ["*"])
	options = [
		GitHubInstallation({**row, "doctype": "GitHub Installation"}).as_selector_option() for row in rows
	]
	installations = [option for option in options if option]
	return {"authorized": bool(installations), "installations": installations}


def link_installations(team: str, user_token: str):
	"""Link every installation the GitHub user can see to the team, all or nothing."""
	from press.api.github import fetch_installations

	installations = fetch_installations(user_token)
	frappe.db.savepoint("link_github_installations")
	try:
		for installation in installations:
			link_installation(team, installation)
	except Exception:
		frappe.db.rollback(save_point="link_github_installations")
		raise


def link_installation(team: str, installation: dict):
	account_id = str(installation["account"]["id"])
	name = frappe.db.get_value("GitHub Installation", {"team": team, "account_id": account_id})
	if name:
		doc = GitHubInstallation("GitHub Installation", name)
	else:
		doc = frappe.get_doc({"doctype": "GitHub Installation", "team": team, "account_id": account_id})
	doc.update_from_github(installation)
	doc.save(ignore_permissions=True)


def disable_installations_for_account(installation: dict):
	"""Webhooks only take access away. Only the OAuth flow links or re-enables a team."""
	frappe.db.set_value(
		"GitHub Installation", {"account_id": str(installation["account"]["id"])}, "enabled", 0
	)


def validate_team_can_use_installation(team: str, installation_id: str | int | None):
	if not installation_id or not is_enabled_for_team(team):
		return

	filters = {"team": team, "installation_id": str(installation_id), "enabled": 1}
	if not frappe.db.exists("GitHub Installation", filters):
		frappe.throw(
			_("This GitHub account isn't connected to your team. Connect it from GitHub and try again."),
			frappe.PermissionError,
		)
