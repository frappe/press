from typing import TYPE_CHECKING

import frappe
import frappe.utils
from frappe.utils import update_progress_bar

if TYPE_CHECKING:
	from frappe.core.doctype.role.role import Role


def execute():
	User = frappe.qb.DocType("User")
	HasRole = frappe.qb.DocType("Has Role")

	# Get a list of users who don't have the "Press User" role, excluding "Administrator" and "Guest".
	users = [
		u.name
		for u in (
			frappe.qb.from_(User)
			.left_join(HasRole)
			.on((HasRole.parent == User.name) & (HasRole.role == "Press User"))
			.where(HasRole.name.isnull())
			.where(User.name != "Administrator")
			.where(User.name != "Guest")
			.select(User.name)
			.distinct()
			.run(as_dict=True)
		)
	]

	total = len(users)
	chunk_size = 100
	old_roles = ("Press Admin", "Press Member")

	# Give "Press User" role to users who don't have it.
	print(f"Updating {total} users")
	for chunk_start in range(0, total, chunk_size):
		chunk = users[chunk_start : chunk_start + chunk_size]
		for i, user in enumerate(chunk, start=chunk_start):
			name = frappe.generate_hash(length=8)
			now_str = frappe.utils.now()
			frappe.qb.into(HasRole).columns(
				"name",
				"creation",
				"modified",
				"modified_by",
				"owner",
				"parent",
				"parentfield",
				"parenttype",
				"role",
			).insert(
				name,
				now_str,
				now_str,
				"Administrator",
				"Administrator",
				user,
				"roles",
				"User",
				"Press User",
			).run()
			update_progress_bar("Updating users", i, total)
		frappe.db.commit()

	# Remove old roles from all users.
	frappe.qb.from_(HasRole).where(HasRole.role.isin(old_roles)).where(
		HasRole.parentype == "User"
	).delete().run()

	# Change all remaining "Press Admin" and "Press Member" roles to "Press User".
	frappe.qb.update(HasRole).set(HasRole.role, "Press User").where(HasRole.role.isin(old_roles)).run()

	# Disable old roles.
	for old_role in old_roles:
		if frappe.db.exists("Role", old_role):
			role_doc: Role = frappe.get_doc("Role", old_role)
			role_doc.disabled = True
			role_doc.save()

	# Commit changes.
	frappe.db.commit()
