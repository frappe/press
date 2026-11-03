import frappe
from frappe.utils import cint


def execute():
	"""The wait time is a Duration field, which holds seconds, but the code read it as minutes."""
	minutes = cint(frappe.db.get_single_value("Incident Settings", "wait_time_post_investigator_actions"))
	if minutes and minutes < 60:
		frappe.db.set_single_value("Incident Settings", "wait_time_post_investigator_actions", minutes * 60)
