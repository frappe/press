from typing import TYPE_CHECKING

import frappe
from frappe.utils import update_progress_bar

if TYPE_CHECKING:
	from frappe.core.doctype.role.role import Role
	from frappe.core.doctype.user.user import User


def execute():
	users = frappe.db.get_all("User", pluck="name")
	total = len(users)
	chunk_size = 100
	old_roles = ("Press Admin", "Press Member")
	print(f"Merging roles of {total} users")
	for chunk_start in range(0, total, chunk_size):
		chunk = users[chunk_start : chunk_start + chunk_size]
		for i, user in enumerate(chunk, start=chunk_start):
			user_doc: User = frappe.get_doc("User", user)
			user_doc.remove_roles(*old_roles)
			user_doc.add_roles("Press User")
			update_progress_bar("Merging roles", i, total)
		frappe.db.commit()
	for old_role in old_roles:
		if frappe.db.exists("Role", old_role):
			role_doc: Role = frappe.get_doc("Role", old_role)
			role_doc.disabled = True
			role_doc.save()
	frappe.db.commit()
