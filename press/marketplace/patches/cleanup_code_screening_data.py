import frappe


def execute():
	"""
	Clean up Code Screening data before bench migrate drops the columns.
	- Null out screening fields on App Release Approval Request
	- Null out review_stage on Marketplace App
	- Delete orphaned App Release Approval Code Comments rows
	(the child DocType is removed; bench trim-tables will drop the table later)
	"""
	screening_fields = [
		"screening_status",
		"baseline_request",
		"baseline_result",
		"baseline_requirements",
		"result",
		"result_html",
		"result_html_rendered",
		"requirements",
	]

	for field in screening_fields:
		if frappe.db.has_column("App Release Approval Request", field):
			frappe.db.sql(
				f"UPDATE `tabApp Release Approval Request` SET `{field}` = NULL WHERE `{field}` IS NOT NULL"
			)

	if frappe.db.has_column("Marketplace App", "review_stage"):
		frappe.db.sql(
			"UPDATE `tabMarketplace App` SET `review_stage` = NULL WHERE `review_stage` IS NOT NULL"
		)

	if frappe.db.table_exists("tabApp Release Approval Code Comments"):
		frappe.db.sql("DELETE FROM `tabApp Release Approval Code Comments`")
