# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
import copy

from frappe.model.document import Document

DEFAULT_DEPENDENCIES = [
	{"dependency": "NVM_VERSION", "version": "0.36.0"},
	{"dependency": "NODE_VERSION", "version": "18.16.0"},
	{"dependency": "PYTHON_VERSION", "version": "3.11"},
	{"dependency": "WKHTMLTOPDF_VERSION", "version": "0.12.5"},
	{"dependency": "BENCH_VERSION", "version": "5.22.1"},
]


class FrappeVersion(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.frappe_version_dependency.frappe_version_dependency import (
			FrappeVersionDependency,
		)

		default: DF.Check
		dependencies: DF.Table[FrappeVersionDependency]
		number: DF.Int
		public: DF.Check
		status: DF.Literal["Develop", "Beta", "Stable", "End of Life"]
	# end: auto-generated types

	def before_insert(self):
		self.set_dependencies()

	def set_dependencies(self):
		dependencies = copy.deepcopy(DEFAULT_DEPENDENCIES)
		if not hasattr(self, "dependencies") or not self.dependencies:
			self.extend("dependencies", dependencies)
