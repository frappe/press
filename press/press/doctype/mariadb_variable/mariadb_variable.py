# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.press.doctype.database_server.database_server import DatabaseServer


class MariaDBVariable(Document):
	def get_default_value(self):
		if not (value := self.default_value):
			frappe.throw("Default Value is required")
		match self.datatype:
			case "Int":
				return int(value)
			case "Float":
				return float(value)
			case "Bool":
				return bool(value)
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
		value = self.get_default_value()
		server: DatabaseServer = frappe.get_doc("Database Server", server_name)
		server.add_mariadb_variable(self.name, f"value_{self.datatype.lower()}", value)
