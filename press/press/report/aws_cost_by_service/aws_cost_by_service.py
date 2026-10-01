# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import boto3
import frappe
from frappe.utils import add_days, add_months, cint, flt, get_first_day, getdate
from frappe.utils.caching import redis_cache

from press.utils.aws import get_press_aws_credentials

JUMP_THRESHOLD_PERCENT = 15

# Cost Explorer's GroupBy caps out at 2 dimensions per call — SERVICE is fixed,
# this is the user-selectable second dimension for the drill-down breakdown.
BREAKDOWN_DIMENSIONS = {
	"Usage Type": "USAGE_TYPE",
	"Region": "REGION",
}


def execute(filters=None):
	frappe.only_for("System Manager")
	filters = filters or {}
	months = get_months(cint(filters.get("lookback_months")) or 6)
	breakdown_label = filters.get("breakdown_by") or "Usage Type"
	dimension = BREAKDOWN_DIMENSIONS.get(breakdown_label, "USAGE_TYPE")
	cost_by_service = get_cost_by_service(months, dimension)

	rows = build_tree_rows(cost_by_service, months)
	if filters.get("service"):
		rows = filter_by_service(rows, filters["service"])

	columns = get_columns(months, breakdown_label)
	chart = get_chart(rows, months)
	report_summary = get_report_summary(rows, months)
	return columns, rows, None, chart, report_summary


def get_months(lookback_months):
	# Three months minimum: the current part month, plus the two complete months the
	# change column compares.
	lookback_months = max(lookback_months, 3)
	first_of_this_month = get_first_day(getdate())
	return [add_months(first_of_this_month, -i) for i in range(lookback_months - 1, -1, -1)]


def get_cost_by_service(months, dimension):
	"""Nested {service: {breakdown_value: {month: cost}}} — a single 2-dimension
	Cost Explorer query (GroupBy supports up to 2 keys), so drilling into a
	service's cost breakdown needs no extra AWS calls beyond the usual fetch."""
	months_key = tuple(str(month) for month in months)

	cost_by_service = {}
	for period in get_cost_and_usage_pages(months_key, dimension):
		month = period["TimePeriod"]["Start"]
		for group in period["Groups"]:
			service, breakdown_value = group["Keys"]
			cost = flt(group["Metrics"]["UnblendedCost"]["Amount"])
			cost_by_service.setdefault(service, {}).setdefault(breakdown_value, {})[month] = cost
	return cost_by_service


def get_ce_client():
	return boto3.client("ce", region_name="us-east-1", **get_press_aws_credentials())


@redis_cache(ttl=60 * 60)
def get_cost_and_usage_pages(months, dimension):
	"""get_cost_and_usage paginates via NextPageToken once the account has enough
	distinct line items; reading only the first page silently drops services.
	Cached briefly since Cost Explorer bills $0.01 per request."""
	client = get_ce_client()
	kwargs = {
		"TimePeriod": {"Start": months[0], "End": str(add_days(getdate(), 1))},
		"Granularity": "MONTHLY",
		"Metrics": ["UnblendedCost"],
		"GroupBy": [
			{"Type": "DIMENSION", "Key": "SERVICE"},
			{"Type": "DIMENSION", "Key": dimension},
		],
	}

	results = []
	next_page_token = None
	while True:
		if next_page_token:
			kwargs["NextPageToken"] = next_page_token
		response = client.get_cost_and_usage(**kwargs)
		results.extend(response["ResultsByTime"])
		next_page_token = response.get("NextPageToken")
		if not next_page_token:
			return results


def build_tree_rows(cost_by_service, months):
	"""One row per service (indent 0), immediately followed by its cost
	breakdown (indent 1) — the pre-order, parent-then-children layout the
	framework's tree report view expects (frappe-datatable reads `indent` off
	each row and infers the tree structure purely from row order)."""
	# The last month in the window is only billed up to today. Comparing a part month
	# against a whole one reports every service as collapsing, so the change is measured
	# between the two most recent complete months instead. Use Cloud Cost Drilldown to
	# see what the current month is doing day by day.
	current_month, previous_month = str(months[-2]), str(months[-3])
	service_totals = get_service_totals(cost_by_service)

	# Ordered by the month in progress, which is what someone opening this wants to see
	# first even though the change column deliberately ignores it.
	services_sorted = sorted(
		service_totals.items(), key=lambda item: item[1].get(str(months[-1]), 0), reverse=True
	)

	rows = []
	for service, totals in services_sorted:
		rows.append(build_row(service, totals, months, current_month, previous_month, indent=0))

		breakdown_sorted = sorted(
			cost_by_service[service].items(),
			key=lambda item: item[1].get(str(months[-1]), 0),
			reverse=True,
		)
		for breakdown_value, cost_by_month in breakdown_sorted:
			row = build_row(breakdown_value, cost_by_month, months, current_month, previous_month, indent=1)
			row["parent_service"] = service
			rows.append(row)
	return rows


