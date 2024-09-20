# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from tqdm import tqdm


def execute():
	marketplace_app_names = frappe.get_all("Marketplace App", pluck="name")

	for app in tqdm(marketplace_app_names):
		ratings = frappe.db.get_all(
			"App User Review",
			filters={"app": app},
			fields=["rating"],
			pluck="rating",
		)

		if ratings:
			average_rating = (sum(ratings) / len(ratings)) * 5
			average_rating = round(average_rating, 2)

			frappe.db.set_value(
				"Marketplace App", app, "average_rating", average_rating, update_modified=False
			)
		else:
			frappe.db.set_value("Marketplace App", app, "average_rating", 0, update_modified=False)
