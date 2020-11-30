import frappe


def execute():
	frappe.db.sql(
		"update `tabSite Backup` set files_availability = 'Available' where `site` not"
		" like '%frappe.cloud.archived%'"
	)
	frappe.db.sql(
		"update `tabSite Backup` set files_availability = 'Unavailable' where `site`"
		" like '%frappe.cloud.archived%'"
	)
	frappe.db.commit()
