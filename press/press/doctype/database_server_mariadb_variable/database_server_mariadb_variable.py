# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe.model.document import Document


class DatabaseServerMariaDBVariable(Document):
	@property
	def datatype(self) -> str:
		return frappe.db.get_value("MariaDB Variable", self.mariadb_variable, "datatype")

	@property
	def value_fields(self):
		return list(filter(lambda x: x.startswith("value_"), self.as_dict().keys()))

	@property
	def value_field(self):
		"""Return the first value field that has a value"""
		for f in self.value_fields:
			if self.get(f):
				return f

	@property
	def value(self) -> Any:
		"""Return the value of the first value field that has a value"""
		return self.get(self.value_field)

	def validate_only_one_value_is_set(self):
		if sum([bool(self.get(f)) for f in self.value_fields]) > 1:
			frappe.throw("Only one value can be set for MariaDB system variable")

	def validate_datatype_of_field_is_correct(self):
		if type(self.value).__name__ != self.datatype.lower():
			frappe.throw(f"Value for {self.mariadb_variable} must be {self.datatype}")

	def validate_value_field_set_is_correct(self):
		if self.value_field != f"value_{self.datatype.lower()}":
			frappe.throw(
				f"Value field for {self.mariadb_variable} must be value_{self.datatype.lower()}"
			)

	def validate(  # Is not called by FF. Called manually from database_server.py
		self,
	):
		self.validate_only_one_value_is_set()
		self.validate_value_field_set_is_correct()
		self.validate_datatype_of_field_is_correct()


def on_doctype_update():
	frappe.db.add_unique(
		"Database Server MariaDB Variable", ("mariadb_variable", "parent")
	)
