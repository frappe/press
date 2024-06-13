# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from tqdm import tqdm


def execute():
	sites = frappe.get_all("Site", fields=["name", "team"])

	for site in tqdm(sites):
		site_updates = frappe.get_all("Site Update", filters={"site": site["name"]})
		for site_update in site_updates:
			frappe.db.set_value("Site Update", site_update["name"], "team", site["team"])

		site_backups = frappe.get_all("Site Backup", filters={"site": site["name"]})
		for site_backup in site_backups:
			frappe.db.set_value("Site Backup", site_backup["name"], "team", site["team"])

		site_migrations = frappe.get_all("Site Migration", filters={"site": site["name"]})
		for site_migration in site_migrations:
			frappe.db.set_value("Site Migration", site_migration["name"], "team", site["team"])
