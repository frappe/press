# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document

DISK_FULL_ALERT = "Disk Full"
DISK_FULL_BANNER = {
	"title": "Server is out of disk space",
	"message": (
		"Sites on this server may stop responding until space is freed up. "
		"Add a storage add-on or drop old backups and logs."
	),
	"type": "Error",
	"type_of_scope": "Server",
	"help_url": "https://docs.frappe.io/cloud/storage-addons",
}


class DashboardBanner(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.dashboard_banner_cluster.dashboard_banner_cluster import (
			DashboardBannerCluster,
		)
		from press.press.doctype.dashboard_banner_dismissal.dashboard_banner_dismissal import (
			DashboardBannerDismissal,
		)
		from press.press.doctype.dashboard_banner_server.dashboard_banner_server import DashboardBannerServer
		from press.press.doctype.dashboard_banner_site.dashboard_banner_site import DashboardBannerSite
		from press.press.doctype.dashboard_banner_team.dashboard_banner_team import DashboardBannerTeam

		action_label: DF.Data | None
		action_script: DF.Code | None
		cluster: DF.TableMultiSelect[DashboardBannerCluster]
		enabled: DF.Check
		has_action: DF.Check
		help_url: DF.Data | None
		is_dismissible: DF.Check
		is_global: DF.Check
		is_scheduled: DF.Check
		message: DF.LongText | None
		scheduled_end_time: DF.Datetime | None
		scheduled_start_time: DF.Datetime | None
		server: DF.TableMultiSelect[DashboardBannerServer]
		site: DF.TableMultiSelect[DashboardBannerSite]
		team: DF.TableMultiSelect[DashboardBannerTeam]
		title: DF.Data | None
		type: DF.Literal["Info", "Success", "Error", "Warning"]
		type_of_scope: DF.Literal["Team", "Server", "Site", "Cluster"]
		user_dismissals: DF.Table[DashboardBannerDismissal]
	# end: auto-generated types


def get_disk_full_banner() -> DashboardBanner:
	name = frappe.db.get_value("Dashboard Banner", {"title": DISK_FULL_BANNER["title"]})
	if name:
		return frappe.get_doc("Dashboard Banner", name)
	return frappe.get_doc({"doctype": "Dashboard Banner", **DISK_FULL_BANNER}).insert(ignore_permissions=True)


def set_disk_full_banner(servers: list[str], is_full: bool):
	"""Show (or hide) the disk full banner on the given app servers and their sites."""
	if not servers:
		return

	banner = get_disk_full_banner()
	affected = {row.server for row in banner.server}
	affected = affected | set(servers) if is_full else affected - set(servers)

	banner.server = []
	for server in sorted(affected):
		banner.append("server", {"server": server})
	banner.enabled = bool(affected)
	banner.save(ignore_permissions=True)


def app_servers_of(instances: set[str]) -> list[str]:
	"""Banners are scoped to app servers, so map database servers to the servers they serve.

	A unified server is its own database server, so both matches are made in one query
	to return it only once.
	"""
	instances = list(instances)
	return frappe.get_all(
		"Server",
		or_filters={"name": ("in", instances), "database_server": ("in", instances)},
		pluck="name",
	)
