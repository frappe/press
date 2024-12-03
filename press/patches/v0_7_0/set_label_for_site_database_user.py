import frappe


def execute():
	db_users = frappe.get_all(
		"Site Database User",
		filters={"status": ("!=", "Archived")},
		fields=["name", "username"],
	)

	for db_user in db_users:
		frappe.db.set_value("Site Database User", db_user.name, "label", f"User {db_user.username}")
