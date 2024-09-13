import frappe


def execute():
	# Set enable_performance_tuning to True for all records in Team DocType
	# Default value in Team doctype has been set to True
	frappe.db.sql(
		"""
        UPDATE `tabTeam`
        SET enable_performance_tuning = 1
    """
	)
