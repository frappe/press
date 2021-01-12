import frappe
from frappe.utils import cint
import functools
from press.press.doctype.plan.plan import get_plan_config


@functools.lru_cache(maxsize=128)
def get_cpu_limit(plan):
	return frappe.db.get_value("Plan", plan, "cpu_time_per_day") * 3600 * 1000_000


@functools.lru_cache(maxsize=128)
def _get_limits(plan):
	return (
		_get_config(plan)["rate_limit"]["limit"] * 1000000,
		*frappe.db.get_value("Plan", plan, ["max_database_usage", "max_storage_usage"]),
	)


@functools.lru_cache(maxsize=128)
def _get_config(plan):
	return get_plan_config(plan)


def _get_cpu_counter(site):
	_temp_cpu_counter = frappe.get_all(
		"Site Request Log",
		fields=["counter"],
		filters={"site": site},
		order_by="timestamp desc",
		pluck="counter",
		limit=1,
	)
	if _temp_cpu_counter:
		cpu_usage = cint(_temp_cpu_counter[0])
	else:
		cpu_usage = 0
	return cpu_usage


def update_cpu_usages():
	"""Update CPU Usages field Site.current_cpu_usage across all Active sites
	Does Site.save action and commits to update usage percentages
	"""
	sites = frappe.get_all("Site", filters={"status": "Active"}, pluck="name")

	for site in sites:
		_usage = frappe.get_all(
			"Site Request Log",
			filters={"site": site},
			order_by="timestamp desc",
			pluck="counter",
			limit=1,
		)
		plan = frappe.db.get_value(
			"Subscription",
			filters={"document_type": "Site", "document_name": site},
			fieldname="plan",
		)
		cpu_limit = get_cpu_limit(plan) if plan else 999_999_999
		usage = cint(_usage[0]) if _usage else 0
		current_cpu_usage = (usage / cpu_limit) * 100
		site_doc = frappe.get_doc("Site", site)

		if site_doc.current_cpu_usage != current_cpu_usage:
			site_doc.current_cpu_usage = current_cpu_usage
			site_doc.save()

	frappe.db.commit()


def update_disk_usages():
	"""Notify users if they reach 80% of daily CPU usage or total capacity for DB or FS limit"""

	latest_usages = frappe.db.sql(
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

	for usage in latest_usages:
		plan = usage.plan
		database_usage = usage.database
		cpu_usage = _get_cpu_counter(usage.site)
		disk_usage = usage.public + usage.private
		cpu_limit, database_limit, disk_limit = _get_limits(plan)

		latest_cpu_usage = int((cpu_usage / cpu_limit) * 100)
		latest_database_usage = int((database_usage / database_limit) * 100)
		latest_disk_usage = int((disk_usage / disk_limit) * 100)

		# notify if reaching disk/database limits
		site = frappe.get_doc("Site", usage.site)
		if (
			site.current_cpu_usage != latest_cpu_usage
			or site.current_database_usage != latest_database_usage
			or site.current_disk_usage != latest_disk_usage
		):
			site.current_cpu_usage = latest_cpu_usage
			site.current_database_usage = latest_database_usage
			site.current_disk_usage = latest_disk_usage
			site.save()
