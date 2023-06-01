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
		v = self.get(self.value_field)
		if self.value_field == "value_int":
			v = v * 1024 * 1024  # Convert MB to bytes
		return v

	@property
	def dynamic(self) -> bool:
		if not self.get("_dynamic"):
			self._dynamic = frappe.db.get_value(
				"MariaDB Variable", self.mariadb_variable, "dynamic"
			)
		return self._dynamic

	@dynamic.setter
	def dynamic(self, value: bool):
		self._dynamic = value

	@property
	def skippable(self) -> bool:
		return frappe.db.get_value("MariaDB Variable", self.mariadb_variable, "skippable")

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

	def validate_skipped_should_be_skippable(self):
		if self.skip and not self.skippable:
			frappe.throw(
				f"Only skippable variables can be skipped. {self.mariadb_variable} is not skippable"
			)

	def set_default_value_if_no_value(self):
		if self.value:
			return
		default_value = frappe.db.get_value(
			"MariaDB Variable", self.mariadb_variable, "default_value"
		)
		if default_value:
			self.set(f"value_{self.datatype.lower()}", default_value)

	def validate_empty_only_if_skippable(self):
		if not self.value and not self.skippable:
			frappe.throw(f"Value for {self.mariadb_variable} cannot be empty")

	def set_persist_and_unset_dynamic_if_skipped(self):
		if self.skip:
			self.persist = True
			self.dynamic = False

	def validate(  # Is not called by FF. Called manually from database_server.py
		self,
	):
		self.validate_only_one_value_is_set()
		self.set_default_value_if_no_value()
		self.validate_skipped_should_be_skippable()
		self.validate_empty_only_if_skippable()
		self.set_persist_and_unset_dynamic_if_skipped()
		if self.value:
			self.validate_value_field_set_is_correct()
			self.validate_datatype_of_field_is_correct()


def on_doctype_update():
	frappe.db.add_unique(
		"Database Server MariaDB Variable", ("mariadb_variable", "parent")
	)
