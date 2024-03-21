# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MarketplaceAppVersion(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		source: DF.Link
		version: DF.Link
	# end: auto-generated types

	dashboard_fields = ["name", "version", "source"]

	@staticmethod
	def get_list_query(query):
		AppSource = frappe.qb.DocType("App Source")
		MarketplaceAppVersion = frappe.qb.DocType("Marketplace App Version")
		query = (
			query.select(AppSource.branch, AppSource.repository_owner, AppSource.repository)
			.left_join(AppSource)
			.on(MarketplaceAppVersion.source == AppSource.name)
		)
		return query
