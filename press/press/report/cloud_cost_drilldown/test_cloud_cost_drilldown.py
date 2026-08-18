# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from press.press.report.cloud_cost_drilldown.cloud_cost_drilldown import execute

ACCOUNT = "test-payer"


class TestCloudCostDrilldown(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Cloud Cost Daily")

	def seed(self, date, service, usage_type, cost):
		frappe.get_doc(
			{
				"doctype": "Cloud Cost Daily",
				"date": date,
				"account": ACCOUNT,
				"service": service,
				"usage_type": usage_type,
				"region": "ap-south-1",
				"amortized_cost": cost,
				"unblended_cost": cost,
				"usage_quantity": cost * 10,
				"usage_unit": "GB-Mo",
			}
		).insert()

	def seed_window(self, start, days, service, usage_type, cost):
		for offset in range(days):
			self.seed(add_days(start, offset), service, usage_type, cost)

	def run_report(self, group_by, **filters):
		from_date, to_date = add_days(getdate(), -7), add_days(getdate(), -1)
		return execute({"from_date": from_date, "to_date": to_date, "group_by": group_by, **filters})

	def test_grouping_by_service_compares_the_window_with_the_one_before_it(self):
		"""The previous window is the same length, immediately before. Comparing a part
		period against a whole one is what made the monthly view read as a collapse."""
		self.seed_window(add_days(getdate(), -14), 7, "AmazonS3", "APS3-TimedStorage-ByteHrs", 10)
		self.seed_window(add_days(getdate(), -7), 7, "AmazonS3", "APS3-TimedStorage-ByteHrs", 15)

		_, data, _, _, _ = self.run_report("Service")

		self.assertEqual(len(data), 1)
		self.assertAlmostEqual(data[0]["cost"], 105)
		self.assertAlmostEqual(data[0]["previous_cost"], 70)
		self.assertAlmostEqual(data[0]["change_percent"], 50)

	def test_usage_types_separate_storing_more_from_writing_more_often(self):
		"""The whole point of the second level: S3 being up says nothing, storage being
		up while requests are flat says the reaper stopped."""
		self.seed_window(add_days(getdate(), -7), 7, "AmazonS3", "APS3-TimedStorage-ByteHrs", 15)
		self.seed_window(add_days(getdate(), -7), 7, "AmazonS3", "APS3-Requests-Tier1", 2)

		_, data, _, _, _ = self.run_report("Usage Type", service="AmazonS3")

		by_usage_type = {row["usage_type"]: row["cost"] for row in data}
		self.assertAlmostEqual(by_usage_type["APS3-TimedStorage-ByteHrs"], 105)
		self.assertAlmostEqual(by_usage_type["APS3-Requests-Tier1"], 14)

	def test_grouping_by_date_gives_a_row_for_every_day_in_the_window(self):
		self.seed_window(add_days(getdate(), -7), 7, "AmazonS3", "APS3-TimedStorage-ByteHrs", 10)

		columns, data, _, chart, _ = self.run_report("Date")

		self.assertEqual(columns[0]["fieldname"], "date")
		self.assertEqual(len(data), 7)
		self.assertEqual(len(chart["data"]["labels"]), 7)
		self.assertAlmostEqual(data[-1]["cost"], 10)

	def test_a_day_with_no_rows_reads_as_zero_rather_than_going_missing(self):
		self.seed_window(add_days(getdate(), -7), 7, "AmazonS3", "APS3-TimedStorage-ByteHrs", 10)
		frappe.db.delete("Cloud Cost Daily", {"date": add_days(getdate(), -4)})

		_, data, _, _, _ = self.run_report("Date")

		blank = [row for row in data if row["date"] == add_days(getdate(), -4)]
		self.assertEqual(len(blank), 1)
		self.assertEqual(blank[0]["cost"], 0)

	def test_summary_names_the_largest_increase(self):
		self.seed_window(add_days(getdate(), -14), 7, "EC2 - Other", "APS3-EBS:SnapshotUsage", 5)
		self.seed_window(add_days(getdate(), -7), 7, "EC2 - Other", "APS3-EBS:SnapshotUsage", 20)
		self.seed_window(add_days(getdate(), -7), 7, "AmazonS3", "APS3-TimedStorage-ByteHrs", 3)

		_, _, _, _, summary = self.run_report("Service")

		self.assertAlmostEqual(summary[2]["value"], 105)
