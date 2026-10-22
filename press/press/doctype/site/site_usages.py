import functools
from typing import TYPE_CHECKING

import frappe
import frappe.utils
import rq
from frappe.query_builder import Order
from frappe.query_builder.functions import Abs, Cast
from pypika.analytics import RowNumber

from press.api.analytics import get_current_cpu_usage_for_sites_on_server
from press.press.doctype.site_plan.site_plan import get_plan_config
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site


@functools.lru_cache(maxsize=128)
def get_cpu_limit(plan):
	return frappe.db.get_value("Site Plan", plan, "cpu_time_per_day") * 3600 * 1000_000


@functools.lru_cache(maxsize=128)
def get_cpu_limits(plan):
	return get_config(plan).get("rate_limit", {}).get("limit", 1) * 1000_000


@functools.lru_cache(maxsize=128)
def get_disk_limits(plan):
	return frappe.db.get_value("Site Plan", plan, ["max_database_usage", "max_storage_usage"])


@functools.lru_cache(maxsize=128)
def get_config(plan):
	return get_plan_config(plan)


def update_cpu_usages():
	"""Update CPU Usages field Site.current_cpu_usage across all Active sites from Site Request Log"""
	servers = frappe.get_all("Server", filters={"status": "Active", "is_primary": True}, pluck="name")
	for server in servers:
		frappe.enqueue(
			"press.press.doctype.site.site_usages.update_cpu_usage_server",
			server=server,
			queue="long",
			deduplicate=True,
			job_id=f"update_cpu_usages:{server}",
		)


def update_cpu_usage_server(server):
	usage = get_current_cpu_usage_for_sites_on_server(server)
	sites = frappe.get_all(
		"Site",
		filters={"status": "Active", "server": server},
		fields=["name", "plan", "current_cpu_usage"],
	)

	for site in sites:
		if site.name not in usage:
			continue
		try:
			cpu_usage = usage[site.name]
			cpu_limit = get_cpu_limits(site.plan)
			latest_cpu_usage = int((cpu_usage / cpu_limit) * 100)

			if site.current_cpu_usage != latest_cpu_usage:
				site_doc = frappe.get_doc("Site", site.name)
				site_doc.current_cpu_usage = latest_cpu_usage
				site_doc.save()
				frappe.db.commit()
		except rq.timeouts.JobTimeoutException:
			frappe.db.rollback()
			return
		except Exception:
			log_error("Site CPU Usage Update Error", site=site, cpu_usage=cpu_usage, cpu_limit=cpu_limit)
			frappe.db.rollback()


def get_changed_disk_usages():
	"""Latest Site Usage of each site in the past 12 hours, where it moved more than 1% of the plan"""
	SiteUsage = frappe.qb.DocType("Site Usage")
	Subscription = frappe.qb.DocType("Subscription")
	SiteTable = frappe.qb.DocType("Site")
	SitePlan = frappe.qb.DocType("Site Plan")

	usage = (
		frappe.qb.from_(SiteUsage)
		.select(
			SiteUsage.site,
			SiteUsage.database,
			(SiteUsage.public + SiteUsage.private).as_("disk"),
			RowNumber().over(SiteUsage.site).orderby(SiteUsage.creation, order=Order.desc).as_("rank"),
		)
		.where(SiteUsage.creation > frappe.utils.add_to_date(frappe.utils.now(), hours=-12))
	).as_("usage")

	joined = (
		frappe.qb.from_(usage)
		.join(Subscription)
		.on(usage.site == Subscription.document_name)
		.left_join(SiteTable)
		.on(usage.site == SiteTable.name)
		.left_join(SitePlan)
		.on(Subscription.plan == SitePlan.name)
		.select(
			usage.site,
			SiteTable.current_database_usage,
			SiteTable.current_disk_usage,
			Cast(usage.database / SitePlan.max_database_usage * 100, "INTEGER").as_("latest_database_usage"),
			Cast(usage.disk / SitePlan.max_storage_usage * 100, "INTEGER").as_("latest_disk_usage"),
		)
		.where(usage.rank == 1)
		.where(Subscription.document_type == "Site")
		.where(SiteTable.status != "Archived")
	).as_("joined")

	return (
		frappe.qb.from_(joined)
		.select(joined.site, joined.latest_database_usage, joined.latest_disk_usage)
		.where(
			(Abs(joined.latest_database_usage - joined.current_database_usage) > 1)
			| (Abs(joined.latest_disk_usage - joined.current_disk_usage) > 1)
		)
		.run(as_dict=True)
	)


def update_disk_usages():
	"""Update Storage and Database Usages fields Site.current_database_usage and Site.current_disk_usage for sites that have Site Usage documents"""

	latest_disk_usages = get_changed_disk_usages()

	for usage in latest_disk_usages:
		try:
			site: Site = frappe.get_doc("Site", usage.site, for_update=True)
			site.current_database_usage = usage.latest_database_usage
			site.current_disk_usage = usage.latest_disk_usage
			site.check_if_disk_usage_exceeded(save=False)
			site.save()
			frappe.db.commit()
		except frappe.DoesNotExistError:
			frappe.db.rollback()
		except Exception:
			log_error("Site Disk Usage Update Error", usage=usage)
			frappe.db.rollback()
