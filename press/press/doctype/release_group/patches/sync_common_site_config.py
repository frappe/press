# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def execute():
	for name in frappe.db.get_all("Release Group", pluck="name"):
		release_group = frappe.get_doc("Release Group", name)
		if (
			release_group.common_site_config
			and release_group.common_site_config != "{}"
			and release_group.common_site_config_table == []
		):
			common_site_config = frappe.parse_json(release_group.common_site_config)
			for key, value in common_site_config.items():
				config_type = get_type(value)
				if config_type == "JSON":
					value = frappe.as_json(value)
				release_group.append(
					"common_site_config_table",
					{
						"key": key,
						"value": value,
						"type": config_type,
						"internal": frappe.db.get_value("Site Config Key", key, "internal"),
					},
				)
			release_group.save()


def get_type(value):
	if isinstance(value, bool):
		return "Boolean"
	elif isinstance(value, str):
		return "String"
	elif isinstance(value, int):
		return "Number"
	elif isinstance(value, dict):
		return "JSON"
