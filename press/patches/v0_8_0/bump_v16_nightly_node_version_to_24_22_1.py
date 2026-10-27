import frappe
from frappe.utils import update_progress_bar
from packaging.version import Version

# dependency: (versions to move, as a LIKE pattern; new version). Only older versions move.
# Node moves only within 24.x, so no group is moved across a major.
# pip moves only from the old default, so a group pinned to 25.2 keeps its workaround.
BUMPS = {
	"NODE_VERSION": ("24.%", "24.22.1"),
	"PIP_VERSION": ("25.3", "26.2.2"),
}


def execute():
	groups = frappe.get_all(
		"Release Group",
		filters={"version": ["in", ["Version 16", "Nightly"]], "enabled": 1},
		pluck="name",
	)

	if not groups:
		return

	for dependency, (current, new) in BUMPS.items():
		bump(groups, dependency, current, new)

	frappe.db.commit()


def bump(groups: list[str], dependency: str, current: str, new: str):
	rows = frappe.get_all(
		"Release Group Dependency",
		filters=[
			["parenttype", "=", "Release Group"],
			["parent", "in", groups],
			["dependency", "=", dependency],
			["version", "like", current],
		],
		fields=["name", "parent", "version"],
	)
	rows = [row for row in rows if Version(row.version) < Version(new)]

	now = frappe.utils.now_datetime()
	for i, row in enumerate(rows):
		update_progress_bar(f"Bumping {dependency} on Version 16 and Nightly groups", i, len(rows))
		frappe.db.set_value("Release Group Dependency", row.name, "version", new, update_modified=False)
		# Set what ReleaseGroup.on_update would have set. Saving each group instead would run every
		# Release Group validation during migrate, where one bad group aborts the whole patch.
		frappe.db.set_value("Release Group", row.parent, "last_dependency_update", now)
