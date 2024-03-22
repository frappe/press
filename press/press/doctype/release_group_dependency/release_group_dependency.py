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
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		version: DF.Data
	# end: auto-generated types

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		RGDependency = frappe.qb.DocType("Release Group Dependency")
		BenchDependency = frappe.qb.DocType("Bench Dependency")
		group = filters.get("parent") if filters else None
		if group:
			is_owned_by_team("Release Group", group, raise_exception=True)
			query = (
				query.join(BenchDependency)
				.on(BenchDependency.name == RGDependency.dependency)
				.where(BenchDependency.internal == 0)
				.select(RGDependency.dependency, RGDependency.version, BenchDependency.title)
			)
			dependencies = query.run(as_dict=True)
			return dependencies
