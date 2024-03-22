# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class AppTag(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		github_installation_id: DF.Data | None
		hash: DF.Data | None
		repository: DF.Data | None
		repository_owner: DF.Data | None
		tag: DF.Data | None
		timestamp: DF.Data | None
	# end: auto-generated types

	pass
