# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint

from press.access.support_access import has_support_access
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
			return None
		if not has_support_access("Release Group", group):
			is_owned_by_team("Release Group", group, raise_exception=True)

		# The incoming query is scoped to the caller's team, which hides it from support
		return dependencies_of(group, cint(list_args.get("start")), cint(list_args.get("limit")) or 20)


def dependencies_of(group: str, start: int, limit: int) -> list[dict]:
	RGDependency = frappe.qb.DocType("Release Group Dependency")
	BenchDependency = frappe.qb.DocType("Bench Dependency")
	return (
		frappe.qb.from_(RGDependency)
		.join(BenchDependency)
		.on(BenchDependency.name == RGDependency.dependency)
		.where(RGDependency.parenttype == "Release Group")
		.where(RGDependency.parent == group)
		.where(BenchDependency.internal == 0)
		.select(
			RGDependency.name,
			RGDependency.dependency,
			RGDependency.version,
			BenchDependency.title,
			RGDependency.is_custom,
		)
		.orderby(RGDependency.idx)
		.offset(start)
		.limit(limit)
		.run(as_dict=True)
	)
