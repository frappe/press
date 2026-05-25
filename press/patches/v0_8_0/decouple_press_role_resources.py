import frappe
from frappe.utils import update_progress_bar

from press.press.doctype.team_member_resource.team_member_resource import sync_press_role


def execute():
	press_roles = frappe.get_all("Press Role", pluck="name")
	total = len(press_roles)
	for index, press_role in enumerate(press_roles, start=1):
		press_role_doc = frappe.get_doc("Press Role", press_role)
		sync_press_role(press_role_doc)
		update_progress_bar("Syncing Press Role Resources", index, total, absolute=True)
		frappe.db.commit()
	print()
