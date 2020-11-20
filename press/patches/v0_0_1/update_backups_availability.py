import frappe


def execute():
	frappe.db.sql("update `tabSite Backup` set files_availability = 'Available'")
	frappe.db.commit()
