# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Which team owns a document reached through the dashboard API.

`press.api.client` acts for exactly one team, so before it reads or writes a
document it has to name the team that owns it. Doctypes carrying a `team` field
answer that themselves. Every other doctype in `ALLOWED_DOCTYPES` declares its
answer here, and an undeclared doctype is refused.

Defaulting to "allow" is what let any signed-in user read and edit every other
team's Support Access, Partner Lead and SSH keys — frappe/security#183.
"""

from __future__ import annotations

import frappe
from frappe.query_builder import Criterion

# Reference data. The same rows for every team, so any signed-in user may read
# them and nobody may write them from the dashboard. Nothing derived from a
# single team's data belongs here.
GLOBAL_DOCTYPES = frozenset(
	{
		"Agent Job Type",
		"Frappe Version",
		"Partner Lead Origin",
		"Partner Lead Type",
		"Partner Tier",
		"Press Settings",
		"Product Trial",
		"Server Plan",
		"Site Plan",
	}
)

# Doctypes that name their owning team in fields other than `team`. The document
# belongs to every team those fields point at.
TEAM_FIELDS: dict[str, tuple[str, ...]] = {
	"Partner Approval Request": ("requested_by", "partner"),
	"Partner Audit": ("partner_team",),
	"Partner Lead": ("partner_team",),
	"Partner Non Conformance": ("partner_team",),
	"Partner Payment Payout": ("partner",),
	"Support Access": ("requested_team", "target_team"),
	"Team": ("name", "parent_team"),
}

# Doctypes owned by a user instead of a team.
USER_FIELDS: dict[str, str] = {
	"User SSH Key": "user",
}

# Doctypes owned through a link to a document that carries a `team` field.
LINKED_OWNERS: dict[str, tuple[str, str]] = {
	"Agent Job": ("bench", "Bench"),
	"Auto Scale Record": ("primary_server", "Server"),
	"Marketplace App Plan": ("app", "Marketplace App"),
	"New Bench Queue": ("group", "Release Group"),
	"Server Firewall": ("server_id", "Server"),
}

# Doctypes owned through a dynamic link, where another field names the doctype
# being linked to.
DYNAMICALLY_LINKED_OWNERS: dict[str, tuple[str, str]] = {
	"Ansible Play": ("server", "server_type"),
}

# Doctypes whose `get_list_query` does the scoping itself, because a job or play
# can hang off a site, a bench, a group or a server and no single join covers
# all four. Both refuse to list anything unless the caller names one it owns.
SELF_SCOPED_DOCTYPES = frozenset({"Agent Job", "Ansible Play"})


def current_team() -> str:
	return frappe.local.team().name


def has_document_access(doctype: str, name: str, doc=None) -> bool:
	"""Whether the current team owns this document."""
	if doctype in GLOBAL_DOCTYPES:
		return True

	meta = frappe.get_meta(doctype)
	if meta.istable:
		return has_parent_access(doctype, name)

	if meta.has_field("team"):
		team = doc.team if doc else frappe.db.get_value(doctype, name, "team")
		return bool(team) and team == current_team()

	if doctype in TEAM_FIELDS:
		return current_team() in owning_teams(doctype, name)

	if doctype in USER_FIELDS:
		return frappe.db.get_value(doctype, name, USER_FIELDS[doctype]) == frappe.session.user

	if doctype in LINKED_OWNERS:
		return has_linked_access(doctype, name)

	if doctype in DYNAMICALLY_LINKED_OWNERS:
		return has_dynamically_linked_access(doctype, name)

	return False


def owning_teams(doctype: str, name: str) -> set[str]:
	values = frappe.db.get_value(doctype, name, TEAM_FIELDS[doctype], as_dict=True) or {}
	return {team for team in values.values() if team}


def has_parent_access(doctype: str, name: str) -> bool:
	"""A child row belongs to whoever owns the row it hangs off."""
	parent = frappe.db.get_value(doctype, name, ["parenttype", "parent"], as_dict=True)
	if not (parent and parent.parenttype and parent.parent):
		return False

	return has_document_access(parent.parenttype, parent.parent)


def has_linked_access(doctype: str, name: str) -> bool:
	link_field, linked_doctype = LINKED_OWNERS[doctype]
	linked_name = frappe.db.get_value(doctype, name, link_field)

	return bool(linked_name) and has_document_access(linked_doctype, linked_name)


def has_dynamically_linked_access(doctype: str, name: str) -> bool:
	link_field, doctype_field = DYNAMICALLY_LINKED_OWNERS[doctype]
	link = frappe.db.get_value(doctype, name, [link_field, doctype_field], as_dict=True)
	if not (link and link[link_field] and link[doctype_field]):
		return False

	return has_document_access(link[doctype_field], link[link_field])


def team_condition(doctype: str, table):
	"""Condition matching rows of `doctype` that the current team owns."""
	fieldnames: tuple[str, ...] = TEAM_FIELDS.get(doctype, ())
	if frappe.get_meta(doctype).has_field("team"):
		fieldnames = ("team",)

	if not fieldnames:
		return None

	return Criterion.any([table[fieldname] == current_team() for fieldname in fieldnames])


def scope_query(doctype: str, meta, filters: dict, query):
	"""Restrict a list query to the documents the current team owns.

	Doctypes with a `team` field are scoped by the caller, which has its own
	opt-out for system users and support agents. Everything else is scoped here,
	and a doctype nothing can scope is not listable at all.
	"""
	if meta.has_field("team") or doctype in GLOBAL_DOCTYPES or doctype in SELF_SCOPED_DOCTYPES:
		return query

	if frappe.local.system_user():
		return query

	if meta.istable:
		return scope_by_parent(doctype, filters, query)

	if doctype in TEAM_FIELDS:
		return query.where(team_condition(doctype, frappe.qb.DocType(doctype)))

	if doctype in USER_FIELDS:
		return query.where(frappe.qb.DocType(doctype)[USER_FIELDS[doctype]] == frappe.session.user)

	if doctype in LINKED_OWNERS:
		return scope_by_link(doctype, query)

	refuse_to_list(doctype)
	return None


def refuse_to_list(doctype: str):
	frappe.throw(f"{doctype} cannot be listed from the dashboard", frappe.PermissionError)


def scope_by_parent(doctype: str, filters: dict, query):
	"""Join the parent the caller named and keep only the rows its team owns.

	The caller picks `parenttype`, so the join is only sound as long as the rows
	it authorizes actually hang off that doctype. `get_list` already filters on
	the stored `parenttype`, but the join repeats it rather than trusting a
	filter built three functions away.
	"""
	parenttype = str((filters or {}).get("parenttype") or "")
	if not parenttype:
		refuse_to_list(doctype)

	ParentDocType = frappe.qb.DocType(parenttype)
	ChildDocType = frappe.qb.DocType(doctype)

	condition = team_condition(parenttype, ParentDocType)
	if condition is None:
		refuse_to_list(doctype)

	return (
		query.join(ParentDocType)
		.on(ParentDocType.name == ChildDocType.parent)
		.where(ChildDocType.parenttype == parenttype)
		.where(condition)
	)


def scope_by_link(doctype: str, query):
	link_field, linked_doctype = LINKED_OWNERS[doctype]
	DocType = frappe.qb.DocType(doctype)
	LinkedDocType = frappe.qb.DocType(linked_doctype)

	return (
		query.inner_join(LinkedDocType)
		.on(LinkedDocType.name == DocType[link_field])
		.where(LinkedDocType.team == current_team())
	)
