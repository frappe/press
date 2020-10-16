import frappe
import json


def execute():
	frappe.reload_doc("press", "doctype", "site")
	frappe.reload_doc("press", "doctype", "site config")
	sites = frappe.get_all("Site", {"status": ("!=", "Archived")})

	commit_scheme = frappe.db.auto_commit_on_many_writes
	frappe.db.auto_commit_on_many_writes = 1

	for _site in sites:
		site = frappe.get_doc("Site", _site.name)
		if site.configuration:
			continue
		print(f"Updating Site Config for {site.name}")
		config = json.loads(site.config)
		for key, value in config.items():
			if isinstance(value, (dict, list)):
				value = json.dumps(value)
			else:
				value = value
			site.append("configuration", {"key": key, "value": value})
		site.save()

	frappe.db.auto_commit_on_many_writes = commit_scheme
