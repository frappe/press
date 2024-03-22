# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class TeamMemberDeletionRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		anon_team_member: DF.Data | None
		deletion_status: DF.Literal["Pending", "Deleted"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		team_member: DF.Link | None
	# end: auto-generated types

	pass
