# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.data import sbool

try:
	import frappe_mcp
except ImportError:
	frappe_mcp = None


class _MCPUnavailable:
	"""No-op stand-in used when the optional `frappe-mcp` extra is absent.

	`frappe-mcp` is an extra rather than a required dependency: it pins
	pydantic<2.12, whose pydantic-core cannot be built on Python 3.14, and
	Frappe 16 requires Python 3.14.

	Tool modules bind `@press_mcp.tool()` at import time. With no server to
	register against, registration degrades to a no-op and the decorated
	functions stay plain callables, so every module in this package remains
	importable. That matters beyond MCP itself: the incident support agent
	imports `press.mcp.tools.telemetry.clients`, and importing that submodule
	runs this module first.
	"""

	def __init__(self, name):
		self.name = name

	def tool(self, *args, **kwargs):
		if args and callable(args[0]):
			return args[0]
		return lambda fn: fn

	def register(self, *args, **kwargs):
		return self.tool(*args, **kwargs)


mcp = frappe_mcp.MCP("press-mcp") if frappe_mcp else _MCPUnavailable("press-mcp")


@mcp.register()
def handler():
	frappe.only_for("System Manager")

	user_type = frappe.get_cached_value("User", frappe.session.user, "user_type")

	# Allow unchecked access to System Users
	if user_type != "System User":
		frappe.throw("Access not allowed for this URL", frappe.AuthenticationError)

	# MCP feature flag should be enabled
	if not sbool(str(frappe.get_value("Press Settings", None, "enable_mcp"))):
		frappe.throw("MCP is not enabled", frappe.AuthenticationError)

	import press.mcp.tools.actions
	import press.mcp.tools.codebase
	import press.mcp.tools.documents
	import press.mcp.tools.routes
	import press.mcp.tools.telemetry

	_ = press.mcp.tools.codebase
	_ = press.mcp.tools.documents
	_ = press.mcp.tools.routes
	_ = press.mcp.tools.telemetry
	_ = press.mcp.tools.actions
