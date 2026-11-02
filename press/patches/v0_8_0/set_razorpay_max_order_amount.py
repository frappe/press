import frappe


def execute():
	frappe.reload_doc("press", "doctype", "press_settings")
	frappe.db.set_single_value("Press Settings", "razorpay_max_order_amount_inr", 500000)
