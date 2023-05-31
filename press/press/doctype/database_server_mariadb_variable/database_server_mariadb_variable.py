# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe.model.document import Document


class DatabaseServerMariaDBVariable(Document):
	def get_datatype(self) -> str:
		return frappe.db.get_value("MariaDB Variable", self.mariadb_variable, "datatype")

	@property
	def value_fields(self):
		return list(filter(lambda x: x.startswith("value_"), self.as_dict().keys()))

	@property
	def value(self) -> Any:
		"""Return the first value field that has a value"""
		for f in self.value_fields:
			if value := self.get(f):
				return value

	def validate_only_one_value_is_set(self):
		if sum([bool(self.get(f)) for f in self.value_fields]) > 1:
			frappe.throw("Only one value can be set for MariaDB system variable")

	def validate_datatype_of_field_is_correct(self):
		datatype = self.get_datatype()
		if type(self.value).__name__ != datatype.lower():
			frappe.throw(f"Value for {self.mariadb_variable} must be {datatype}")

	def validate(self):
		self.validate_only_one_value_is_set()
		self.validate_datatype_of_field_is_correct()


def on_doctype_update():
	frappe.db.add_unique(
		"Database Server MariaDB Variable", ("mariadb_variable", "parent")
	)
