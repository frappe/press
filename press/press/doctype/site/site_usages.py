import functools
from typing import TYPE_CHECKING

import frappe
import frappe.utils
import rq
from frappe.query_builder import Order
from frappe.query_builder.functions import Abs, Cast
from pypika.analytics import RowNumber

from press.api.analytics import get_current_cpu_usage_for_sites_on_server
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.server.server import find_recent_notice_dispatch, notice_message_id
from press.press.doctype.site_plan.site_plan import get_plan_config
from press.utils import log_error
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site

DAILY_COMPUTE_WARNING_THRESHOLD = 80
DAILY_COMPUTE_NOTICE_WINDOW_DAYS = 1


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


@functools.lru_cache(maxsize=128)
def get_daily_compute_hours(plan):
	"""Hours of compute the plan includes each day. Zero means the plan sets no daily limit."""
	return frappe.db.get_value("Site Plan", plan, "cpu_time_per_day") or 0


def enforces_a_daily_compute_limit(site) -> bool:
	"""Only a shared server rate limits a site, and only when its plan sets a daily limit."""
	if not get_daily_compute_hours(site.plan):
		return False
	return bool(frappe.get_cached_value("Server", site.server, "public"))


def sites_nearing_daily_compute_limit(threshold: int) -> list[frappe._dict]:
	"""Paid live sites that have used `threshold`% or more of the compute their plan allows today."""
	free_teams = frappe.get_all("Team", filters={"free_account": True, "enabled": True}, pluck="name")
	sites = frappe.get_all(
		"Site",
		filters={
			"status": "Active",
			"free": False,
			"team": ("not in", free_teams),
			"current_cpu_usage": (">=", threshold),
		},
		fields=["name", "team", "plan", "server", "current_cpu_usage"],
	)
	return [site for site in sites if enforces_a_daily_compute_limit(site)]


def notify_sites_nearing_daily_compute_limit(threshold: int = DAILY_COMPUTE_WARNING_THRESHOLD):
	"""Warn the team of each site that is close to the daily compute limit of its plan."""
	for site in sites_nearing_daily_compute_limit(threshold):
		if has_job_timeout_exceeded():
			return
		send_daily_compute_limit_warning(site, threshold)
		frappe.db.commit()


def send_daily_compute_limit_warning(site: frappe._dict, threshold: int):
	"""Mail the site's team once a day. A site over the limit gets its own notice."""
	over_limit = site.current_cpu_usage >= 100
	message_id = daily_compute_notice_message_id(site, threshold, over_limit)
	if find_recent_notice_dispatch(message_id, DAILY_COMPUTE_NOTICE_WINDOW_DAYS):
		return

	recipients = get_communication_info("Email", "Site Activity", "Site", site.name)
	if not recipients:
		return

	frappe.sendmail(
		recipients=recipients,
		subject=daily_compute_limit_subject(site.name, over_limit),
		template="site_nearing_daily_compute_limit",
		args={
			"site": site.name,
			"plan": site.plan,
			"usage": site.current_cpu_usage,
			"compute_hours": get_daily_compute_hours(site.plan),
			"over_limit": over_limit,
			"action_url": f"{frappe.utils.get_url()}/dashboard/sites/{site.name}/insights",
		},
		reference_doctype="Site",
		reference_name=site.name,
		message_id=message_id,
	)


def daily_compute_notice_message_id(site: frappe._dict, threshold: int, over_limit: bool) -> str:
	"""Keyed on over_limit too, so the warning does not suppress the later over-limit notice."""
	args = {"site": site.name, "threshold": threshold, "over_limit": over_limit}
	return notice_message_id("daily-compute-limit-notice", site.team, args)


def daily_compute_limit_subject(site: str, over_limit: bool) -> str:
	if over_limit:
		return f"Action needed: {site} has used up its daily compute limit"
	return f"{site} is close to its daily compute limit"
