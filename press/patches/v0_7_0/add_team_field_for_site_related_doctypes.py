# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from tqdm import tqdm


def execute():
	sites = frappe.get_all(
		"Site", fields=["name", "team"], filters={"status": ("!=", "Archived")}
	)

	for site in tqdm(sites):
		frappe.db.set_value("Site Update", {"site": site["name"]}, "team", site["team"])
		frappe.db.set_value("Site Backup", {"site": site["name"]}, "team", site["team"])
		frappe.db.set_value("Site Activity", {"site": site["name"]}, "team", site["team"])
