# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.utils import slug


def execute():
	for row in frappe.get_all(
		"Virtual Machine",
		{"status": "Running"},
		["cluster", "series", "max(`index`) as `index`"],
		group_by="cluster, series",
		order_by="series, cluster",
	):
		frappe.db.sql(
			f"""
			INSERT INTO `tabSeries` (`name`, `current`)
			VALUES ({row.series}-{slug(row.cluster)}, {row.index})
		"""
		)
