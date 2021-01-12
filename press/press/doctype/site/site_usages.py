import frappe
from frappe.utils import cint
import functools


def update_cpu_usages():
	"""Update CPU Usages field Site.current_cpu_usage across all Active sites
	Does Site.save action and commits to update usage percentages
	"""
	sites = frappe.get_all("Site", filters={"status": "Active"}, pluck="name")

	@functools.lru_cache()
	def get_cpu_limit(plan):
		return frappe.db.get_value("Plan", plan, "cpu_time_per_day") * 3600 * 1000_000

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
