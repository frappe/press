# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe_mcp

mcp = frappe_mcp.MCP("press-mcp")


@mcp.register()
def handler():
	import press.mcp.tools.documents

	_ = press.mcp.tools.documents
