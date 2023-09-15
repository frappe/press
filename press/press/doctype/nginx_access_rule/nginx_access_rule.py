# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class NginxAccessRule(Document):
	@staticmethod
	def create_nginx_access_rule(server, server_type, ip_address, action):
		_server, _server_type = get_proxy_server(server, server_type)

		try:
			frappe.get_doc(
				{
					"doctype": "Nginx Access Rule",
					"server": _server,
					"server_type": _server_type,
					"ip_address": ip_address,
					"action": action,
				}
			).insert(ignore_permissions=True)

		except frappe.DuplicateEntryError:
			pass

	@staticmethod
	def fetch_nginx_access_rules(server, server_type):
		_server, _server_type = get_proxy_server(server, server_type)

		return frappe.get_all(
			"Nginx Access Rule",
			filters={"server": _server, "server_type": _server_type},
			fields=["name", "ip_address", "action as rule", "server_type", "server"],
		)


def get_proxy_server(server, server_type):
	try:
		proxy_server = frappe.db.get_value(server_type, server, "proxy_server", cache=True)
		return proxy_server, "Proxy Server"

	except frappe.DoesNotExistError:
		pass

	return server, server_type
