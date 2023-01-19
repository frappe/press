import frappe
import functools
from press.press.doctype.plan.plan import get_plan_config
from press.api.analytics import get_current_cpu_usage
from press.utils import log_error


@functools.lru_cache(maxsize=128)
def get_cpu_limit(plan):
	return frappe.db.get_value("Plan", plan, "cpu_time_per_day") * 3600 * 1000_000


@functools.lru_cache(maxsize=128)
def get_cpu_limits(plan):
	return get_config(plan)["rate_limit"]["limit"] * 1000_000


@functools.lru_cache(maxsize=128)
def get_disk_limits(plan):
	return frappe.db.get_value("Plan", plan, ["max_database_usage", "max_storage_usage"])


@functools.lru_cache(maxsize=128)
def get_config(plan):
	return get_plan_config(plan)


def get_cpu_counter(site):
	cpu_usage = get_current_cpu_usage(site)
	return cpu_usage


def update_cpu_usages():
	"""Update CPU Usages field Site.current_cpu_usage across all Active sites from Site Request Log"""
	sites = frappe.get_all("Site", filters={"status": "Active"}, pluck="name")

	for site in sites:
		site_doc = frappe.get_cached_doc("Site", site)
		cpu_usage = get_cpu_counter(site)
		cpu_limit = get_cpu_limits(site_doc.plan)
		latest_cpu_usage = int((cpu_usage / cpu_limit) * 100)

		if site_doc.current_cpu_usage != latest_cpu_usage:
			site_doc.current_cpu_usage = latest_cpu_usage
			site_doc.save()


def update_disk_usages():
	"""Update Storage and Database Usages fields Site.current_database_usage and Site.current_disk_usage for sites that have Site Usage documents"""

	latest_disk_usages = frappe.db.sql(
		r"""WITH disk_usage AS (
			SELECT `site`, `backups`, `database`, `public`, `private`,
			ROW_NUMBER() OVER (PARTITION BY `site` ORDER BY `creation` DESC) AS 'rank'
			FROM `tabSite Usage`
			WHERE `site` NOT LIKE '%cloud.archived%'
		) SELECT d.*, s.plan
			FROM disk_usage d INNER JOIN `tabSubscription` s
			ON d.site = s.document_name
			WHERE `rank` = 1 AND s.`document_type` = 'Site' AND s.`enabled`
		""",
		as_dict=True,
	)

	for usage in latest_disk_usages:
		try:
			plan = usage.plan
			site = frappe.get_cached_doc("Site", usage.site)

			database_usage = usage.database
			disk_usage = usage.public + usage.private
			database_limit, disk_limit = get_disk_limits(plan)
			latest_database_usage = int((database_usage / database_limit) * 100)
			latest_disk_usage = int((disk_usage / disk_limit) * 100)

			if (
				site.current_database_usage != latest_database_usage
				or site.current_disk_usage != latest_disk_usage
			):
				site.current_database_usage = latest_database_usage
				site.current_disk_usage = latest_disk_usage
				site.save()
				frappe.db.commit()
		except Exception():
			log_error("Site Disk Usage Update Error", usage=usage)
			frappe.db.rollback()
