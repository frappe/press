# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe
from tqdm import tqdm


def execute():
	frappe.reload_doc("press", "doctype", "site")
	sites = frappe.get_all(
		"Site",
		{
			"status": ("!=", "Archived"),
			"is_database_access_enabled": True,
			"database_access_user": ("is", "not set"),
		},
		ignore_ifnull=True,
	)
	for site in tqdm(sites):
		try:
			site = frappe.get_doc("Site", site.name)
			config = site.fetch_info()["config"]
			site.database_access_user = config["db_name"]
			site.database_access_password = config["db_password"]
			site.database_access_mode = "read_write"
			site.save()
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			print(f"Couldn't set DB credentials for site {site.name}: {e}")
