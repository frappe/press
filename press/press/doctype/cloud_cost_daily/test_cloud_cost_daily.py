# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cloud_cost_daily.cloud_cost_daily import build_rows, store_rows
from press.utils.aws import region_from_usage_type


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


class TestCloudCostDaily(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Cloud Cost Daily", {"account": "test-payer"})

	def test_response_is_flattened_into_one_row_per_usage_type(self):
		rows_by_date = build_rows("test-payer", cost_explorer_response("2026-07-01", 10, 300))

		self.assertEqual(list(rows_by_date), ["2026-07-01"])
		rows = rows_by_date["2026-07-01"]
		self.assertEqual(len(rows), 2)
		self.assertEqual(rows[0]["service"], "Amazon Simple Storage Service")
		self.assertEqual(rows[0]["usage_type"], "APS3-TimedStorage-ByteHrs")
		self.assertEqual(rows[0]["amortized_cost"], 10)
		self.assertEqual(rows[0]["usage_quantity"], 300)
		self.assertEqual(rows[0]["usage_unit"], "GB-Mo")

	def test_region_is_recovered_from_the_usage_type_prefix(self):
		self.assertEqual(region_from_usage_type("APS3-TimedStorage-ByteHrs"), "ap-south-1")
		self.assertEqual(region_from_usage_type("USE1-BoxUsage:m5.large"), "us-east-1")
		self.assertEqual(region_from_usage_type("DataTransfer-Out-Bytes"), "us-east-1")
		self.assertEqual(region_from_usage_type(""), "")

	def test_unknown_prefix_is_kept_rather_than_guessed(self):
		self.assertEqual(region_from_usage_type("ZZZ9-TimedStorage-ByteHrs"), "ZZZ9")

	def test_reingesting_a_day_replaces_it_instead_of_doubling_it(self):
		"""AWS keeps revising recent days, so the same day arrives more than once."""
		store_rows("test-payer", build_rows("test-payer", cost_explorer_response("2026-07-01", 10, 300)))
		store_rows("test-payer", build_rows("test-payer", cost_explorer_response("2026-07-01", 18, 540)))

		rows = frappe.get_all(
			"Cloud Cost Daily",
			{"account": "test-payer", "date": "2026-07-01", "service": "Amazon Simple Storage Service"},
			["amortized_cost", "usage_quantity"],
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].amortized_cost, 18)
		self.assertEqual(rows[0].usage_quantity, 540)

	def test_replacing_one_day_leaves_the_others_alone(self):
		store_rows("test-payer", build_rows("test-payer", cost_explorer_response("2026-07-01", 10, 300)))
		store_rows("test-payer", build_rows("test-payer", cost_explorer_response("2026-07-02", 11, 330)))
		store_rows("test-payer", build_rows("test-payer", cost_explorer_response("2026-07-02", 99, 990)))

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
