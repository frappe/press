# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

from press.press.doctype.team_change.balance import move_balance, settle_open_invoices
from press.press.doctype.team_change.server_transfer import can_have_servers
from press.press.doctype.team_change.team_change import validate_team_enabled
from press.press.doctype.team_change.transfer import TRANSFER_RULES, team_resources, validate_can_move

if TYPE_CHECKING:
	from press.press.doctype.team_change.team_change import TeamChange


class AdminTransfer:
	"""A System Manager's move of the ticked resource rows of a Team Change, run from desk."""

	def __init__(self, team_change: TeamChange):
		self.team_change = team_change

	@property
	def documents(self) -> list[tuple[str, str]]:
		return [(row.document_type, row.document_name) for row in self.team_change.resources if row.include]

	def validate(self):
		documents = self.documents
		if len(documents) != len(set(documents)):
			frappe.throw("A resource is listed more than once. Remove the duplicate row and save again.")
		for doctype, name in documents:
			validate_can_move(doctype, name, self.team_change.from_team)
		validate_team_enabled(self.team_change.to_team)
		self.validate_servers_allowed()
		self.validate_balance_move()

	def validate_servers_allowed(self):
		to_team = self.team_change.to_team
		if any(doctype == "Server" for doctype, _ in self.documents) and not can_have_servers(to_team):
			frappe.throw(
				f"The team {to_team} can't have dedicated servers, so a server can't move to it. "
				"Turn on Servers Enabled for the team, or remove the Server rows."
			)

	def validate_balance_move(self):
		team_change = self.team_change
		if not team_change.move_balance:
			return
		if team_change.transfer_type != "Full Account":
			frappe.throw(
				"The credit balance can be moved only in a full account transfer. "
				"Set Transfer Type to Full Account, or clear Settle Invoices and Move Credit Balance."
			)
		from_currency, to_currency = (
			frappe.db.get_value("Team", team, "currency")
			for team in (team_change.from_team, team_change.to_team)
		)
		if from_currency == to_currency:
			team_change.exchange_rate = 1
		elif not team_change.exchange_rate or team_change.exchange_rate <= 0:
			frappe.throw(
				f"The teams use different currencies. Enter the exchange rate from {from_currency} to {to_currency}."
			)

	def move(self):
		for doctype, name in self.documents:
			TRANSFER_RULES[doctype].move(name, self.team_change.to_team)
		if self.team_change.move_balance:
			self.move_credit_balance()

	def move_credit_balance(self):
		team_change = self.team_change
		settle_open_invoices(team_change.from_team)
		remark = f"Moved from team {team_change.from_team} to {team_change.to_team} by Team Change {team_change.name}"
		moved = move_balance(team_change.from_team, team_change.to_team, team_change.exchange_rate, remark)
		team_change.db_set("balance_moved", moved)

	def fetch_resources(self):
		"""List every resource of the source team, for the admin to clear Include on what stays"""
		if self.team_change.transfer_type != "Full Account":
			frappe.throw(
				"Fetch Resources is for a full account transfer. Add specific resources as rows instead."
			)
		self.team_change.set("resources", team_resources(self.team_change.from_team))
		self.team_change.save()

	def transfer(self):
		if not self.documents and not self.team_change.move_balance:
			frappe.throw(
				"Nothing is included in this transfer. Add at least one resource to transfer, or tick Include on a row."
			)
		self.team_change.update(
			{
				"transfer_completed": 1,
				"transferred_by": frappe.session.user,
				"transferred_on": frappe.utils.now_datetime(),
			}
		)
		self.team_change.save()
