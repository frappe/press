import datetime
from datetime import timedelta
from itertools import cycle

import frappe

agents = [
	"jayanta@frappe.io",
	"saurabh@erpnext.com",
	"mangesh@frappe.io",
	"bowrna@frappe.io",
	"shadrak@erpnext.com",
	"aradhya@frappe.io",
	"sabu@frappe.io",
	"tanmoy@frappe.io",
	"aysha@frappe.io",
	"ritwik.p@frappe.io",
	"balamurali@erpnext.com",
]


def get_weekends(
	start_date: datetime.date,
	end_date: datetime.date,
) -> list[tuple[datetime.date, datetime.date]]:
	"""Returns a list of weekends till the given date"""
	weekends = []
	dt = start_date
	while dt <= end_date:
		if dt.weekday() == 6:  # 0 is monday, 6 is sunday
			weekends.append((dt - datetime.timedelta(days=1), dt))
		dt += timedelta(days=1)
	return weekends


def next_weekdays(from_: datetime.date, till: datetime.date):
	"""Returns the next weekday"""
	dt = from_
	while dt <= till:
		dt += timedelta(days=1)
		if dt.weekday() not in [5, 6]:  # 0 is monday, 6 is sunday
			yield dt


def main():
	agent_cycle = cycle(agents)

	from_ = datetime.date.today()
	till = datetime.date(2023, 7, 20)

	for weekend in get_weekends(from_, till):
		agent = next(agent_cycle)
		contact = frappe.get_doc("User", {"name": agent})
		if frappe.db.exists(
			"Event",
			{
				"subject": ("like", "%Weekend Support"),
				"starts_on": weekend[0],
				"ends_on": weekend[1],
			},
		):
			continue
		frappe.get_doc(
			{
				"doctype": "Event",
				"subject": f"{contact.first_name} on Weekend Support",
				"starts_on": weekend[0],
				"ends_on": weekend[1],
				"all_day": 1,
				"event_type": "Public",
			}
		).insert()
