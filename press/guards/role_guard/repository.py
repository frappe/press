from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.query_builder.functions import Count

from press.utils import is_admin_user, is_team_owner
from press.utils import user as utils_user


def allowed_repositories(team: str) -> set[tuple[str, str]] | None:
	"""
	Return the (owner, repository) pairs the session user may access through
	the team's GitHub account, lowercased. `None` means no restriction applies.

	Owners, admins, system managers and role-less members of relaxed teams
	are not restricted. With the switch on, a team without roles allows nothing.
	"""
	if utils_user.is_system_manager() or is_team_owner(team) or is_admin_user(team):
		return None

	restrict, relaxed = frappe.db.get_value(
		"Team", team, ["restrict_repository_access", "relaxed_permissions"]
	) or (0, 0)
	if not restrict:
		return None

	if relaxed and not user_role_count(team):
		return None

	PressRole = frappe.qb.DocType("Press Role")
	PressRoleUser = frappe.qb.DocType("Press Role User")
	PressRoleRepository = frappe.qb.DocType("Press Role Repository")
	rows = (
		frappe.qb.from_(PressRoleRepository)
		.inner_join(PressRole)
		.on(PressRole.name == PressRoleRepository.parent)
		.inner_join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.select(PressRoleRepository.repository_owner, PressRoleRepository.repository)
		.where(PressRoleRepository.parenttype == "Press Role")
		.where(PressRole.team == team)
		.where(PressRoleUser.user == frappe.session.user)
		.run(as_dict=True)
	)
	return {(row.repository_owner.lower(), row.repository.lower()) for row in rows}


def user_role_count(team: str) -> int:
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleUser = frappe.qb.DocType("Press Role User")
	return (
		frappe.qb.from_(PressRole)
		.inner_join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.select(Count(PressRole.name).as_("count"))
		.where(PressRole.team == team)
		.where(PressRoleUser.user == frappe.session.user)
		.run(as_dict=True)
		.pop()
		.get("count")
	)


def is_allowed(allowed: set[tuple[str, str]] | None, owner: str, repository: str) -> bool:
	return allowed is None or (str(owner).lower(), str(repository).lower()) in allowed


def check(team: str | None, owner: str, repository: str) -> None:
	"""Throw if the session user may not access `owner/repository` in `team`."""
	if not team:
		return
	if not is_allowed(allowed_repositories(team), owner, repository):
		message = _("Your role does not have access to the repository {0}/{1}.").format(owner, repository)
		frappe.throw(message, frappe.PermissionError)


def check_url(team: str | None, repository_url: str) -> None:
	"""`check` for a repository URL like https://github.com/owner/repo."""
	# A URL without owner/repo checks as ("", ""), which a restricted user never has.
	parts = [*urlparse(repository_url or "").path.strip("/").removesuffix(".git").split("/"), "", ""]
	check(team, parts[0], parts[1])
