import frappe


def execute():
	suspended_sites = frappe.get_all("Site", filters={"status": "Suspended"}, pluck="name")

	if not suspended_sites:
		return

	site_suspension_activity_records = frappe.get_all(
		"Site Activity",
		filters={
			"action": "Suspend Site",
			"site": ["in", suspended_sites],
		},
		fields=["site", "max(creation) as suspended_at"],
		group_by="site",
	)

	for row in site_suspension_activity_records:
		frappe.db.set_value("Site", row.site, "suspended_at", row.suspended_at, update_modified=False)

	frappe.db.commit()
