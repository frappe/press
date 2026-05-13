import frappe


def execute():
	leads = frappe.get_all("Partner Lead", {"status": "In Process"}, ["name", "engagement_stage"])

	engagement_stage_status_map = {
		"Demo": "Demo/Making",
		"Follow-up": "Follow Up",
		"Quotation": "Proposal/Quotation",
		"Ready for Closing": "Ready to Close",
	}

	for lead in leads:
		status = ""
		if not lead.engagement_stage:
			status = "Open"
		elif lead.engagement_stage in engagement_stage_status_map:
			status = engagement_stage_status_map[lead.engagement_stage]
		else:
			status = lead.engagement_stage

		frappe.db.set_value("Partner Lead", lead.name, "status", status, update_modified=False)
