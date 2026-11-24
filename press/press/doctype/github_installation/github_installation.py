# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document

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
			frappe.throw(f"GitHub account {self.account_login} is already linked to team {self.team}")

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

	def as_selector_option(self) -> dict:
		from press.api.github import fetch_repositories, get_access_token

		return {
			"id": self.installation_id,
			"login": self.account_login,
			"url": self.installation_url,
			"image": self.account_avatar_url,
			"repos": fetch_repositories(
				INSTALLATION_REPOSITORIES_URL, get_access_token(self.installation_id)
			),
		}


def is_enabled_for_team(team: str) -> bool:
	return bool(frappe.db.get_value("Team", team, "github_installations_enabled"))


def get_selector_options(team: str) -> dict:
	names = frappe.get_all("GitHub Installation", {"team": team, "enabled": 1}, pluck="name")
	installations = [GitHubInstallation("GitHub Installation", name).as_selector_option() for name in names]
	return {"authorized": bool(installations), "installations": installations}


def link_installations(team: str, user_token: str):
	"""Link every installation the GitHub user can see to the team."""
	from press.api.github import fetch_installations

	for installation in fetch_installations(user_token):
		link_installation(team, installation)


def link_installation(team: str, installation: dict):
	account_id = str(installation["account"]["id"])
	name = frappe.db.get_value("GitHub Installation", {"team": team, "account_id": account_id})
	if name:
		doc = GitHubInstallation("GitHub Installation", name)
	else:
		doc = frappe.get_doc({"doctype": "GitHub Installation", "team": team, "account_id": account_id})
	doc.update_from_github(installation)
	doc.save(ignore_permissions=True)


def update_installation_from_webhook(installation: dict, enabled: bool):
	"""Update rows already linked to this GitHub account. Webhooks never link a new team."""
	frappe.db.set_value(
		"GitHub Installation",
		{"account_id": str(installation["account"]["id"])},
		{
			"installation_id": str(installation["id"]),
			"account_login": installation["account"]["login"],
			"enabled": enabled,
		},
	)


def validate_team_can_use_installation(team: str, installation_id: str | int | None):
	if not installation_id or not is_enabled_for_team(team):
		return

	filters = {"team": team, "installation_id": str(installation_id), "enabled": 1}
	if not frappe.db.exists("GitHub Installation", filters):
		frappe.throw(
			"This GitHub account isn't connected to your team. Connect it from GitHub and try again.",
			frappe.PermissionError,
		)
