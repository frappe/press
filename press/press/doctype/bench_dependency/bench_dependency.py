# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BenchDependency(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.bench_dependency_version.bench_dependency_version import (
			BenchDependencyVersion,
		)

		internal: DF.Check
		supported_versions: DF.Table[BenchDependencyVersion]
		title: DF.Data | None
	# end: auto-generated types

	pass
