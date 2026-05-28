# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
import frappe_mcp

mcp = frappe_mcp.MCP("press-mcp")


@mcp.register()
def handler():
	frappe.only_for("System Manager")

	user_type = frappe.get_cached_value("User", frappe.session.user, "user_type")

	# Allow unchecked access to System Users
	if user_type != "System User":
		frappe.throw("Access not allowed for this URL", frappe.AuthenticationError)

	import press.mcp.tools.documents
	import press.mcp.tools.telemetry

	_ = press.mcp.tools.documents
	_ = press.mcp.tools.telemetry
