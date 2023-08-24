import frappe
import datetime
from datetime import timedelta
from itertools import cycle

agents = [
	"shadrak@erpnext.com",
	"balamurali@erpnext.com",
	"aditya@erpnext.com",
	"athul@erpnext.com",
	"rutwik@frappe.io",
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
	weekday_cycle = agents
	# weekday_cycle.remove("aditya@erpnext.com")
	weekday_cycle = cycle(weekday_cycle)

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

	for weekday in next_weekdays(from_, till):
		agent = next(weekday_cycle)
		contact = frappe.get_last_doc("Contact", {"email_id": agent})
		if frappe.db.exists(
			"Event",
			{
				"subject": ("like", "%Dedicated Support"),
				"starts_on": weekday,
				"ends_on": datetime.datetime.combine(weekday, datetime.time(23, 59)),
			},
		):
			continue
		frappe.get_doc(
			{
				"doctype": "Event",
				"subject": f"{contact.first_name} on Dedicated Support",
				"starts_on": weekday,
				"ends_on": datetime.datetime.combine(weekday, datetime.time(23, 59)),
				"all_day": 1,
				"event_type": "Public",
			}
		).insert()
