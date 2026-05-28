# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.utils import system_manager_only
from press.utils import poly_get_doctype

_PROXY_REFUSED = (
	"Proxy server restarts are never allowed via MCP — "
	"they affect all sites on the cluster. Use the dashboard or escalate manually."
)


@press_mcp.tool()
@system_manager_only
def reboot_server(server: str, confirm: bool = False) -> dict:
	"""Reboot an app or database server.

	For AWS EC2: uses serial console reboot (sysrq) — harder reset that
	recovers hung kernels. For all other providers: normal VM reboot via
	the provider API.

	Proxy servers are never rebooted via this tool.

	Pass confirm=True to execute. Without it, returns a dry-run summary.
	"""
	if frappe.db.exists("Proxy Server", server):
		frappe.throw(_PROXY_REFUSED)

	server_doctype = poly_get_doctype(["Server", "Database Server"], server)
	server_doc = frappe.get_doc(server_doctype, server)

	provider = server_doc.provider
	is_aws = provider == "AWS EC2"
	method = "serial console reboot (sysrq)" if is_aws else f"VM reboot via {provider}"

	if not confirm:
		return {
			"action": "reboot_server",
			"server": server,
			"server_type": server_doctype,
			"provider": provider,
			"method": method,
			"impact": (
				"Hard reboot via serial console. Causes downtime for all benches/sites on this server."
				if is_aws
				else "Normal VM reboot. Causes downtime for all benches/sites on this server."
			),
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	if is_aws:
		server_doc.reboot_with_serial_console()
	else:
		server_doc.reboot()

	return {
		"action": "reboot_server",
		"server": server,
		"server_type": server_doctype,
		"provider": provider,
		"method": method,
		"status": "triggered",
	}
