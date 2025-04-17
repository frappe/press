import frappe


def execute():
	sites = frappe.get_all(
		"Site",
		filters={
			"status": [
				"in",
				["Active", "Updating", "Recovering", "Broken", "Inactive", "Pending", "Suspended"],
			],
			"ifnull(backup_time, '')": ("!=", ""),
		},
		fields=["name", "backup_time"],
	)

	for site in sites:
		site = frappe.get_doc("Site", site.name)
		frappe.db.set_value("Site", site.name, "schedule_logical_backup_at_custom_time", True)
		frappe.get_doc(
			{
				"doctype": "Site Backup Time",
				"parent": site.name,
				"parenttype": "Site",
				"parentfield": "logical_backup_times",
				"backup_time": site.backup_time,
			}
		).insert()
