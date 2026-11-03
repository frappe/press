# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import frappe
from frappe.utils import add_to_date, fmt_money, now_datetime

from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.server.server import Server
from press.press.doctype.team.team import Team
from press.press.doctype.team_change.team_change import transfer_release_group, transfer_site

if TYPE_CHECKING:
	from collections.abc import Sequence

RUNNING_JOB_STATUSES = ("Pending", "Running")
RUNNING_JOB_WINDOW_HOURS = 24


class ServerTransfer:
	"""Checks and moves a dedicated server, with everything on it, to another team."""

	def __init__(self, server: str, from_team: str):
		self.server = Server("Server", server)
		self.from_team = from_team

	@cached_property
	def database_servers(self) -> list[str]:
		# An empty `primary` filter matches every primary database server, so stop here
		if not (primary := self.server.database_server):
			return []
		replicas = frappe.get_all(
			"Database Server", {"primary": primary, "status": ("!=", "Archived")}, pluck="name"
		)
		return [primary, *replicas]

	@cached_property
	def groups(self) -> list[str]:
		return frappe.get_all(
			"Release Group Server", {"server": self.server.name}, pluck="parent", distinct=True
		)

	@cached_property
	def sites(self) -> list[frappe._dict]:
		return frappe.get_all(
			"Site", {"server": self.server.name, "status": ("!=", "Archived")}, ["name", "team"]
		)

	def blockers(self, to_team: str) -> list[str]:
		"""Reasons this server can't move to `to_team`. Empty when it can."""
		checks = (
			self._server_state_blocker,
			self._running_jobs_blocker,
			self._linked_servers_blocker,
			self._unpaid_invoices_blocker,
			self._other_teams_sites_blocker,
			self._other_teams_groups_blocker,
			self._multi_server_groups_blocker,
		)
		reasons = [reason for check in checks if (reason := check())]
		if reason := self._servers_not_enabled_blocker(to_team):
			reasons.append(reason)
		return reasons

	def _server_state_blocker(self) -> str | None:
		if self.server.is_self_hosted:
			return "Self-hosted servers can't be transferred."
		if self.server.is_managed_database:
			return "Servers with a managed database can't be transferred. Please raise a support ticket."
		if self.server.status != "Active":
			return f"The server must be Active. It is {self.server.status} right now."
		return None

	def _running_jobs_blocker(self) -> str | None:
		# Only server operations like resize or snapshot; site jobs are safe, and older jobs are stuck
		running = frappe.db.exists(
			"Press Job",
			{
				"server": ("in", [self.server.name, *self.database_servers]),
				"status": ("in", RUNNING_JOB_STATUSES),
				"creation": (">", add_to_date(now_datetime(), hours=-RUNNING_JOB_WINDOW_HOURS)),
			},
		)
		if running:
			return "A server operation (like a resize or snapshot) is running. Wait for it to finish, then try again."
		return None

	def _linked_servers_blocker(self) -> str | None:
		if self.server.secondary_server or self.server.enable_on_prem_failover_support:
			return "Turn off autoscaling and on-prem failover before transferring this server."
		return None

	def _unpaid_invoices_blocker(self) -> str | None:
		if Team("Team", self.from_team).has_unpaid_invoices():
			return "Please pay your unpaid invoices before transferring this server."
		return None

	def _other_teams_sites_blocker(self) -> str | None:
		if others := [site["name"] for site in self.sites if site["team"] != self.from_team]:
			return f"Sites of other teams are on this server: {', '.join(others)}. Move them off first."
		return None

	def _other_teams_groups_blocker(self) -> str | None:
		others = frappe.get_all(
			"Release Group",
			{"name": ("in", self.groups), "team": ("!=", self.from_team), "enabled": 1},
			pluck="title",
		)
		if others:
			return f"Bench groups of other teams are on this server: {', '.join(others)}."
		return None

	def _multi_server_groups_blocker(self) -> str | None:
		spanning = frappe.get_all(
			"Release Group Server",
			{"parent": ("in", self.groups), "server": ("!=", self.server.name)},
			pluck="parent",
			distinct=True,
		)
		if spanning:
			titles = frappe.get_all("Release Group", {"name": ("in", spanning)}, pluck="title")
			return (
				f"These bench groups also run on other servers: {', '.join(titles)}. "
				"Please raise a support ticket to transfer this server."
			)
		return None

	def _servers_not_enabled_blocker(self, to_team: str) -> str | None:
		if not can_have_servers(to_team):
			return "The receiving team can't have dedicated servers yet. They need to contact support to enable it."
		return None

	def email_details(self, to_team: str) -> dict:
		"""What the receiving team takes over, shown in the confirmation email."""
		return {
			"monthly_price": self.monthly_price(to_team),
			"site_count": len(self.sites),
			"group_count": len(self.groups),
		}

	def monthly_price(self, to_team: str) -> str:
		"""Monthly price of the server plans, in the receiving team's currency."""
		currency = frappe.db.get_value("Team", to_team, "currency")
		price_field = "price_inr" if currency == "INR" else "price_usd"
		plans = [
			self.server.plan,
			*(frappe.db.get_value("Database Server", d, "plan") for d in self.database_servers),
		]
		total = sum(frappe.db.get_value("Server Plan", plan, price_field) or 0 for plan in plans if plan)
		return fmt_money(total, currency=currency)

	def transfer(self, to_team: str):
		self._transfer_hosted(to_team)
		self.transfer_family(to_team)

	def _transfer_hosted(self, to_team: str):
		# The blockers made sure nothing here runs on another server or belongs to another team
		own_groups = frappe.get_all(
			"Release Group", {"name": ("in", self.groups), "team": self.from_team}, pluck="name"
		)
		for group in own_groups:
			transfer_release_group(group, to_team)
		for site in self.sites:
			if site["team"] == self.from_team:
				transfer_site(site["name"], to_team)

	def transfer_family(self, to_team: str):
		"""Move the servers, their machines, subscriptions and snapshots, but not what runs on them."""
		self._transfer_machines(to_team)
		self._transfer_snapshots(to_team)
		self._remove_old_team_settings()

	@cached_property
	def app_servers(self) -> list[str]:
		"""The server and its autoscaling secondary, which the customer blockers refuse."""
		return [name for name in (self.server.name, self.server.secondary_server) if name]

	def _transfer_machines(self, to_team: str):
		machines = {"Server": self.app_servers, "Database Server": self.database_servers}
		for doctype, names in machines.items():
			virtual_machines = frappe.get_all(doctype, {"name": ("in", names)}, pluck="virtual_machine")
			_set_team(doctype, names, to_team)
			_set_team("Virtual Machine", virtual_machines, to_team)

	def _transfer_snapshots(self, to_team: str):
		snapshots = frappe.get_all("Server Snapshot", {"app_server": self.server.name}, pluck="name")
		_set_team("Server Snapshot", snapshots, to_team)

	def _remove_old_team_settings(self):
		frappe.db.delete("Press Role Permission", {"server": self.server.name})
		# Without its own contacts, the server falls back to the new team's contacts
		frappe.db.delete("Communication Info", {"parenttype": "Server", "parent": self.server.name})
		get_communication_info.clear_cache()


def can_have_servers(team: str) -> bool:
	return bool(frappe.db.get_value("Team", team, "servers_enabled"))


def _set_team(doctype: str, names: Sequence[str | None], to_team: str):
	"""Move the records, and the subscriptions that bill for them, to `to_team`."""
	if not (names := [name for name in names if name]):
		return
	frappe.db.set_value(doctype, {"name": ("in", names)}, "team", to_team)
	frappe.db.set_value(
		"Subscription", {"document_type": doctype, "document_name": ("in", names)}, "team", to_team
	)
