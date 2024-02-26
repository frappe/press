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
	def before_insert(self):
		self.set_dependencies()

	def set_dependencies(self):
		dependencies = copy.deepcopy(DEFAULT_DEPENDENCIES)
		if not hasattr(self, "dependencies") or not self.dependencies:
			self.extend("dependencies", dependencies)
