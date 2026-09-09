import json

import frappe

from press.press.doctype.site.site import Site
from press.utils import log_error


def execute():
	"""Only two plan names were exempt, so most dedicated server sites got a rate limit."""
	plans = frappe.get_all("Site Plan", filters={"dedicated_server_plan": 1}, pluck="name")
	sites = frappe.get_all(
		"Site",
		filters={"plan": ["in", plans], "status": ["!=", "Archived"]},
		fields=["name", "config"],
	)
	for site in sites:
		if not json.loads(site.config or "{}").get("rate_limit"):
			continue
		try:
			Site("Site", site.name).update_site_config({"rate_limit": {}})
			frappe.db.commit()
		except Exception:
			# one unreachable bench must not stop the migration
			frappe.db.rollback()
			log_error("Dedicated Site Rate Limit Patch Failure", site=site.name)
		else:
			print(f"Reset rate limit: {site.name}")
