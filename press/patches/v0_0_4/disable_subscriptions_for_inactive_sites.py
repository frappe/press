# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	subscription = frappe.qb.DocType("Subscription")
	site = frappe.qb.DocType("Site")

	inactive_sites = (
		frappe.qb.from_(subscription)
		.left_join(site)
		.on(subscription.document_name == site.name)
		.select(subscription.name)
		.where(site.status.isin(["Archived", "Broken", "Suspended"]))
	).run(pluck=True)

	(
		frappe.qb.update(subscription)
		.set(subscription.enabled, 0)
		.where(subscription.enabled == 1)
		.where(subscription.name.isin(inactive_sites))
	).run()
