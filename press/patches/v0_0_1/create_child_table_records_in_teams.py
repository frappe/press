import frappe


def execute():
	frappe.reload_doc("press", "doctype", "team")
	teams = frappe.get_all("Team", pluck="name")

	for name in teams:
		team = frappe.get_doc("Team", name)
		team.append("communication_emails", {"type": "invoices", "value": team.name})
		team.append(
			"communication_emails", {"type": "marketplace_notifications", "value": team.name}
		)
		team.append("communication_emails", {"type": "notifications", "value": team.name})
		team.save()
