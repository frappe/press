# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AppUserReview(Document):
	def after_insert(self):
		self.update_average_rating()

	def update_average_rating(self):
		ratings = frappe.db.get_all(
			"App User Review",
			filters={"app": self.app},
			fields=["rating"],
			pluck="rating",
		)

		if ratings:
			average_rating = (sum(ratings) / len(ratings)) * 5
			average_rating = round(average_rating, 2)

			frappe.db.set_value(
				"Marketplace App", self.app, "average_rating", average_rating, update_modified=False
			)
		else:
			frappe.db.set_value(
				"Marketplace App", self.app, "average_rating", 0, update_modified=False
			)
