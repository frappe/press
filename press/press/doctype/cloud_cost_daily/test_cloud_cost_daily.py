# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cloud_cost_daily.adapters.aws import AWSCostSource
from press.press.doctype.cloud_cost_daily.cloud_cost_daily import store_rows
from press.utils.aws import region_from_usage_type

ACCOUNT = {"label": "test-payer", "provider": "AWS EC2", "cluster": None}


def cost_explorer_response(date, amount, quantity):
	return [
		{
			"TimePeriod": {"Start": date, "End": date},
			"Groups": [
				{
					"Keys": ["Amazon Simple Storage Service", "APS3-TimedStorage-ByteHrs"],
					"Metrics": {
						"AmortizedCost": {"Amount": str(amount), "Unit": "USD"},
						"UnblendedCost": {"Amount": str(amount), "Unit": "USD"},
						"UsageQuantity": {"Amount": str(quantity), "Unit": "GB-Mo"},
					},
				},
				{
					"Keys": ["EC2 - Other", "APS3-EBS:SnapshotUsage"],
					"Metrics": {
						"AmortizedCost": {"Amount": "12.5", "Unit": "USD"},
						"UnblendedCost": {"Amount": "12.5", "Unit": "USD"},
						"UsageQuantity": {"Amount": "400", "Unit": "GB-Mo"},
					},
				},
			],
		}
	]


def collect(periods):
	rows_by_date = {}
	AWSCostSource(ACCOUNT).collect(periods, rows_by_date)
	return rows_by_date


class TestCloudCostDaily(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Cloud Cost Daily", {"account": "test-payer"})

	def test_response_is_flattened_into_one_row_per_usage_type(self):
		rows_by_date = collect(cost_explorer_response("2026-07-01", 10, 300))

		self.assertEqual(list(rows_by_date), ["2026-07-01"])
		rows = rows_by_date["2026-07-01"]
		self.assertEqual(len(rows), 2)
		self.assertEqual(rows[0]["service"], "Amazon Simple Storage Service")
		self.assertEqual(rows[0]["usage_type"], "APS3-TimedStorage-ByteHrs")
		self.assertEqual(rows[0]["amortized_cost"], 10)
		self.assertEqual(rows[0]["usage_quantity"], 300)
		self.assertEqual(rows[0]["usage_unit"], "GB-Mo")

	def test_metered_rows_are_marked_as_billed_not_modelled(self):
		row = collect(cost_explorer_response("2026-07-01", 10, 300))["2026-07-01"][0]

		self.assertEqual(row["provider"], "AWS EC2")
		self.assertEqual(row["source"], "Billed")
		self.assertEqual(row["currency"], "USD")

	def test_region_is_recovered_from_the_usage_type_prefix(self):
		self.assertEqual(region_from_usage_type("APS3-TimedStorage-ByteHrs"), "ap-south-1")
		self.assertEqual(region_from_usage_type("USE1-BoxUsage:m5.large"), "us-east-1")
		self.assertEqual(region_from_usage_type("DataTransfer-Out-Bytes"), "us-east-1")
		self.assertEqual(region_from_usage_type(""), "")

	def test_unknown_prefix_is_kept_rather_than_guessed(self):
		self.assertEqual(region_from_usage_type("ZZZ9-TimedStorage-ByteHrs"), "ZZZ9")

	def test_reingesting_a_day_replaces_it_instead_of_doubling_it(self):
		"""Providers keep revising recent days, so the same day arrives more than once."""
		store_rows("test-payer", collect(cost_explorer_response("2026-07-01", 10, 300)))
		store_rows("test-payer", collect(cost_explorer_response("2026-07-01", 18, 540)))

		rows = frappe.get_all(
			"Cloud Cost Daily",
			{"account": "test-payer", "date": "2026-07-01", "service": "Amazon Simple Storage Service"},
			["amortized_cost", "usage_quantity"],
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].amortized_cost, 18)
		self.assertEqual(rows[0].usage_quantity, 540)

	def test_replacing_one_day_leaves_the_others_alone(self):
		store_rows("test-payer", collect(cost_explorer_response("2026-07-01", 10, 300)))
		store_rows("test-payer", collect(cost_explorer_response("2026-07-02", 11, 330)))
		store_rows("test-payer", collect(cost_explorer_response("2026-07-02", 99, 990)))

		self.assertEqual(
			frappe.db.count("Cloud Cost Daily", {"account": "test-payer", "date": "2026-07-01"}), 2
		)
		self.assertEqual(
			frappe.db.get_value(
				"Cloud Cost Daily",
				{"account": "test-payer", "date": "2026-07-01", "service": "Amazon Simple Storage Service"},
				"amortized_cost",
			),
			10,
		)
