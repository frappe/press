# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count


def get_server_site_warranty_count(server: str | None = None, site: str | None = None):
	if not server and not site:
		frappe.throw("One of `site` or `server` is required", frappe.ValidationError)

	if site:
		server = frappe.get_value("Site", site, "server")

	Site = frappe.qb.DocType("Site")
	SitePlan = frappe.qb.DocType("Site Plan")

	query = (
		frappe.qb.from_(Site)
		.left_join(SitePlan)
		.on(Site.plan == SitePlan.name)
		.select(Count(Site.name).as_("supported_sites"))
		.where(
			(SitePlan.support_included == 1) & (SitePlan.dedicated_server_plan == 1) & (Site.server == server)
		)
	)

	return query.run(as_dict=True)[0]["supported_sites"]


def get_server_site_warranty_quota(server: str | None = None, site: str | None = None):
	if not server and not site:
		frappe.throw("One of `site` or `server` is required", frappe.ValidationError)

	if site:
		server = frappe.get_value("Site", site, "server")

	return frappe.get_value("Server", server, "site_warranty_quota")


def get_available_warranty_quota_for_server(server: str | None) -> dict:
	consumed = get_server_site_warranty_count(server)
	total = get_server_site_warranty_quota(server)

	return {
		"consumed": int(consumed),
		"total": int(total),
		"available": total - consumed,
	}


def is_product_warranty_enabled_for_plan_(site_plan: str):
	return frappe.get_value("Site Plan", site_plan, "support_included")


def get_next_allowed_dedicated_product_warranty_change_date(site: str):
	server = frappe.get_value("Site", site, "server")
	COOLDOWN = frappe.get_value("Server", server, "site_warranty_change_cooldown")

	if not COOLDOWN:
		return datetime.now()

	SitePlanChange = DocType("Site Plan Change")
	FromPlan = DocType("Site Plan").as_("from_plan")
	ToPlan = DocType("Site Plan").as_("to_plan")

	query = (
		frappe.qb.from_(SitePlanChange)
		.left_join(FromPlan)
		.on(FromPlan.name == SitePlanChange.from_plan)
		.left_join(ToPlan)
		.on(ToPlan.name == SitePlanChange.to_plan)
		.select(
			SitePlanChange.name,
			SitePlanChange.timestamp,
			FromPlan.support_included.as_("from_support_included"),
			ToPlan.support_included.as_("to_support_included"),
		)
		.where(
			(SitePlanChange.site == site)
			& (SitePlanChange.timestamp >= datetime.now() - timedelta(days=COOLDOWN))
			# both must be dedicated server site plans
			& (FromPlan.dedicated_server_plan == 1)
			& (ToPlan.dedicated_server_plan == 1)
			# support_included changed
			& (FromPlan.support_included != ToPlan.support_included)
		)
		.orderby(SitePlanChange.timestamp, order=frappe.qb.desc)
		.limit(1)
	)

	warranty_changes = query.run(as_dict=True)

	if not warranty_changes:
		return datetime.now()

	return warranty_changes[0]["timestamp"] + timedelta(days=COOLDOWN)


def attach_warranty_info_to_dedicated_servers(servers: list[dict]) -> list[dict]:
	for server in servers:
		if not server.get("public", True):
			server["product_warranty"] = get_available_warranty_quota_for_server(server.get("name"))
	return servers
