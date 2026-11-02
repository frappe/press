# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.utils import system_manager_only


@press_mcp.tool()
@system_manager_only
def clear_site_cache(site: str, confirm: bool = False) -> dict:
	"""Clear Redis cache for a site.

	Safe, zero-downtime. Cache rebuilds automatically on next request.

	Pass confirm=True to execute. Without it, returns a dry-run summary.
	"""
	if not frappe.db.exists("Site", site):
		frappe.throw(f"Site {site!r} not found")

	if not confirm:
		return {
			"action": "clear_site_cache",
			"site": site,
			"impact": "Clears Redis cache. Zero downtime.",
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	frappe.get_doc("Site", site).clear_site_cache()
	return {"action": "clear_site_cache", "site": site, "status": "triggered"}


@press_mcp.tool()
@system_manager_only
def activate_site(site: str, confirm: bool = False) -> dict:
	"""Activate an inactive, broken, or suspended site.

	Removes maintenance mode and marks the site Active (or Broken if
	unresponsive). Rejects if site is already Active.

	Pass confirm=True to execute. Without it, returns a dry-run summary.
	"""
	if not frappe.db.exists("Site", site):
		frappe.throw(f"Site {site!r} not found")

	site_doc = frappe.get_doc("Site", site)

	if site_doc.status not in ("Inactive", "Broken", "Suspended"):
		frappe.throw(
			f"Site {site!r} has status {site_doc.status!r}. Can only activate Inactive, Broken, or Suspended sites."
		)

	if not confirm:
		return {
			"action": "activate_site",
			"site": site,
			"current_status": site_doc.status,
			"impact": "Removes maintenance mode and marks site Active (or Broken if unresponsive).",
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	site_doc.activate()
	site_doc.save()
	return {"action": "activate_site", "site": site, "status": "triggered"}
