# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import boto3
from frappe.utils import flt, getdate

from press.press.doctype.cloud_cost_daily.adapters.base import BILLED, CostSource
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


class AWSCostSource(CostSource):
	provider = "AWS EC2"
	source = BILLED
	currency = "USD"

	def credentials(self):
		if self.cluster:
			return get_cluster_aws_credentials(self.cluster)
		return get_press_aws_credentials()

	def fetch(self, start, end):
		"""Cost Explorer bills $0.01 per request, so the whole window is asked for at
		once rather than a day at a time."""
		client = boto3.client("ce", region_name="us-east-1", **self.credentials())
		kwargs = {
			"TimePeriod": {"Start": str(getdate(start)), "End": str(getdate(end))},
			"Granularity": "DAILY",
			"Metrics": METRICS,
			"GroupBy": GROUP_BY,
		}

		rows_by_date = {}
		next_page_token = None
		while True:
			if next_page_token:
				kwargs["NextPageToken"] = next_page_token
			response = client.get_cost_and_usage(**kwargs)
			self.collect(response["ResultsByTime"], rows_by_date)

			next_page_token = response.get("NextPageToken")
			if not next_page_token:
				return rows_by_date

	def collect(self, periods, rows_by_date):
		for period in periods:
			date = period["TimePeriod"]["Start"]
			rows = rows_by_date.setdefault(date, [])

			for group in period["Groups"]:
				service, usage_type = group["Keys"]
				metrics = group["Metrics"]
				usage = metrics.get("UsageQuantity", {})
				row = self.row(
					date,
					service,
					usage_type,
					region_from_usage_type(usage_type),
					flt(metrics.get("AmortizedCost", {}).get("Amount")),
					flt(usage.get("Amount")),
					usage.get("Unit"),
				)
				row["unblended_cost"] = flt(metrics.get("UnblendedCost", {}).get("Amount"))
				rows.append(row)
