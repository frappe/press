import frappe
from frappe.utils import now_datetime, add_to_date


def execute():
	five_minutes_ago = add_to_date(now_datetime(), minutes=-5)

	frappe.db.sql(
		"""
		UPDATE `tabAgent Job`
			SET status = 'Delivery Failure'
		WHERE job_id = 0 and status = 'Undelivered' and creation <= %s
	""",
		five_minutes_ago,
	)
