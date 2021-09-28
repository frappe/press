# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.utils import get_current_team
from frappe.model.document import Document


class FeatureExperiment(Document):
	def log_record(self, notes="", log=""):
		current_team = get_current_team()
		frappe.get_doc(
			{
				"doctype": "Feature Experiment Log",
				"experiment": self.name,
				"type": "Record",
				"team": current_team,
				"notes": notes,
				"log": log,
			}
		).insert()

	def log_error(self, notes="", log=""):
		current_team = get_current_team()
		frappe.get_doc(
			{
				"doctype": "Feature Experiment Log",
				"experiment": self.name,
				"type": "Error",
				"team": current_team,
				"notes": notes,
				"log": log,
			}
		).insert()
