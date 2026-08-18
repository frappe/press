# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Walk down from a service that moved to the usage type, region and day behind it.

Group by Service to see which one moved, set that service and group by Usage Type to
see whether it was storing more, writing more often or moving more bytes, then group by
Date to find the day it started. Every level is served from Cloud Cost Daily, so none of
it costs a Cost Explorer request.
"""

import frappe
from frappe.utils import add_days, cint, flt, getdate

GROUP_FIELDS = {
	"Service": "service",
	"Usage Type": "usage_type",
	"Region": "region",
	"Date": "date",
}


def execute(filters=None):
	frappe.only_for("System Manager")
	filters = frappe._dict(filters or {})
	group_field = GROUP_FIELDS.get(filters.group_by or "Service", "service")

	from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
	window = (to_date - from_date).days + 1
	rows = get_rows(filters, add_days(from_date, -window), to_date)

	if group_field == "date":
		data = build_daily_rows(rows, from_date, to_date)
	else:
		data = build_grouped_rows(rows, group_field, from_date, to_date)

	columns = get_columns(filters.group_by or "Service")
	chart = get_chart(rows, from_date, to_date)
	return columns, data, None, chart, get_report_summary(data)


def get_rows(filters, from_date, to_date):
	conditions = {"date": ("between", [from_date, to_date])}
	for fieldname in ("account", "service", "usage_type", "region"):
		if filters.get(fieldname):
			conditions[fieldname] = ("like", f"%{filters[fieldname]}%")

	return frappe.get_all(
		"Cloud Cost Daily",
		conditions,
		[
			"date",
			"account",
			"service",
			"usage_type",
			"region",
			"amortized_cost",
			"usage_quantity",
			"usage_unit",
		],
		order_by="date asc",
		limit_page_length=0,
	)


def build_grouped_rows(rows, group_field, from_date, to_date):
	"""Each group's total over the window against its total over the window before it,
	so a step shows up as a percentage rather than as two numbers to subtract by eye."""
	groups = {}
	for row in rows:
		key = row.get(group_field) or "(none)"
		group = groups.setdefault(
			key,
			{group_field: key, "cost": 0, "previous_cost": 0, "usage": 0, "previous_usage": 0, "unit": ""},
		)
		current = getdate(row.date) >= from_date
		group["cost" if current else "previous_cost"] += flt(row.amortized_cost)
		group["usage" if current else "previous_usage"] += flt(row.usage_quantity)
		group["unit"] = group["unit"] or row.usage_unit

	days = (to_date - from_date).days + 1
	for group in groups.values():
		group["daily_cost"] = group["cost"] / days
		group["change_amount"] = group["cost"] - group["previous_cost"]
		group["change_percent"] = percent_change(group["previous_cost"], group["cost"])
		group["usage_change_percent"] = percent_change(group["previous_usage"], group["usage"])

	return sorted(groups.values(), key=lambda group: group["cost"], reverse=True)


def build_daily_rows(rows, from_date, to_date):
	"""One row per day, each compared with the day before it. This is the level the
	question "when did it start" is actually answered at."""
	totals = {}
	units = {}
	for row in rows:
		date = getdate(row.date)
		total = totals.setdefault(date, {"cost": 0, "usage": 0})
		total["cost"] += flt(row.amortized_cost)
		total["usage"] += flt(row.usage_quantity)
		units[date] = units.get(date) or row.usage_unit

	data = []
	date = from_date
	while date <= to_date:
		today = totals.get(date, {"cost": 0, "usage": 0})
		yesterday = totals.get(add_days(date, -1), {"cost": 0, "usage": 0})
		data.append(
			{
				"date": date,
				"cost": today["cost"],
				"previous_cost": yesterday["cost"],
				"daily_cost": today["cost"],
				"change_amount": today["cost"] - yesterday["cost"],
				"change_percent": percent_change(yesterday["cost"], today["cost"]),
				"usage": today["usage"],
				"previous_usage": yesterday["usage"],
				"usage_change_percent": percent_change(yesterday["usage"], today["usage"]),
				"unit": units.get(date, ""),
			}
		)
		date = add_days(date, 1)
	return data


def percent_change(previous, current):
	if not previous:
		return 100.0 if current else 0.0
	return (current - previous) / abs(previous) * 100


def get_columns(group_by):
	group_field = GROUP_FIELDS[group_by]
	first = {
		"fieldname": group_field,
		"label": group_by,
		"fieldtype": "Date" if group_field == "date" else "Data",
		"width": 240,
	}

	return [
		first,
		{"fieldname": "cost", "label": "Cost (USD)", "fieldtype": "Currency", "width": 120},
		{"fieldname": "previous_cost", "label": "Previous (USD)", "fieldtype": "Currency", "width": 120},
		{"fieldname": "change_amount", "label": "Change (USD)", "fieldtype": "Currency", "width": 120},
		{"fieldname": "change_percent", "label": "Change", "fieldtype": "Percent", "width": 100},
		{"fieldname": "daily_cost", "label": "Per Day (USD)", "fieldtype": "Currency", "width": 120},
		{"fieldname": "usage", "label": "Usage", "fieldtype": "Float", "width": 120},
		{"fieldname": "usage_change_percent", "label": "Usage Change", "fieldtype": "Percent", "width": 120},
		{"fieldname": "unit", "label": "Unit", "fieldtype": "Data", "width": 90},
	]


def get_chart(rows, from_date, to_date):
	totals = {}
	for row in rows:
		date = getdate(row.date)
		if date >= from_date:
			totals[date] = totals.get(date, 0) + flt(row.amortized_cost)

	labels, values = [], []
	date = from_date
	while date <= to_date:
		labels.append(str(date))
		values.append(flt(totals.get(date, 0), 2))
		date = add_days(date, 1)

	return {
		"data": {"labels": labels, "datasets": [{"name": "Daily Cost (USD)", "values": values}]},
		"type": "line",
	}


def get_report_summary(data):
	total = sum(row["cost"] for row in data)
	risers = [row for row in data if row["change_amount"] > 0]
	biggest = max(risers, key=lambda row: row["change_amount"], default=None)

	return [
		{"value": total, "label": "Total (USD)", "datatype": "Currency", "indicator": "blue"},
		{
			"value": sum(row["change_amount"] for row in data),
			"label": "Change vs Previous Window (USD)",
			"datatype": "Currency",
			"indicator": "orange",
		},
		{
			"value": biggest["change_amount"] if biggest else 0,
			"label": "Largest Increase (USD)",
			"datatype": "Currency",
			"indicator": "red",
		},
		{"value": cint(len(data)), "label": "Rows", "datatype": "Int", "indicator": "blue"},
	]
