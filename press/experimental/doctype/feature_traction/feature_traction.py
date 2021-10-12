# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FeatureTraction(Document):
	pass


def log_feature_traction(
	title="Unknown", source="", log="", related_to="General", path=""
):
	return frappe.get_doc(
		{
			"doctype": "Feature Traction",
			"title": title,
			"source": source,
			"log": log,
			"related_to": related_to,
			"path": path,
		}
	).insert(ignore_permissions=True)
