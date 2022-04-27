import frappe


def execute():
	frappe.reload_doc("press", "doctype", "team")
	frappe.reload_doc("press", "doctype", "invoice")

	partners = frappe.db.get_all("Team", filters={"erpnext_partner": True})

	for partner in partners:
		frappe.db.set_value("Team", partner.name, "partner_email", partner.name)
