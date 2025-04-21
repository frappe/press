import frappe


def execute():
	sites = frappe.get_all(
		"Site",
		filters={
			"status": [
				"in",
				["Active", "Updating", "Recovering", "Broken", "Inactive", "Pending", "Suspended"],
			],
			"skip_scheduled_backups": True,
		},
		pluck="name",
	)

	for site in sites:
		frappe.db.set_value("Site", site, "skip_scheduled_logical_backups", True)
