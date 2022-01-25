# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe
from frappe.utils import update_progress_bar


def execute():
	frappe.db.sql("DROP TABLE IF EXISTS `tabSubscription`")

	frappe.reload_doc("press", "doctype", "subscription", force=True)
	frappe.reload_doc("press", "doctype", "site")

	active_sites = frappe.db.get_all(
		"Site",
		filters={"status": "Active", "free": False, "team": ("is", "set")},
		fields=["name", "team", "plan"],
	)
	for i, site in enumerate(active_sites):
		update_progress_bar("Creating Subscriptions", i, len(active_sites))

		# skip if already exists
		if frappe.db.exists(
			"Subscription",
			{"team": site.team, "document_type": "Site", "document_name": site.name},
		):
			continue

		try:
			frappe.get_doc(
				doctype="Subscription",
				enabled=1,
				team=site.team,
				document_type="Site",
				document_name=site.name,
				plan=site.plan,
				interval="Daily",
			).insert()
		except frappe.DuplicateEntryError:
			print(f"Failed to create subscription for site {site}")

	print()
