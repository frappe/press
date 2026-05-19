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
		"""
		Validate that the team exists and that the current user has permission
		to assign resources to the team.
		"""
		# Check if the current user is a member of the team.
		if not frappe.db.exists({"doctype": "Team Member", "parent": self.team, "user": frappe.session.user}):
			frappe.throw(_("Current user must be a member of the team to assign resources."))
		# Check if the current user has the necessary permissions to assign resources.
		team: Team = frappe.get_doc("Team", self.team)
		if not (team.is_team_owner() or team.is_admin_user()):
			frappe.throw(_("Current user must be a team owner or admin to assign resources."))

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
		permitted_document_types = ["Server", "Bench", "Site"]
		if self.document_type not in permitted_document_types:
			frappe.throw(_("Document type must be one of {0}").format(", ".join(permitted_document_types)))

	def validate_document(self):
		"""
		Validate that the document exists and is associated with the team.
		"""
		document_team = frappe.db.get_value(self.document_type, self.document, "team")
		if document_team != self.team:
			frappe.throw(_("Document {0} is not associated with team {1}").format(self.document, self.team))


def sync_press_role(doc, method=None):
	"""
	This is a hook method that synchronizes the resources of team members based
	on `Press Role`s of a team. It is triggered whenever there is a change in
	the `Press Role` doctype, such as when a role is created, updated, or
	deleted. This method is a utility for transitioning from older
	implementations of resource management to the new `Team Member Resource`
	doctype, ensuring that all team members have their resources updated
	according to their assigned `Press Role`s.
	"""
	users = [user.user for user in doc.users]
	team = doc.team

	# Delete all existing `team-member-resource` entries for the team.
	frappe.db.delete("Team Member Resource", {"team": team})

	# Loop through each user and synchronize their resources based on their assigned `Press Role`s.
	for user in users:
		PressRole = frappe.qb.DocType("Press Role")
		PressRoleUser = frappe.qb.DocType("Press Role User")
		PressRoleResource = frappe.qb.DocType("Press Role Resource")

		# Fetch all resources of a user in a team.
		resources = (
			frappe.qb.from_(PressRoleResource)
			.left_join(PressRole)
			.on(PressRole.name == PressRoleResource.parent)
			.left_join(PressRoleUser)
			.on(PressRoleUser.parent == PressRole.name)
			.where(PressRole.team == team)
			.where(PressRoleUser.user == user)
			.select(
				PressRoleResource.document_type,
				PressRoleResource.document_name,
			)
			.run(as_dict=True)
		)

		# Loop through the resources and create `team-member-resource` entries if
		# they don't exist.
		for resource in resources:
			# Check if a `team-member-resource` entry already exists for the team,
			# user, document type, and document.
			document = {
				"doctype": "Team Member Resource",
				"team": team,
				"user": user,
				"document_type": resource.document_type,
				"document": resource.document_name,
			}
			if not frappe.db.exists(document):
				# If the resource does not exist, create a new `team-member-resource` entry.
				frappe.get_doc(document).insert()
