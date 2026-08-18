# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from press.press.doctype.cloud_usage_anomaly.cloud_usage_anomaly import (
	detect_anomalies,
	run_daily_pipeline,
)

ACCOUNT = "test-payer"
BASELINE_DAYS = 30
SNAPSHOT_USAGE_TYPE = "APS3-EBS:SnapshotUsage"
STORAGE_USAGE_TYPE = "APS3-TimedStorage-ByteHrs"


class TestCloudUsageAnomaly(FrappeTestCase):
	def setUp(self):
		for doctype in (
			"Cloud Cost Daily",
			"Cloud Usage Driver",
			"Cloud Usage Anomaly Contributor",
			"Cloud Usage Anomaly",
		):
			frappe.db.delete(doctype)

		settings = frappe.get_single("Cloud Cost Settings")
		settings.update(
			{
				"enabled": 1,
				"baseline_days": BASELINE_DAYS,
				"spike_mad_threshold": 3,
				"minimum_daily_cost_impact": 5,
				"minimum_series_cost": 1,
				"level_shift_minimum_change": 20,
				"organic_tolerance": 5,
			}
		)
		settings.save()

	def day(self, offset):
		"""Offset 0 is the oldest day in the detection window, offset 29 the newest."""
		return add_days(getdate(), -BASELINE_DAYS + offset)

	def seed_cost(self, service, usage_type, values, cost_per_unit=0.03):
		for offset, quantity in enumerate(values):
			frappe.get_doc(
				{
					"doctype": "Cloud Cost Daily",
					"date": self.day(offset),
					"account": ACCOUNT,
					"service": service,
					"usage_type": usage_type,
					"region": "ap-south-1",
					"amortized_cost": quantity * cost_per_unit,
					"unblended_cost": quantity * cost_per_unit,
					"usage_quantity": quantity,
					"usage_unit": "GB-Mo",
				}
			).insert()

	def seed_driver(self, driver, values):
		for offset, value in enumerate(values):
			frappe.get_doc(
				{
					"doctype": "Cloud Usage Driver",
					"date": self.day(offset),
					"driver": driver,
					"scope": "",
					"value": value,
					"unit": "GB",
				}
			).insert()

	def test_growth_without_its_driver_is_reported_with_the_day_it_started(self):
		"""Snapshot storage steps up while the snapshots Press knows about stay flat.
		Nothing else explains it, so it is the reaper, and the useful part of the answer
		is which day it stopped."""
		self.seed_cost("EC2 - Other", SNAPSHOT_USAGE_TYPE, [400] * 20 + [700] * 10)
		self.seed_driver("Snapshot Size", [400] * 30)

		self.assertEqual(detect_anomalies(), 1)

		anomaly = frappe.get_last_doc("Cloud Usage Anomaly")
		self.assertEqual(anomaly.detector, "Level Shift")
		self.assertEqual(anomaly.verdict, "Inorganic")
		self.assertEqual(getdate(anomaly.changed_on), self.day(20))
		self.assertEqual(anomaly.metric, "Usage")
		self.assertAlmostEqual(anomaly.baseline_value, 400)
		self.assertAlmostEqual(anomaly.current_value, 700)
		self.assertAlmostEqual(anomaly.change_percent, 75)
		self.assertAlmostEqual(anomaly.driver_change_percent, 0)
		self.assertAlmostEqual(anomaly.daily_cost_impact, 9)
		self.assertEqual(anomaly.status, "Open")

	def test_growth_its_driver_kept_up_with_is_not_an_alert(self):
		"""The same shape of growth, but the backups Press is holding grew with it.
		That is the product working and must not wake anyone."""
		self.seed_cost("Amazon Simple Storage Service", STORAGE_USAGE_TYPE, [400] * 20 + [700] * 10)
		self.seed_driver("Backup Bytes Stored", [400] * 20 + [700] * 10)

		detect_anomalies()

		anomaly = frappe.get_last_doc("Cloud Usage Anomaly")
		self.assertEqual(anomaly.verdict, "Organic")
		self.assertAlmostEqual(anomaly.driver_change_percent, 75)

	def test_usage_type_with_no_driver_is_left_unexplained(self):
		self.seed_cost("AWS Key Management Service", "APS3-KMS-Requests", [400] * 20 + [700] * 10)

		detect_anomalies()

		self.assertEqual(frappe.get_last_doc("Cloud Usage Anomaly").verdict, "No Driver")

	def test_a_series_too_small_to_matter_is_ignored(self):
		"""A series that triples is still not worth a page when it costs cents."""
		self.seed_cost("EC2 - Other", SNAPSHOT_USAGE_TYPE, [1] * 20 + [3] * 10, cost_per_unit=0.01)
		self.seed_driver("Snapshot Size", [1] * 30)

		self.assertEqual(detect_anomalies(), 0)

	def test_a_flat_series_reports_nothing(self):
		self.seed_cost("EC2 - Other", SNAPSHOT_USAGE_TYPE, [400] * 30)
		self.seed_driver("Snapshot Size", [400] * 30)

		self.assertEqual(detect_anomalies(), 0)

	def test_running_again_sharpens_the_same_finding_rather_than_filing_another(self):
		self.seed_cost("EC2 - Other", SNAPSHOT_USAGE_TYPE, [400] * 20 + [700] * 10)
		self.seed_driver("Snapshot Size", [400] * 30)

		detect_anomalies()
		detect_anomalies()

		self.assertEqual(frappe.db.count("Cloud Usage Anomaly"), 1)

	def test_a_finding_an_operator_dismissed_does_not_come_back(self):
		self.seed_cost("EC2 - Other", SNAPSHOT_USAGE_TYPE, [400] * 20 + [700] * 10)
		self.seed_driver("Snapshot Size", [400] * 30)

		detect_anomalies()
		anomaly = frappe.get_last_doc("Cloud Usage Anomaly")
		anomaly.status = "False Positive"
		anomaly.save()

		self.assertEqual(detect_anomalies(), 0)
		self.assertEqual(frappe.db.count("Cloud Usage Anomaly"), 1)

	def test_days_between_samples_are_read_as_zero_not_as_a_gap(self):
		"""Cost Explorer omits days a series did not bill on. Left as gaps they read as
		a drop and a recovery, which is a level shift that never happened."""
		self.seed_cost("EC2 - Other", SNAPSHOT_USAGE_TYPE, [400] * 30)
		frappe.db.delete("Cloud Cost Daily", {"date": self.day(15)})

		self.assertEqual(detect_anomalies(), 0)

	def test_the_pipeline_stays_inert_until_it_is_switched_on(self):
		"""It ships disabled. A scheduler calling Cost Explorer against an account nobody
		has configured would fail every night and bill for the privilege."""
		frappe.db.set_single_value("Cloud Cost Settings", "enabled", 0)
		self.seed_cost("EC2 - Other", SNAPSHOT_USAGE_TYPE, [400] * 20 + [700] * 10)
		self.seed_driver("Snapshot Size", [400] * 30)

		run_daily_pipeline()

		self.assertEqual(frappe.db.count("Cloud Usage Anomaly"), 0)
