import frappe
import json


def execute():
	"""Convert site._site_usages Data field into individual fields"""
	frappe.reload_doc("press", "doctype", "site")
	non_archived_sites = frappe.get_all(
		"Site", filters={"status": ("!=", "Archived")}, pluck="name"
	)

	for site in non_archived_sites:
		site_doc = frappe.get_doc("Site", site)
		parsed_usage = json.loads(site_doc._site_usages or "{}")
		site_doc.current_cpu_usage = parsed_usage.get("cpu", 0) * 100
		site_doc.current_database_usage = parsed_usage.get("database", 0) * 100
		site_doc.current_disk_usage = parsed_usage.get("disk", 0) * 100
		site_doc.save()