def get_service_totals(cost_by_service):
	totals_by_service = {}
	for service, cost_by_breakdown_value in cost_by_service.items():
		totals = {}
		for cost_by_month in cost_by_breakdown_value.values():
			for month, amount in cost_by_month.items():
				totals[month] = totals.get(month, 0) + amount
		totals_by_service[service] = totals
	return totals_by_service


def build_row(label, cost_by_month, months, current_month, previous_month, indent):
	current_cost = cost_by_month.get(current_month, 0)
	previous_cost = cost_by_month.get(previous_month, 0)
	change_amount = current_cost - previous_cost
	change_percent = (change_amount / previous_cost * 100) if previous_cost else 0

	row = {
		"service": label,
		"indent": indent,
		"change_amount": change_amount,
		"change_percent": change_percent,
		"notable_change": abs(change_percent) > JUMP_THRESHOLD_PERCENT,
	}
	for month in months:
		row[month_fieldname(month)] = cost_by_month.get(str(month), 0)
	return row


def filter_by_service(rows, service_query):
	"""Keep only services matching the search text, along with their
	usage-type children — rows are already parent-then-children ordered."""
	filtered = []
	keep_children = False
	for row in rows:
		if row["indent"] == 0:
			keep_children = service_query.lower() in row["service"].lower()
			if keep_children:
				filtered.append(row)
		elif keep_children:
			filtered.append(row)
	return filtered


def month_fieldname(month):
	return month.strftime("m_%Y_%m")


def month_label(month):
	return month.strftime("%b %Y")


def get_columns(months, breakdown_label):
	columns = [
		{
			"fieldname": "service",
			"label": f"Service / {breakdown_label}",
			"fieldtype": "Data",
			"width": 260,
		}
	]
	for month in months:
		partial = month == months[-1]
		columns.append(
			{
				"fieldname": month_fieldname(month),
				"label": f"{month_label(month)} (MTD)" if partial else month_label(month),
				"fieldtype": "Currency",
				"width": 130 if partial else 110,
			}
		)
	complete = month_label(months[-2])
	columns.extend(
		[
			{
				"fieldname": "change_amount",
				"label": f"Change to {complete} ($)",
				"fieldtype": "Currency",
				"width": 150,
			},
			{
				"fieldname": "change_percent",
				"label": f"Change to {complete} (%)",
				"fieldtype": "Percent",
				"width": 150,
			},
			{
				"fieldname": "notable_change",
				"label": f"Notable Change (>{JUMP_THRESHOLD_PERCENT}%)",
				"fieldtype": "Check",
				"width": 120,
			},
		]
	)
	return columns


def get_chart(rows, months):
	top_services = [row for row in rows if row["indent"] == 0][:5]
	return {
		"data": {
			"labels": [month_label(month) for month in months],
			"datasets": [
				{
					"name": row["service"],
					"values": [row[month_fieldname(month)] for month in months],
				}
				for row in top_services
			],
		},
		"type": "line",
	}


def get_report_summary(rows, months):
	service_rows = [row for row in rows if row["indent"] == 0]
	current_month_field = month_fieldname(months[-1])
	total_current = sum(row[current_month_field] for row in service_rows)
	notable_count = sum(1 for row in service_rows if row["notable_change"])

	return [
		{
			"value": total_current,
			"label": f"Total Cost — {month_label(months[-1])} to date (USD)",
			"datatype": "Currency",
			"indicator": "blue",
		},
		{
			"value": len(service_rows),
			"label": "Services Billed",
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": notable_count,
			"label": f"Services With >{JUMP_THRESHOLD_PERCENT}% Change",
			"datatype": "Int",
			"indicator": "orange",
		},
	]
