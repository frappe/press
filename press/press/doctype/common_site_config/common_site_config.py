# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CommonSiteConfig(Document):
	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		Config = frappe.qb.DocType("Common Site Config")
		if filters and filters.get("group"):
			query = (
				query.where(Config.parent == filters.get("group"))
				.where(Config.parenttype == "Release Group")
				.where(Config.internal == 0)
				.orderby(Config.key, order=frappe.qb.asc)
			)
		configs = query.run(as_dict=True)
		config_key_titles = frappe.db.get_all(
			"Site Config Key",
			fields=["key", "title"],
			filters={"key": ["in", [c.key for c in configs]]},
		)
		for config in configs:
			config.title = next((c.title for c in config_key_titles if c.key == config.key), "")
		return configs

	def get_type(self):
		return frappe.db.get_value("Site Config Key", self.key, "type")
