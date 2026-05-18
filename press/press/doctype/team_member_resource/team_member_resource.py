# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.team.team import Team


class TeamMemberResource(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.
	if TYPE_CHECKING:
		from frappe.types import DF

		document: DF.DynamicLink
		document_type: DF.Link
		team: DF.Link
		user: DF.Link
	# end: auto-generated types

	def before_validate(self):
		self.prevent_duplicate()

	def prevent_duplicate(self):
		if frappe.db.exists(
			{
				"doctype": self.doctype,
				"team": self.team,
				"user": self.user,
				"document_type": self.document_type,
				"document": self.document,
			}
		):
			frappe.throw(
				_("A resource with the same team, user, document type, and document already exists.")
			)

	def validate(self):
		self.validate_team()
		self.validate_user()
		self.validate_document_type()
		self.validate_document()

	def validate_team(self):
		# Check if the current user is a member of the team.
		if not frappe.db.exists({"doctype": "Team Member", "parent": self.team, "user": frappe.session.user}):
			frappe.throw(_("Current user must be a member of the team to assign resources."))
		# Check if the current user has the necessary permissions to assign resources.
		team: Team = frappe.get_doc("Team", self.team)
		if not (team.is_team_owner() or team.is_admin_user()):
			frappe.throw(_("Current user must be a team owner or admin to assign resources."))

	def validate_user(self):
		if not frappe.db.exists({"doctype": "Team Member", "parent": self.team, "user": self.user}):
			frappe.throw(_("User {0} is not a member of the team").format(self.user))

	def validate_document_type(self):
		permitted_document_types = ["Server", "Bench", "Site"]
		if self.document_type not in permitted_document_types:
			frappe.throw(_("Document type must be one of {0}").format(", ".join(permitted_document_types)))

	def validate_document(self):
		document_team = frappe.db.get_value(self.document_type, self.document, "team")
		if document_team != self.team:
			frappe.throw(_("Document {0} is not associated with team {1}").format(self.document, self.team))
