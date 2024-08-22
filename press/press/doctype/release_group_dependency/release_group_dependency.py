# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.api.client import is_owned_by_team


class ReleaseGroupDependency(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		dependency: DF.Data
		is_custom: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		version: DF.Data
	# end: auto-generated types

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		if not filters or not (group := filters.get("parent")):
			return
		is_owned_by_team("Release Group", group, raise_exception=True)

		RGDependency = frappe.qb.DocType("Release Group Dependency")
		BenchDependency = frappe.qb.DocType("Bench Dependency")

		query = (
			query.join(BenchDependency)
			.on(BenchDependency.name == RGDependency.dependency)
			.where(BenchDependency.internal == 0)
			.select(
				RGDependency.dependency,
				RGDependency.version,
				BenchDependency.title,
				RGDependency.is_custom,
			)
		)
		dependencies = query.run(as_dict=True)
		return dependencies
