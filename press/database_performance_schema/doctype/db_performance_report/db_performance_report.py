# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DBPerformanceReport(Document):
	pass


def clear_performance_reports_older_than_7_days():
	"""If any logtype table grows too large then clearing it with DELETE query
	is not feasible in reasonable time. This command copies recent data to new
	table and replaces current table with new smaller table.
	ref: https://mariadb.com/kb/en/big-deletes/#deleting-more-than-half-a-table
	"""
	from frappe.utils import get_table_name

	original = get_table_name("DB Performance Report")
	temporary = f"{original} temp_table"
	backup = f"{original} backup_table"

	try:
		frappe.db.sql_ddl(f"CREATE TABLE `{temporary}` LIKE `{original}`")

		# Copy all recent data to new table
		frappe.db.sql(
			f"""INSERT INTO `{temporary}`
				SELECT * FROM `{original}`
				WHERE `{original}`.`modified` > NOW() - INTERVAL 7 DAY"""
		)
		frappe.db.sql_ddl(f"RENAME TABLE `{original}` TO `{backup}`, `{temporary}` TO `{original}`")
	except Exception:
		frappe.db.rollback()
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{temporary}`")
		raise
	else:
		frappe.db.sql_ddl(f"DROP TABLE `{backup}`")