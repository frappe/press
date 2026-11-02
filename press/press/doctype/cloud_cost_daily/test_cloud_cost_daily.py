# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cloud_cost_daily.adapters.aws import AWSCostSource
from press.press.doctype.cloud_cost_daily.cloud_cost_daily import get_cost_accounts, store_rows
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


class TestCostAccounts(FrappeTestCase):
	"""Accounts are worked out from what Press already knows, so there is nothing to
	configure and no list to keep in step with the clusters."""

	def set_aws_key(self, value):
		frappe.db.set_single_value("Press Settings", "aws_access_key_id", value)

	def test_aws_is_one_account_from_press_settings(self):
		"""Per-cluster AWS keys run machines, they do not read bills. Querying a member
		account the payer already covers would count its spend twice."""
		self.set_aws_key("AKIATESTONLY")

		aws = [account for account in get_cost_accounts() if account["provider"] == "AWS EC2"]

		self.assertEqual(len(aws), 1)
		self.assertIsNone(aws[0]["cluster"])

	def test_no_aws_account_when_no_keys_are_configured(self):
		self.set_aws_key("")

		self.assertEqual([a for a in get_cost_accounts() if a["provider"] == "AWS EC2"], [])

	def test_every_other_provider_is_read_from_its_own_cluster(self):
		"""Only AWS keeps billing credentials centrally. The rest hold their token on
		the cluster, so that is where each account has to come from."""
		for account in get_cost_accounts():
			if account["provider"] != "AWS EC2":
				self.assertTrue(account["cluster"])

	def test_archived_clusters_are_not_queried(self):
		archived = frappe.get_all("Cluster", {"status": "Archived"}, pluck="name")
		labels = [account["label"] for account in get_cost_accounts()]

		for cluster in archived:
			self.assertNotIn(cluster, labels)
