# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import boto3
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, flt, get_datetime_str, getdate, now_datetime

from press.utils.aws import (
	get_cluster_aws_credentials,
	get_press_aws_credentials,
	region_from_usage_type,
)

# Cost Explorer accepts at most two grouping dimensions. Service alone answers "which
# service", which is never actionable on its own; usage type is what separates storing
# more bytes from writing them more often, and it carries the region as a prefix.
GROUP_BY = [
	{"Type": "DIMENSION", "Key": "SERVICE"},
	{"Type": "DIMENSION", "Key": "USAGE_TYPE"},
]
METRICS = ["AmortizedCost", "UnblendedCost", "UsageQuantity"]

STORED_FIELDS = [
	"name",
	"creation",
	"modified",
	"owner",
	"modified_by",
	"date",
	"account",
	"service",
	"usage_type",
	"region",
	"amortized_cost",
	"unblended_cost",
	"usage_quantity",
	"usage_unit",
]


class CloudCostDaily(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Data
		amortized_cost: DF.Currency
		date: DF.Date
		region: DF.Data | None
		service: DF.Data
		unblended_cost: DF.Currency
		usage_quantity: DF.Float
		usage_type: DF.Data | None
		usage_unit: DF.Data | None
	# end: auto-generated types

	pass


def get_cost_accounts():
	"""The AWS accounts to query, as configured on Cloud Cost Settings. Each row is
	queried separately, so a payer account and one of its members must not both be
	listed — Cost Explorer would report the member's spend under both."""
	settings = frappe.get_single("Cloud Cost Settings")

	accounts = []
	for row in settings.accounts:
		if not row.enabled:
			continue
		if row.credentials_from == "Cluster":
			credentials = get_cluster_aws_credentials(row.cluster)
		else:
			credentials = get_press_aws_credentials()
		accounts.append({"label": row.label, "credentials": credentials})
	return accounts


def fetch_cost_and_usage(credentials, start, end):
	"""Daily cost and usage between start (inclusive) and end (exclusive), grouped by
	service and usage type. Cost Explorer bills $0.01 per request, so callers should
	ask for the widest window they need rather than looping a day at a time."""
	client = boto3.client("ce", region_name="us-east-1", **credentials)
	kwargs = {
		"TimePeriod": {"Start": str(getdate(start)), "End": str(getdate(end))},
		"Granularity": "DAILY",
		"Metrics": METRICS,
		"GroupBy": GROUP_BY,
	}

	next_page_token = None
	while True:
		if next_page_token:
			kwargs["NextPageToken"] = next_page_token
		response = client.get_cost_and_usage(**kwargs)
		yield from response["ResultsByTime"]

		next_page_token = response.get("NextPageToken")
		if not next_page_token:
			return


def build_rows(label, periods):
	"""Cost Explorer's nested response flattened into one row per day, service and
	usage type, keyed by the day so each day can be replaced as a whole."""
	rows_by_date = {}
	for period in periods:
		date = period["TimePeriod"]["Start"]
		rows = rows_by_date.setdefault(date, [])

		for group in period["Groups"]:
			service, usage_type = group["Keys"]
			metrics = group["Metrics"]
			usage = metrics.get("UsageQuantity", {})
			rows.append(
				{
					"date": date,
					"account": label,
					"service": service,
					"usage_type": usage_type,
					"region": region_from_usage_type(usage_type),
					"amortized_cost": flt(metrics.get("AmortizedCost", {}).get("Amount")),
					"unblended_cost": flt(metrics.get("UnblendedCost", {}).get("Amount")),
					"usage_quantity": flt(usage.get("Amount")),
					"usage_unit": usage.get("Unit"),
				}
			)
	return rows_by_date


def store_rows(label, rows_by_date):
	"""Replace each day wholesale. AWS restates recent days, and a day is small enough
	that replacing it is simpler and safer than diffing every line against what we hold."""
	timestamp = get_datetime_str(now_datetime())
	user = frappe.session.user

	stored = 0
	for date, rows in rows_by_date.items():
		frappe.db.delete("Cloud Cost Daily", {"account": label, "date": date})
		if not rows:
			continue

		values = [
			(
				frappe.generate_hash(length=10),
				timestamp,
				timestamp,
				user,
				user,
				row["date"],
				row["account"],
				row["service"],
				row["usage_type"],
				row["region"],
				row["amortized_cost"],
				row["unblended_cost"],
				row["usage_quantity"],
				row["usage_unit"],
			)
			for row in rows
		]
		frappe.db.bulk_insert("Cloud Cost Daily", STORED_FIELDS, values)
		stored += len(values)
	return stored


def ingest_account(account, start, end):
	periods = fetch_cost_and_usage(account["credentials"], start, end)
	return store_rows(account["label"], build_rows(account["label"], periods))


def ingest_daily_costs(start=None, end=None):
	"""Pull the trailing window from Cost Explorer for every configured account.
	The window reaches back past yesterday because AWS keeps revising recent days."""
	settings = frappe.get_single("Cloud Cost Settings")
	end = getdate(end) if end else add_days(getdate(), 1)
	start = getdate(start) if start else add_days(end, -(cint(settings.restatement_days) or 5))

	for account in get_cost_accounts():
		try:
			ingest_account(account, start, end)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title="Cloud Cost Ingest Failed",
				message=f"Account {account['label']} between {start} and {end}",
			)


def backfill_history():
	"""Load the full history Cost Explorer still holds, one month per request so no
	single response has to be paginated far."""
	settings = frappe.get_single("Cloud Cost Settings")
	months = cint(settings.backfill_months) or 14

	end = add_days(getdate(), 1)
	for month in range(months):
		window_end = add_months(end, -month)
		window_start = add_months(end, -(month + 1))
		ingest_daily_costs(start=window_start, end=window_end)


def purge_old_rows():
	settings = frappe.get_single("Cloud Cost Settings")
	retention_days = cint(settings.retention_days)
	if not retention_days:
		return

	frappe.db.delete("Cloud Cost Daily", {"date": ("<", add_days(getdate(), -retention_days))})
