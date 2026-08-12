# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from typing import Literal

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.tools.telemetry.config import GUIDES
from press.mcp.utils import system_manager_only


@press_mcp.tool()
@system_manager_only
def list_telemetry_guides() -> list[dict]:
	"""List available telemetry guides."""
	return [
		{
			"key": guide,
			"name": config["name"],
			"title": config["title"],
			"use_for": config["use_for"],
		}
		for guide, config in GUIDES.items()
	]


@press_mcp.tool()
@system_manager_only
def get_telemetry_guide(guide: Literal["Site", "Bench", "Server", "Logs", "Trace ID"]) -> dict:
	"""Get a telemetry guide.

	Valid guide values: Site, Bench, Server, Logs, Trace ID
	"""
	key = guide.lower().replace(" ", "_")
	if key not in GUIDES:
		frappe.throw(f"Unknown guide '{guide}'. Valid: {', '.join(GUIDES)}")
	return GUIDES[key]
