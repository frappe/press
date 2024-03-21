# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class TeamMemberImpersonation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		impersonator: DF.Link
		member: DF.Link
		reason: DF.TextEditor
		team: DF.Link
		user: DF.Link
	# end: auto-generated types

	pass
