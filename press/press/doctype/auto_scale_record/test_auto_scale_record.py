# Copyright (c) 2025, Frappe and Contributors
# See license.txt
from __future__ import annotations

from datetime import timedelta
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from press.api.server import schedule_auto_scale
from press.press.doctype.auto_scale_record.auto_scale_record import (
	AutoScaleRecord,
	is_secondary_ready_for_scale_down,
)
from press.press.doctype.nfs_volume_detachment.nfs_volume_detachment import NFSVolumeDetachment
from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import (
	PrometheusAlertRule,
)
from press.press.doctype.server.test_server import create_test_server


def mimic_memory_usage(is_high: bool = False):
	return {"memory": 0.2} if not is_high else {"memory": 0.9}


def mimic_cpu_usage(is_high: bool = False):
	return {"vcpu": 0.2} if not is_high else {"vcpu": 0.9}


def mimic_get_cpu_and_memory_usage(is_high: bool = False):
	cpu_usage = mimic_cpu_usage(is_high)
	cpu_usage.update(mimic_memory_usage(is_high))
	return cpu_usage


@patch.object(AutoScaleRecord, "after_insert", new=Mock())
@patch.object(PrometheusAlertRule, "on_update", new=Mock())
@patch.object(NFSVolumeDetachment, "after_insert", new=Mock())
class UnitTestAutoScaleRecord(TestCase):
	"""
	Unit tests for AutoScaleRecord.
	Use this class for testing individual functions and methods.
	"""

	@classmethod
	def setUpClass(cls):
		cls.primary_server = create_test_server()
		cls.secondary_server = create_test_server()
		cls.primary_server.secondary_server = cls.secondary_server.name
		cls.primary_server.save()

	def test_scheduled_auto_scale(self):
		first_auto_scale_window = [
			frappe.utils.now_datetime() + timedelta(minutes=5),
			frappe.utils.now_datetime() + timedelta(minutes=6),
		]

		with self.assertRaises(frappe.ValidationError):
			# Scales must be atleast 60 minutes apart
			schedule_auto_scale(
				self.primary_server.name,
				scheduled_scale_up_time=first_auto_scale_window[0],
				scheduled_scale_down_time=first_auto_scale_window[1],
			)

		first_auto_scale_window[1] = frappe.utils.now_datetime() + timedelta(minutes=70)
		schedule_auto_scale(
			self.primary_server.name,
			scheduled_scale_up_time=first_auto_scale_window[0],
			scheduled_scale_down_time=first_auto_scale_window[1],
		)

		# A scheduled auto scale cannot be created if there is a conflicting auto scale window
		# Trying to scale up when already scaled up according to the previous schedule
		conflicting_auto_scale_window = [
			frappe.utils.now_datetime() + timedelta(minutes=5),
			frappe.utils.now_datetime() + timedelta(minutes=70),
		]

		with self.assertRaises(frappe.ValidationError):
			# Scales must be atleast 60 minutes apart
			schedule_auto_scale(
				self.primary_server.name,
				scheduled_scale_up_time=conflicting_auto_scale_window[0],
				scheduled_scale_down_time=conflicting_auto_scale_window[1],
			)

		# Trying to scale up in the past
		conflicting_auto_scale_window[0] = frappe.utils.now_datetime() + timedelta(minutes=-10)
		with self.assertRaises(frappe.ValidationError):
			schedule_auto_scale(
				self.primary_server.name,
				scheduled_scale_up_time=conflicting_auto_scale_window[0],
				scheduled_scale_down_time=conflicting_auto_scale_window[1],
			)

	def test_trigger_creation(self):
		self.primary_server.add_automated_scaling_triggers(
			metric="CPU",
			action="Scale Up",
			threshold=75.0,
		)

		prometheus_alert_rule: PrometheusAlertRule = frappe.get_doc(
			"Prometheus Alert Rule", f"Auto Scale Up Trigger - {self.primary_server.name}"
		)

		expected_expression_only_cpu = (
			f"""((
				1 - avg by (instance) (
						rate(node_cpu_seconds_total{{instance="{self.primary_server.name}", job="node", mode="idle"}}[4m])
				)
		) * 100 > 75.0)""".strip()
			.replace(" ", "")
			.replace("\n", "")
			.replace("\t", "")
		)

		actual_expression = (
			prometheus_alert_rule.expression.strip().replace(" ", "").replace("\n", "").replace("\t", "")
		)
		self.assertEqual(expected_expression_only_cpu, actual_expression)

		self.primary_server.add_automated_scaling_triggers(
			metric="Memory",
			action="Scale Up",
			threshold=55.0,
		)

		expected_expression_cpu_and_memory = (
			f"""((
				1 - avg by (instance) (
						rate(node_cpu_seconds_total{{instance="{self.primary_server.name}", job="node", mode="idle"}}[4m])
				)
		) * 100 > 75.0) OR ((
			1 -
			(
				avg_over_time(node_memory_MemAvailable_bytes{{instance="{self.primary_server.name}", job="node"}}[4m])
				/
				avg_over_time(node_memory_MemTotal_bytes{{instance="{self.primary_server.name}", job="node"}}[4m])
			)
		) * 100 > 55.0)""".strip()
			.replace(" ", "")
			.replace("\n", "")
			.replace("\t", "")
		)

		prometheus_alert_rule = prometheus_alert_rule.reload()
		actual_expression = (
			prometheus_alert_rule.expression.strip().replace(" ", "").replace("\n", "").replace("\t", "")
		)
		self.assertEqual(expected_expression_cpu_and_memory, actual_expression)
		memory_trigger = frappe.get_last_doc("Auto Scale Trigger", {"metric": "Memory"})
		self.primary_server.remove_automated_scaling_triggers(triggers=[memory_trigger.name])

		prometheus_alert_rule = prometheus_alert_rule.reload()
		actual_expression = (
			prometheus_alert_rule.expression.strip().replace(" ", "").replace("\n", "").replace("\t", "")
		)

		self.assertEqual(expected_expression_only_cpu, actual_expression)
		self.assertEqual(prometheus_alert_rule.enabled, 1)

	def test_dropping_secondary_server_with_triggers(self):
		self.primary_server.add_automated_scaling_triggers(
			metric="CPU",
			action="Scale Up",
			threshold=75.0,
		)

		with self.assertRaises(frappe.ValidationError) as context:
			nfs_volume_detachment: "NFSVolumeDetachment" = frappe.get_doc(
				{"doctype": "NFS Volume Detachment", "primary_server": self.primary_server.name}
			)
			nfs_volume_detachment.insert(ignore_permissions=True)

		self.assertIn(
			"Please remove all auto scale triggers before dropping the secondary server",
			str(context.exception),
		)

		auto_scale_triggers = frappe.get_all(
			"Auto Scale Trigger", filters={"parent": self.primary_server.name}, pluck="name"
		)
		self.primary_server.remove_automated_scaling_triggers(triggers=auto_scale_triggers)

		nfs_volume_detachment: "NFSVolumeDetachment" = frappe.get_doc(
			{"doctype": "NFS Volume Detachment", "primary_server": self.primary_server.name}
		)
		nfs_volume_detachment.insert(ignore_permissions=True)

	def test_remove_all_triggers(self):
		self.primary_server.add_automated_scaling_triggers(
			metric="CPU",
			action="Scale Up",
			threshold=75.0,
		)
		auto_scale_triggers = frappe.get_all(
			"Auto Scale Trigger", filters={"parent": self.primary_server.name}, pluck="name"
		)
		self.primary_server.remove_automated_scaling_triggers(triggers=auto_scale_triggers)

		prometheus_alert_rule = frappe.get_doc(
			"Prometheus Alert Rule", {"name": f"Auto Scale Up Trigger - {self.primary_server.name}"}
		)
		self.assertEqual(prometheus_alert_rule.enabled, 0)

	def test_scale_down_trigger_creation(self):
		self.primary_server.add_automated_scaling_triggers(
			metric="CPU",
			action="Scale Down",
			threshold=25.0,
		)

		prometheus_alert_rule: PrometheusAlertRule = frappe.get_doc(
			"Prometheus Alert Rule",
			{"name": f"Auto Scale Down Trigger - {self.primary_server.name}"},
		)
		expected_expression_only_cpu = (
			f"""((
				1 - avg by (instance) (
						rate(node_cpu_seconds_total{{instance="{self.primary_server.name}", job="node", mode="idle"}}[4m])
				)
		) * 100 < 25.0)""".strip()
			.replace(" ", "")
			.replace("\n", "")
			.replace("\t", "")
		)

		actual_expression = (
			prometheus_alert_rule.expression.strip().replace(" ", "").replace("\n", "").replace("\t", "")
		)
		self.assertEqual(expected_expression_only_cpu, actual_expression)

	def test_is_secondary_ready_for_scale_down(self):
		server = self.primary_server
		server.add_automated_scaling_triggers(
			metric="CPU",
			action="Scale Down",
			threshold=25.0,
		)

		with patch(
			"press.api.server.get_cpu_and_memory_usage",
			side_effect=lambda srv: mimic_get_cpu_and_memory_usage(is_high=True),
		):
			# Resource usage is still high on secondary we should not be ready for scale down
			self.assertFalse(is_secondary_ready_for_scale_down(server))

		with patch(
			"press.api.server.get_cpu_and_memory_usage",
			side_effect=lambda srv: mimic_get_cpu_and_memory_usage(is_high=False),
		):
			# Resource usage is now low on secondary we should be ready for scale down
			self.assertTrue(is_secondary_ready_for_scale_down(server))
