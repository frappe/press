# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import PrometheusAlertRule


@patch.object(Agent, "update_monitor_rules", new=Mock())
def create_test_prometheus_alert_rule(name="Sites Down") -> PrometheusAlertRule:
	return frappe.get_doc(  # type: ignore
		{
			"doctype": "Prometheus Alert Rule",
			"name": name,
			"description": "Sites didn't respond with http 200",
			"severity": "Critical",
			"group_wait": "1m",
			"group_interval": "1m",
			"repeat_interval": "1h",
			"group_by": '["alertname", "cluster", "server", "instance"]',
			"expression": 'probe_success{job="site"} == 0 and probe_http_status_code != 429',
			"for": "4m",
			"enable_reactions": True,
		},
	).insert(ignore_if_duplicate=True)


class TestPrometheusAlertRule(FrappeTestCase):
	"""Tests for PrometheusAlertRule.get_rule(), get_route(), and validate() guards."""

	_MODULE = "press.press.doctype.prometheus_alert_rule.prometheus_alert_rule"

	def _make_doc(self, **kwargs):
		from types import SimpleNamespace

		defaults = dict(
			name="TestAlert",
			description="Test alert description",
			severity="Warning",
			expression="up == 0",
			labels='{"team": "ops"}',
			annotations='{"summary": "Something is down"}',
			group_by='["alertname"]',
			group_wait="30s",
			group_interval="5m",
			repeat_interval="1h",
			enabled=1,
			alert_preview="",
			route_preview="",
		)
		defaults.update(kwargs)
		# Frappe's `get` method is used for the "for" field (reserved keyword)
		obj = SimpleNamespace(**defaults)
		obj.get = lambda field, default=None: getattr(obj, "for_duration", "4m")
		return obj

	def test_get_rule_includes_name_and_expression(self):
		doc = self._make_doc(name="MyAlert", expression="probe_success == 0")
		rule = PrometheusAlertRule.get_rule(doc)
		self.assertEqual(rule["alert"], "MyAlert")
		self.assertEqual(rule["expr"], "probe_success == 0")

	def test_get_rule_merges_severity_into_labels(self):
		doc = self._make_doc(severity="Critical", labels='{"team": "ops"}')
		rule = PrometheusAlertRule.get_rule(doc)
		self.assertEqual(rule["labels"]["severity"], "critical")  # lowercased
		self.assertEqual(rule["labels"]["team"], "ops")

	def test_get_rule_merges_description_into_annotations(self):
		doc = self._make_doc(description="My description", annotations='{"summary": "x"}')
		rule = PrometheusAlertRule.get_rule(doc)
		self.assertEqual(rule["annotations"]["description"], "My description")
		self.assertEqual(rule["annotations"]["summary"], "x")

	def test_get_route_includes_alertname_matcher(self):
		doc = self._make_doc(name="MyAlert")
		route = PrometheusAlertRule.get_route(doc)
		self.assertIn('alertname="MyAlert"', route["matchers"])

	def test_get_route_includes_intervals(self):
		doc = self._make_doc(group_wait="1m", group_interval="5m", repeat_interval="2h")
		route = PrometheusAlertRule.get_route(doc)
		self.assertEqual(route["group_wait"], "1m")
		self.assertEqual(route["group_interval"], "5m")
		self.assertEqual(route["repeat_interval"], "2h")

	def test_validate_raises_when_enabled_without_expression(self):
		"""validate() raises ValidationError when enabled=True but expression is empty."""
		import frappe

		doc = self._make_doc(enabled=1, expression="")
		with (
			patch(f"{self._MODULE}.yaml.dump", return_value=""),
			self.assertRaises(frappe.ValidationError),
		):
			PrometheusAlertRule.validate(doc)

	def test_validate_passes_when_disabled_without_expression(self):
		"""validate() does not raise when rule is disabled even if expression is empty."""
		doc = self._make_doc(enabled=0, expression="")
		with patch(f"{self._MODULE}.yaml.dump", return_value=""):
			PrometheusAlertRule.validate(doc)  # must not raise
