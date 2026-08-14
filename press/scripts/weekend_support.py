import datetime
from datetime import timedelta
from itertools import cycle

import frappe
from frappe.utils import add_months

agents = [
	"aysha@frappe.io",
	"ritwik.p@frappe.io",
	"balamurali@erpnext.com",
	"jayanta@frappe.io",
	"saurabh@erpnext.com",
	"shadrak@erpnext.com",
	"aradhya@frappe.io",
	"sabu@frappe.io",
	"tanmoy@frappe.io",
	"prathamesh@frappe.io",
	"sidhant@frappe.io",
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


def last_assigned_agent() -> str | None:
	"""Returns the agent on support for the latest weekend that's already scheduled"""
	subject = frappe.db.get_value(
		"Event",
		{"subject": ("like", "%on Weekend Support")},
		"subject",
		order_by="starts_on desc",
	)
	if not subject:
		return None
	first_name = subject.split(" on Weekend Support")[0]
	return frappe.db.get_value("User", {"name": ("in", agents), "first_name": first_name}, "name")


def main():
	agent_cycle = cycle(agents)
	last_agent = last_assigned_agent()
	if last_agent:
		# wind the cycle forward so the next weekend gets the next agent
		for agent in agent_cycle:
			if agent == last_agent:
				break

	from_ = datetime.date.today()
	till = add_months(from_, 3)

	for weekend in get_weekends(from_, till):
		if frappe.db.exists(
			"Event",
			{
				"subject": ("like", "%Weekend Support"),
				"starts_on": weekend[0],
				"ends_on": weekend[1],
			},
		):
			continue
		agent = next(agent_cycle)
		contact = frappe.get_doc("User", {"name": agent})
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
