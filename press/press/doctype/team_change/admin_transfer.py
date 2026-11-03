# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

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

	def move(self):
		for doctype, name in self.documents:
			TRANSFER_RULES[doctype].move(name, self.team_change.to_team)

	def fetch_resources(self):
		"""List every resource of the source team, for the admin to clear Include on what stays"""
		if self.team_change.transfer_type != "Full Account":
			frappe.throw(
				"Fetch Resources is for a full account transfer. Add specific resources as rows instead."
			)
		self.team_change.set("resources", team_resources(self.team_change.from_team))
		self.team_change.save()

	def transfer(self):
		if not self.documents:
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
