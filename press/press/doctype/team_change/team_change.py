# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TeamChange(Document):
	def validate(self):
		team = frappe.get_doc(self.document_type, self.document_name).team
		if team != self.from_team:
			frappe.throw(f"The owner of {self.document_type} is not {self.from_team}")

	def on_update(self):
		if self.document_type == "Site" and self.transfer_completed:
			frappe.db.set_value("Site", self.document_name, "team", self.to_team)
			frappe.db.set_value(
				"Subscription",
				{"document_name": self.document_name},
				"team",
				self.to_team,
			)
