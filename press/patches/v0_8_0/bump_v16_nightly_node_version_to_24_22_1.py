import frappe
from frappe.utils import update_progress_bar

NODE_VERSION = "24.22.1"


def execute():
	groups = frappe.get_all(
		"Release Group",
		filters={"version": ["in", ["Version 16", "Nightly"]], "enabled": 1},
		pluck="name",
	)

	if not groups:
		return

	# Only within Node 24, so groups on another major are not downgraded or moved across a major.
	rows = frappe.get_all(
		"Release Group Dependency",
		filters=[
			["parenttype", "=", "Release Group"],
			["parent", "in", groups],
			["dependency", "=", "NODE_VERSION"],
			["version", "like", "24.%"],
			["version", "!=", NODE_VERSION],
		],
		fields=["name", "parent"],
	)

	now = frappe.utils.now_datetime()
	for i, row in enumerate(rows):
		update_progress_bar("Bumping node version on Version 16 and Nightly groups", i, len(rows))
		frappe.db.set_value(
			"Release Group Dependency", row.name, "version", NODE_VERSION, update_modified=False
		)
		# Set what ReleaseGroup.on_update would have set. Saving each group instead would run every
		# Release Group validation during migrate, where one bad group aborts the whole patch.
		frappe.db.set_value("Release Group", row.parent, "last_dependency_update", now)

	frappe.db.commit()
