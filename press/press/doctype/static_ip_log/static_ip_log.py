# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StaticIPLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		server: DF.DynamicLink
		server_type: DF.Link
		static_ip: DF.Data
		status: DF.Literal["Attached", "Detached"]
	# end: auto-generated types

	def validate(self):
		if self.server_type not in ("Server", "Database Server"):
			frappe.throw("Server Type must be either 'Server' or 'Database Server'")


def create_static_ip_log(server: str, server_type: str, static_ip: str, status: str = "Attached"):
	return frappe.get_doc(
		{
			"doctype": "Static IP Log",
			"server": server,
			"server_type": server_type,
			"static_ip": static_ip,
			"status": status,
		}
	).insert(ignore_permissions=True)


def create_static_ip_log_if_applicable(fn):
	def wrapper(self):
		static_ip = self.get("static_ip")
		result = fn(self)

		if self.cloud_provider == "AWS EC2":
			create_static_ip_log(
				server=self.name,
				server_type=self.doctype,
				static_ip=self.static_ip or static_ip,
				status="Attached" if self.static_ip else "Detached",
			)

		return result

	return wrapper
