# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document

from press.guards import role_guard
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

	def as_selector_option(self) -> dict:
		return {
			"id": self.installation_id,
			"login": self.account_login,
			"url": self.installation_url,
			"image": self.account_avatar_url,
		}

	def fetch_repositories(self) -> list[dict]:
		from press.api.github import fetch_repositories, get_access_token

		# GitHub mints no token for a suspended or removed installation
		if not (token := get_access_token(self.installation_id)):
			frappe.throw(_("GitHub gave no access token for installation {0}").format(self.installation_id))
		return fetch_repositories(INSTALLATION_REPOSITORIES_URL, token)

	def filter_permitted(self, repositories: list[dict]) -> list[dict]:
		"""Keep the repositories the session user's Press Roles permit."""
		if (permitted := role_guard.permitted_repositories()) is None:
			return repositories
		return [row for row in repositories if f"{self.account_login}/{row['name']}".lower() in permitted]


def is_enabled_for_team(team: str) -> bool:
	return bool(frappe.db.get_value("Team", team, "github_installations_enabled"))


def get_selector_options(team: str) -> dict:
	"""Reads only the team's rows; repositories load per installation when the user picks one."""
	rows = frappe.get_all("GitHub Installation", {"team": team, "enabled": 1}, ["*"])
	permitted = role_guard.permitted_repositories()
	installations = [
		GitHubInstallation({**row, "doctype": "GitHub Installation"}).as_selector_option()
		for row in rows
		if permits_account(permitted, row.account_login)
	]
	return {"authorized": bool(rows), "installations": installations}


def permits_account(permitted: set[str] | None, login: str | None) -> bool:
	"""Check whether `permitted` (from Press Roles) holds a repository of the GitHub account `login`."""
	prefix = f"{login or ''}/".lower()
	return permitted is None or any(repository.startswith(prefix) for repository in permitted)


def get_selector_repositories(team: str, installation_id: str) -> list[dict]:
	validate_team_can_use_installation(team, installation_id)
	filters = {"team": team, "installation_id": str(installation_id), "enabled": 1}
	name = frappe.db.get_value("GitHub Installation", filters)
	installation = GitHubInstallation("GitHub Installation", name)
	try:
		repositories = installation.fetch_repositories()
	except Exception:
		log_error("GitHub Installation Repositories Error", doc=installation)
		frappe.db.commit()  # The request rolls back on the raise, which would drop the error log
		raise
	return installation.filter_permitted(repositories)


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


def validate_team_can_use_repository(team: str, installation_id: str | int | None, repository: str | None):
	"""`repository` is owner/name or its GitHub URL. Press Roles can limit members to some repositories."""
	validate_team_can_use_installation(team, installation_id)
	if not installation_id or not is_enabled_for_team(team):
		return

	name = get_repository_name(repository)
	if not role_guard.permits_repository(name):
		frappe.throw(
			_("Your role doesn't give you access to the repository {0}.").format(name),
			frappe.PermissionError,
		)


def get_repository_name(repository: str | None) -> str:
	"""owner/name from owner/name or https://github.com/owner/name(.git)."""
	path = urlparse(repository or "").path.strip("/").removesuffix(".git")
	return "/".join(path.split("/")[:2])
