# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import random
from press.utils import get_current_team
from frappe.model.document import Document


class FeatureExperiment(Document):
	def validate(self):
		if self.percentage_for_cohort_a > 100 or self.percentage_for_cohort_a < 0:
			frappe.throw("Percentage value should be between 1 and 100 (inclusive)!")

	def is_cohort_a(self):
		return random.random() <= (self.percentage_for_cohort_a / 100)

	def is_cohort_b(self):
		return not self.is_cohort_a()

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
