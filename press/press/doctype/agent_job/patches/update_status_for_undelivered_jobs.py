import frappe
from frappe.utils import now_datetime, add_to_date


def execute():
	one_minute_ago = add_to_date(now_datetime(), minutes=-1)

	frappe.db.sql(
		"""
		UPDATE `tabAgent Job`
			SET status = 'Delivery Failure'
		WHERE job_id = 0 and status = 'Undelivered' and creation <= %s
	""",
		one_minute_ago,
	)
