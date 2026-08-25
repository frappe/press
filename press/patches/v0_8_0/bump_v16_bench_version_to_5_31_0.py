import frappe
from frappe.utils import update_progress_bar


def execute():
	groups = frappe.get_all("Release Group", filters={"version": "Version 16", "enabled": 1}, pluck="name")

	if not groups:
		return

	rows = frappe.get_all(
		"Release Group Dependency",
		filters={
			"parenttype": "Release Group",
			"parent": ["in", groups],
			"dependency": "BENCH_VERSION",
			"version": ["!=", "5.31.0"],
		},
		fields=["name", "parent"],
	)

	now = frappe.utils.now_datetime()
	for i, row in enumerate(rows):
		update_progress_bar("Bumping bench version on Version 16 groups", i, len(rows))
		frappe.db.set_value("Release Group Dependency", row.name, "version", "5.31.0", update_modified=False)
		# Set what ReleaseGroup.on_update would have set. Saving each group instead would run every
		# Release Group validation during migrate, where one bad group aborts the whole patch.
		frappe.db.set_value("Release Group", row.parent, "last_dependency_update", now)

	frappe.db.commit()
