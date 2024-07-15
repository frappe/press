# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe
from tqdm import tqdm


def execute():
	key_name = "plan_limit"
	if not frappe.db.exists("Site Config Key", {"key": key_name}):
		frappe.get_doc(
			{
				"doctype": "Site Config Key",
				"key": key_name,
				"type": "JSON",
				"internal": True,
			}
		).insert(ignore_permissions=True)

	non_archived_sites = frappe.get_all(
		"Site", filters={"status": ("!=", "Archived")}, pluck="name"
	)

	for site_name in tqdm(non_archived_sites):
		try:
			site = frappe.get_doc("Site", site_name, for_update=True)
			site.update_site_config(site.get_plan_config())
			frappe.db.commit()
		except Exception as e:
			print(f"Couldn't set plan limit for site {site_name}: {e}")
			frappe.db.rollback()
