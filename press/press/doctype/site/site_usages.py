import functools

import rq
import frappe

from press.api.analytics import get_current_cpu_usage_for_sites_on_server
from press.press.doctype.site_plan.site_plan import get_plan_config
from press.utils import log_error


@functools.lru_cache(maxsize=128)
def get_cpu_limit(plan):
	return frappe.db.get_value("Site Plan", plan, "cpu_time_per_day") * 3600 * 1000_000


@functools.lru_cache(maxsize=128)
def get_cpu_limits(plan):
	return get_config(plan).get("rate_limit", {}).get("limit", 1) * 1000_000


@functools.lru_cache(maxsize=128)
def get_disk_limits(plan):
	return frappe.db.get_value(
		"Site Plan", plan, ["max_database_usage", "max_storage_usage"]
	)


@functools.lru_cache(maxsize=128)
def get_config(plan):
	return get_plan_config(plan)


def update_cpu_usages():
	"""Update CPU Usages field Site.current_cpu_usage across all Active sites from Site Request Log"""
	servers = frappe.get_all(
		"Server", filters={"status": "Active", "is_primary": True}, pluck="name"
	)
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
			log_error(
				"Site CPU Usage Update Error", site=site, cpu_usage=cpu_usage, cpu_limit=cpu_limit
			)
			frappe.db.rollback()


def update_disk_usages():
	"""Update Storage and Database Usages fields Site.current_database_usage and Site.current_disk_usage for sites that have Site Usage documents"""

	latest_disk_usages = frappe.db.sql(
		"""WITH disk_usage AS (
			SELECT
				`site`,
				`database`,
				`public` + `private` as disk,
				ROW_NUMBER() OVER (PARTITION BY `site` ORDER BY `creation` DESC) AS 'rank'
			FROM
				`tabSite Usage`
			WHERE
				`creation` > %s
		),
		joined AS (
			SELECT
				u.site,
				site.current_database_usage,
				site.current_disk_usage,
				CAST(u.database / plan.max_database_usage * 100 AS INTEGER) AS latest_database_usage,
				CAST(u.disk / plan.max_storage_usage * 100 AS INTEGER) AS latest_disk_usage
			FROM
				disk_usage u
			INNER JOIN
				`tabSubscription` s
			ON
				u.site = s.document_name
			LEFT JOIN
				`tabSite` site
			ON
				u.site = site.name
			LEFT JOIN
				`tabSite Plan` plan
			ON
				s.plan = plan.name
			WHERE
				`rank` = 1 AND
				s.`document_type` = 'Site' AND
				s.`enabled` AND
				site.`status` != "Archived"
		)
		SELECT
			j.site,
			j.latest_database_usage,
			j.latest_disk_usage
		FROM
			joined j
		WHERE
			ABS(j.latest_database_usage - j.current_database_usage ) > 1 OR
			ABS(j.latest_disk_usage - j.current_disk_usage) > 1
	""",
		values=(frappe.utils.add_to_date(frappe.utils.now(), hours=-12),),
		as_dict=True,
	)

	for usage in latest_disk_usages:
		try:
			site = frappe.get_doc("Site", usage.site, for_update=True)
			site.current_database_usage = usage.latest_database_usage
			site.current_disk_usage = usage.latest_disk_usage
			site.save()
			frappe.db.commit()
		except frappe.DoesNotExistError:
			frappe.db.rollback()
		except Exception:
			log_error("Site Disk Usage Update Error", usage=usage)
			frappe.db.rollback()
