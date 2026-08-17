# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import boto3
import frappe
from frappe.utils import add_days, add_months, cint, flt, get_first_day, getdate
from frappe.utils.caching import redis_cache

from press.utils.aws import get_press_aws_credentials

JUMP_THRESHOLD_PERCENT = 15


def execute(filters=None):
	frappe.only_for("System Manager")
	filters = filters or {}
	months = get_months(cint(filters.get("lookback_months")) or 6)
	cost_by_service = get_cost_by_service(months)

	rows = build_rows(cost_by_service, months)
	if filters.get("service"):
		rows = [row for row in rows if filters["service"].lower() in row["service"].lower()]

	columns = get_columns(months)
	chart = get_chart(rows, months)
	report_summary = get_report_summary(rows, months)
	return columns, rows, None, chart, report_summary


def get_months(lookback_months):
	first_of_this_month = get_first_day(getdate())
	return [add_months(first_of_this_month, -i) for i in range(lookback_months - 1, -1, -1)]


def get_cost_by_service(months):
	months_key = tuple(str(month) for month in months)

	cost_by_service = {}
	for period in get_cost_and_usage_pages(months_key):
		month = period["TimePeriod"]["Start"]
		for group in period["Groups"]:
			service = group["Keys"][0]
			cost = flt(group["Metrics"]["UnblendedCost"]["Amount"])
			cost_by_service.setdefault(service, {})[month] = cost
	return cost_by_service


def get_ce_client():
	return boto3.client("ce", region_name="us-east-1", **get_press_aws_credentials())


@redis_cache(ttl=60 * 60)
def get_cost_and_usage_pages(months):
	"""get_cost_and_usage paginates via NextPageToken once the account has enough
	distinct line items; reading only the first page silently drops services.
	Cached briefly since Cost Explorer bills $0.01 per request."""
	client = get_ce_client()
	kwargs = {
		"TimePeriod": {"Start": months[0], "End": str(add_days(getdate(), 1))},
		"Granularity": "MONTHLY",
		"Metrics": ["UnblendedCost"],
		"GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
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


def build_rows(cost_by_service, months):
	current_month, previous_month = str(months[-1]), str(months[-2])

	rows = []
	for service, cost_by_month in cost_by_service.items():
		current_cost = cost_by_month.get(current_month, 0)
		previous_cost = cost_by_month.get(previous_month, 0)
		change_amount = current_cost - previous_cost
		change_percent = (change_amount / previous_cost * 100) if previous_cost else 0

		row = {
			"service": service,
			"change_amount": change_amount,
			"change_percent": change_percent,
			"notable_change": abs(change_percent) > JUMP_THRESHOLD_PERCENT,
		}
		for month in months:
			row[month_fieldname(month)] = cost_by_month.get(str(month), 0)
		rows.append(row)

	rows.sort(key=lambda row: row[month_fieldname(months[-1])], reverse=True)
	return rows


def month_fieldname(month):
	return month.strftime("m_%Y_%m")


def month_label(month):
	return month.strftime("%b %Y")


def get_columns(months):
	columns = [{"fieldname": "service", "label": "Service", "fieldtype": "Data", "width": 220}]
	for month in months:
		columns.append(
			{
				"fieldname": month_fieldname(month),
				"label": month_label(month),
				"fieldtype": "Currency",
				"width": 110,
			}
		)
	columns.extend(
		[
			{"fieldname": "change_amount", "label": "Change ($)", "fieldtype": "Currency", "width": 110},
			{"fieldname": "change_percent", "label": "Change (%)", "fieldtype": "Percent", "width": 100},
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
	top_services = rows[:5]
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
	current_month_field = month_fieldname(months[-1])
	total_current = sum(row[current_month_field] for row in rows)
	notable_count = sum(1 for row in rows if row["notable_change"])

	return [
		{
			"value": total_current,
			"label": f"Total Cost — {month_label(months[-1])} (USD)",
			"datatype": "Currency",
			"indicator": "blue",
		},
		{
			"value": len(rows),
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
