# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from tqdm import tqdm


def execute():
	notifications = frappe.db.get_all("Press Notification", ["name", "document_type", "document_name"])
	for notification in tqdm(notifications):
		if notification.document_type == "Agent Job":
			reference_doctype = "Site"
			reference_doc = frappe.db.get_value("Agent Job", notification.document_name, "site")
			if not reference_doc:
				reference_doctype = "Server"
				reference_doc = frappe.db.get_value("Agent Job", notification.document_name, "server")

		elif notification.document_type == "Deploy Candidate":
			reference_doctype = "Release Group"
			reference_doc = frappe.db.get_value("Deploy Candidate", notification.document_name, "group")

		frappe.db.set_value(
			"Press Notification",
			notification.name,
			{"reference_doctype": reference_doctype, "reference_name": reference_doc},
			update_modified=False,
		)
