# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class DeployCandidateApp(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link
		app_name: DF.Data | None
		hash: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pullable_hash: DF.Data | None
		pullable_release: DF.Link | None
		release: DF.Link
		source: DF.Link
		title: DF.Data
		use_cached: DF.Check
	# end: auto-generated types

	dashboard_fields = ["app"]
