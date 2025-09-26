# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.utils import get_current_team


class DashboardBanner(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.dashboard_banner_dismissal.dashboard_banner_dismissal import (
			DashboardBannerDismissal,
		)

		action: DF.Data | None
		action_label: DF.Data | None
		enabled: DF.Check
		has_action: DF.Check
		help_url: DF.Data | None
		is_dismissible: DF.Check
		is_global: DF.Check
		message: DF.Data | None
		server: DF.Link | None
		site: DF.Link | None
		team: DF.Link | None
		title: DF.Data | None
		type: DF.Literal["Info", "Success", "Error", "Warning"]
		type_of_scope: DF.Literal["Team", "Server", "Site"]
		user_dismissals: DF.Table[DashboardBannerDismissal]
	# end: auto-generated types

	def validate(self):
		if self.is_global and self.is_dismissible:
			frappe.throw("Global banners cannot be dismissible.")


@frappe.whitelist()
def dismiss_banner(banner_name):
	user = frappe.session.user
	banner = frappe.get_doc("Dashboard Banner", banner_name)
	if banner and banner.is_dismissible:
		banner.append(
			"user_dismissals",
			{
				"user": user,
				"dismissed_at": frappe.utils.now(),
				"dashboard_banner": banner_name,
			},
		)
		banner.save(ignore_permissions=True)
		return True
	return False


@frappe.whitelist()
def get_user_banners():
	team = get_current_team()

	# fetch sites + servers for this team
	site_server_pairs = frappe.get_all(
		"Site",
		filters={"team": team},
		fields=["name", "server"],
	)

	sites = list(set([pair["name"] for pair in site_server_pairs]))
	servers = list(set([pair["server"] for pair in site_server_pairs if pair.get("server")]))

	DashboardBanner = frappe.qb.DocType("Dashboard Banner")

	# fetch all enabled banners for this user
	all_enabled_banners = (
		frappe.qb.from_(DashboardBanner)
		.select("*")
		.where(DashboardBanner.enabled == 1)
		.where(
			((DashboardBanner.type_of_scope == "Site") & (DashboardBanner.site.isin(sites)))
			| ((DashboardBanner.type_of_scope == "Server") & (DashboardBanner.server.isin(servers)))
			| ((DashboardBanner.type_of_scope == "Team") & (DashboardBanner.team == team))
			| (DashboardBanner.is_global == 1)
		)
		.run(as_dict=True)
	)

	# filter out dismissed banners
	user = frappe.session.user
	user_specific_banners = []
	for banner in all_enabled_banners:
		banner_dismissals_by_user = frappe.get_all(
			"Dashboard Banner Dismissal",
			filters={"user": user, "parent": banner["name"]},
		)
		if not banner_dismissals_by_user:
			user_specific_banners.append(banner)

	return user_specific_banners
