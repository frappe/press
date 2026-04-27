from typing import TYPE_CHECKING

import frappe
from frappe.utils import update_progress_bar

if TYPE_CHECKING:
	from frappe.core.doctype.user.user import User


def execute():
	users = frappe.db.get_all("User", pluck="name")
	total = len(users)
	print(f"Merging roles of {total} users")
	for i, user in enumerate(users):
		user_doc: User = frappe.get_doc("User", user)
		user_doc.remove_roles("Press Admin", "Press Member")
		user_doc.add_roles("Press User")
		update_progress_bar("Merging roles", i, total)
	frappe.db.delete("Role", {"name": "Press Admin"})
	frappe.db.delete("Role", {"name": "Press Member"})
	frappe.db.commit()
