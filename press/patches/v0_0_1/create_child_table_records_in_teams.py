import frappe
from press.utils import log_error


def execute():
	frappe.reload_doc("press", "doctype", "team")
	teams = frappe.get_all("Team", pluck="name")

	for name in teams:
		try:
			team = frappe.get_doc("Team", name)
			team.append("communication_emails", {"type": "invoices", "value": team.name})
			team.append(
				"communication_emails", {"type": "marketplace_notifications", "value": team.name}
			)
			team.save()
		except Exception as e:
			log_error(title="Weird Country Name", data=e)
