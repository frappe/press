# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document

from press.api.client import dashboard_whitelist
from press.guards.role_guard import is_restricted
from press.overrides import get_permission_query_conditions_for_doctype


class TeamMemberResource(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	if TYPE_CHECKING:
		from frappe.types import DF

		document_name: DF.DynamicLink
		document_type: DF.Link
		team: DF.Link
		user: DF.Link
	# end: auto-generated types

	dashboard_fields = ("name", "team", "user", "document_type", "document_name")

	def before_validate(self):
		self.prevent_duplicate()

	def prevent_duplicate(self):
		"""
		Prevent creation of duplicate resources with the same team, user,
		document type, and document.
		"""
		if frappe.db.exists(
			{
				"doctype": self.doctype,
				"team": self.team,
				"user": self.user,
				"document_type": self.document_type,
				"document_name": self.document_name,
			}
		):
			frappe.throw(
				_("A resource with the same team, user, document type, and document name already exists.")
			)

	def validate(self):
		self.validate_user()
		self.validate_document_type()
		self.validate_document_name()

	def validate_user(self):
		"""
		Validate that the user exists and is a member of the team.
		"""
		if not frappe.db.exists({"doctype": "Team Member", "parent": self.team, "user": self.user}):
			frappe.throw(_("User {0} is not a member of the team").format(self.user))

	def validate_document_type(self):
		"""
		Validate that the document type is one of the permitted types.
		"""
		permitted_document_types = ["Server", "Release Group", "Site"]
		if self.document_type not in permitted_document_types:
			frappe.throw(_("Document type must be one of {0}").format(", ".join(permitted_document_types)))

	def validate_document_name(self):
		"""
		Validate that the document exists and is associated with the team.
		"""
		document_team = frappe.db.get_value(self.document_type, self.document_name, "team")
		if document_team != self.team:
			frappe.throw(
				_("Document {0} is not associated with team {1}").format(self.document_name, self.team)
			)

	@dashboard_whitelist()
	def delete(self, *args, **kwargs):
		super().delete(*args, **kwargs)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Team Member Resource")


def has_permission(doc, ptype, user):
	return not is_restricted()
