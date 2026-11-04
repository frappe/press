# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""What a System Manager may move to another team, and how each resource moves.

Operational history (usage records, deploy candidates, migrations, recoveries) stays with the old team.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import frappe

from press.press.doctype.team_change.server_transfer import ServerTransfer
from press.press.doctype.team_change.team_change import transfer_release_group, transfer_site

if TYPE_CHECKING:
	from collections.abc import Callable


def transfer_server(server: str, to_team: str):
	"""Move the server family, and the old team's sites and groups that run only on it."""
	from_team = frappe.db.get_value("Server", server, "team")
	groups, sites = hosted_by_server(server, from_team)
	ServerTransfer(server, from_team).transfer_family(to_team)
	frappe.db.set_value("On-Prem Failover", {"app_server": server}, "team", to_team)
	for group in groups:
		TRANSFER_RULES["Release Group"].move(group, to_team)
	for site in sites:
		TRANSFER_RULES["Site"].move(site, to_team)


def hosted_by_server(server: str, team: str) -> tuple[list[str], list[str]]:
	"""What moves with the server: the team's groups that run only on its family, and its sites on it"""
	sites = frappe.get_all(
		"Site", {"server": server, "team": team, **TRANSFER_RULES["Site"].filters}, pluck="name"
	)
	return groups_only_on_server_family(server, team), sites


def groups_only_on_server_family(server: str, team: str) -> list[str]:
	"""A group that also runs on another server stays with the old team, bench on this server included"""
	family = ServerTransfer(server, team).app_servers
	on_server = group_servers({"server": server})
	spanning = on_server and group_servers({"parent": ("in", on_server), "server": ("not in", family)})
	only_on_family = set(on_server) - set(spanning)
	if not only_on_family:
		return []
	rule = TRANSFER_RULES["Release Group"]
	return frappe.get_all(
		"Release Group", {"name": ("in", list(only_on_family)), "team": team, **rule.filters}, pluck="name"
	)


def group_servers(filters: dict) -> list[str]:
	return frappe.get_all("Release Group Server", {"parenttype": "Release Group", **filters}, pluck="parent")


class TransferRule(NamedTuple):
	move: Callable[[str, str], None]
	filters: dict
	refusal: str


# The one definition of what may move and how; every reader and every move goes through it
TRANSFER_RULES = {
	"Server": TransferRule(
		transfer_server,
		{"status": "Active", "public": 0, "is_self_hosted": 0},
		"Only an Active server that isn't public or self hosted can be transferred.",
	),
	"Release Group": TransferRule(
		transfer_release_group, {"enabled": 1}, "A disabled bench group can't be transferred."
	),
	"Site": TransferRule(
		transfer_site, {"status": ("!=", "Archived")}, "An archived site can't be transferred."
	),
}


def team_resources(team: str) -> list[dict]:
	"""What `team` may move, less the bench groups and sites that move with a listed server anyway"""
	moving_with_servers = resources_moving_with_servers(team)
	return [
		{"document_type": doctype, "document_name": name}
		for doctype, rule in TRANSFER_RULES.items()
		for name in frappe.get_all(doctype, {"team": team, **rule.filters}, pluck="name")
		if (doctype, name) not in moving_with_servers
	]


def resources_moving_with_servers(team: str) -> set[tuple[str, str]]:
	moving: set[tuple[str, str]] = set()
	servers = frappe.get_all("Server", {"team": team, **TRANSFER_RULES["Server"].filters}, pluck="name")
	for server in servers:
		groups, sites = hosted_by_server(server, team)
		moving.update(("Release Group", group) for group in groups)
		moving.update(("Site", site) for site in sites)
	return moving


def validate_can_move(doctype: str, name: str, from_team: str):
	if doctype not in TRANSFER_RULES:
		frappe.throw(
			f"{doctype} can't be transferred to another team. Use a row for a {', '.join(TRANSFER_RULES)}."
		)
	if frappe.db.get_value(doctype, name, "team") != from_team:
		frappe.throw(
			f"{doctype} {name} isn't owned by the source team {from_team}. "
			"Remove the row, or set the Source Team to the team that owns it."
		)
	rule = TRANSFER_RULES[doctype]
	if not frappe.db.exists(doctype, {"name": name, **rule.filters}):
		frappe.throw(f"{rule.refusal} Remove the row for {doctype} {name}.")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def transferable_doctypes(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for the Document Type of a resource row"""
	frappe.only_for("System Manager")
	return [[name] for name in TRANSFER_RULES if txt.lower() in name.lower()]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def transferable_resources(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for the Document Name of a resource row: what the source team may move"""
	frappe.only_for("System Manager")
	if doctype not in TRANSFER_RULES:
		return []
	return frappe.get_all(
		doctype,
		{"team": filters.get("team"), "name": ("like", f"%{txt}%"), **TRANSFER_RULES[doctype].filters},
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)
