# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReleaseGroupDependency(Document):
	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		RGDependency = frappe.qb.DocType("Release Group Dependency")
		BenchDependency = frappe.qb.DocType("Bench Dependency")

		if filters and filters.get("group"):
			query = (
				query.join(BenchDependency)
				.on(BenchDependency.name == RGDependency.dependency)
				.where(RGDependency.parent == filters.get("group"))
				.where(RGDependency.parenttype == "Release Group")
				.where(BenchDependency.internal == 0)
				.select(RGDependency.dependency, RGDependency.version, BenchDependency.title)
			)
		dependencies = query.run(as_dict=True)

		return dependencies
