# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class Config(Document):
	dashboard_fields = ["key", "type", "value"]

	def get_type(self):
		return frappe.db.get_value("Site Config Key", self.key, "type")

	def format_config_for_list(configs):
		config_key_titles = frappe.db.get_all(
			"Site Config Key",
			fields=["key", "title"],
			filters={"key": ["in", [c.key for c in configs]]},
		)
		secret_keys = frappe.get_all(
			"Site Config Key", filters={"type": "Password"}, pluck="key"
		)
		for config in configs:
			if config.key in secret_keys:
				config.value = "*******"
			config.title = next((c.title for c in config_key_titles if c.key == config.key), "")
		return configs


class SiteConfig(Config):
	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		Config = frappe.qb.DocType("Site Config")
		query = query.where(Config.internal == 0)
		configs = query.run(as_dict=True)
		return SiteConfig.format_config_for_list(configs)
