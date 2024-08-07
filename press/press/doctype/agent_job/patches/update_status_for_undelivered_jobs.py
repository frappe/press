import frappe
from frappe.utils import add_to_date, now_datetime


def execute():
	five_minute_ago = add_to_date(now_datetime(), minutes=-5)

	frappe.db.sql(
		"""
		UPDATE `tabAgent Job`
			SET status = 'Delivery Failure'
		WHERE job_id = 0 and status = 'Undelivered' and creation <= %s
	""",
		five_minute_ago,
	)
