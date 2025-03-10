# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.utils import has_role

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer


class MariaDBVariable(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		available_values: DF.SmallText
		configurable_by_user: DF.Check
		datatype: DF.Literal["Int", "Float", "Str"]
		default_value: DF.Data | None
		doc_section: DF.Literal["server", "replication-and-binary-log", "innodb"]
		dynamic: DF.Check
		set_on_new_servers: DF.Check
		skippable: DF.Check
	# end: auto-generated types

	@property
	def available_values_list(self) -> list[str]:
		values = self.available_values.split("\n")
		return [v.strip() for v in values if v.strip()]

	def get_default_value(self):
		if not (value := self.default_value):
			frappe.throw("Default Value is required")
		match self.datatype:
			case "Int":
				return int(value)
			case "Float":
				return float(value)
		return value

	@frappe.whitelist()
	def set_on_all_servers(self):
		value = self.get_default_value()
		servers = frappe.get_all(
			"Database Server", {"status": "Active", "is_self_hosted": False}, pluck="name"
		)
		for server_name in servers:
			server: DatabaseServer = frappe.get_doc("Database Server", server_name)
			server.add_mariadb_variable(self.name, f"value_{self.datatype.lower()}", value)

	@frappe.whitelist()
	def set_on_server(self, server_name):
		if not self.configurable_by_user and not has_role("System Manager"):
			frappe.throw(f"{self.name} is not configurable by user")
		value = self.get_default_value()
		server: DatabaseServer = frappe.get_doc("Database Server", server_name)
		server.add_mariadb_variable(self.name, f"value_{self.datatype.lower()}", value)

	@staticmethod
	def get_available_configurable_variables(
		doc_section: str, include_non_dynamic_variables: bool = False
	) -> list[dict]:
		"""
		Get a list of configurable MariaDB variables of given doc_section.

		Args:
			doc_section (str): doc_section of variables to get.
			include_non_dynamic_variables (bool, optional): Whether to include
				variables that are not dynamic. Defaults to False.

		NOTE: During applying changes in dynamic system variables of mariadb server, it would restart the MariaDB server

		Returns:
			list[dict]: List of dictionaries with keys "name", "doc_section",
				"available_values" and "available_values_list".
		"""
		filters = {"configurable_by_user": 1, "doc_section": doc_section}
		if not include_non_dynamic_variables:
			filters.update({"dynamic": 0})
		variables: list[dict] = frappe.get_all(
			"MariaDB Variable",
			filters={"configurable_by_user": 1, "doc_section": doc_section},
			fields=["name", "datatype", "available_values"],
		)
		for variable in variables:
			variable.available_values_list = [
				v.strip() for v in variable.available_values.split("\n") if v.strip()
			]
			del variable["available_values"]
		return variables
