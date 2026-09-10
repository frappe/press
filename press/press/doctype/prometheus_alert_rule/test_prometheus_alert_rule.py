# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import re
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import (
	PrometheusAlertRule,
	storage_alert_rule_name,
)
from press.press.doctype.server.server import DEFAULT_STORAGE_ALERT_THRESHOLD
from press.press.doctype.server.test_server import create_test_server

DISK_EXPRESSION = (
	'100 - (node_filesystem_avail_bytes{job="node", {{ instances }}}'
	' / node_filesystem_size_bytes{job="node", {{ instances }}} * 100) > {{ threshold }}'
)


@patch.object(Agent, "update_monitor_rules", new=Mock())
def create_test_prometheus_alert_rule(
	name="Sites Down",
	expression='probe_success{job="site"} == 0 and probe_http_status_code != 429',
	enabled=False,
	split_by_server_storage_threshold=False,
) -> PrometheusAlertRule:
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
			"expression": expression,
			"for": "4m",
			"enable_reactions": True,
			"enabled": enabled,
			"split_by_server_storage_threshold": split_by_server_storage_threshold,
		},
	).insert(ignore_if_duplicate=True)


@patch.object(Agent, "update_monitor_rules", new=Mock())
class TestPrometheusAlertRule(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def create_server_with_threshold(self, rule: PrometheusAlertRule, threshold: int):
		"""A server on a custom threshold, with the rule sync the doc event would have enqueued."""
		server = create_test_server()
		server.storage_alert_threshold_percent = threshold
		server.save()
		rule.sync_and_push_storage_alert_rules()
		return server

	def create_disk_alert_rule(self) -> PrometheusAlertRule:
		return create_test_prometheus_alert_rule(
			name="Disk Space Low",
			expression=DISK_EXPRESSION,
			enabled=True,
			split_by_server_storage_threshold=True,
		)

	def test_split_rule_without_the_threshold_placeholder_is_rejected(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			r"needs \{\{ threshold \}\} in the expression",
			create_test_prometheus_alert_rule,
			name="Disk Space Low",
			expression=DISK_EXPRESSION.replace(" > {{ threshold }}", " > 90"),
			split_by_server_storage_threshold=True,
		)

	def test_split_rule_without_the_instances_placeholder_is_rejected(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			r"needs \{\{ instances \}\} in the expression",
			create_test_prometheus_alert_rule,
			name="Disk Space Low",
			expression=DISK_EXPRESSION.replace("{{ instances }}", 'mountpoint="/"'),
			split_by_server_storage_threshold=True,
		)

	def test_a_rule_that_does_not_split_needs_no_placeholders(self):
		rule = create_test_prometheus_alert_rule()

		self.assertEqual(rule.get_alert_rules()[0]["expr"], rule.expression)

	def test_expression_is_left_alone_when_splitting_is_disabled(self):
		rule = create_test_prometheus_alert_rule(expression=DISK_EXPRESSION)

		alert_rules = rule.get_alert_rules()

		self.assertEqual(len(alert_rules), 1)
		self.assertEqual(alert_rules[0]["expr"], DISK_EXPRESSION)

	def test_every_instance_alerts_at_the_default_threshold_when_no_server_overrides_it(self):
		rule = self.create_disk_alert_rule()

		alert_rules = rule.get_alert_rules()

		self.assertEqual(len(alert_rules), 1)
		self.assertIn('instance!=""', alert_rules[0]["expr"])
		self.assertTrue(alert_rules[0]["expr"].endswith("> 90"))

	def test_server_with_custom_threshold_gets_a_rule_document_of_its_own(self):
		rule = self.create_disk_alert_rule()
		server = self.create_server_with_threshold(rule, 75)

		own_rule = frappe.get_doc("Prometheus Alert Rule", storage_alert_rule_name(rule.name, server.name))

		self.assertIn(f'instance=~"{re.escape(server.name)}"', own_rule.expression)
		self.assertTrue(own_rule.expression.endswith("> 75"))

	def test_server_with_a_rule_of_its_own_is_excluded_from_the_shared_rule(self):
		rule = self.create_disk_alert_rule()
		server = self.create_server_with_threshold(rule, 75)

		alert_rules = rule.get_alert_rules()

		self.assertEqual(len(alert_rules), 1)
		self.assertIn(f'instance!~"{re.escape(server.name)}"', alert_rules[0]["expr"])
		self.assertTrue(alert_rules[0]["expr"].endswith("> 90"))

	def test_servers_sharing_a_threshold_still_get_one_rule_each(self):
		rule = self.create_disk_alert_rule()
		servers = [self.create_server_with_threshold(rule, 80) for _ in range(2)]

		for server in servers:
			own_rule = frappe.get_doc(
				"Prometheus Alert Rule", storage_alert_rule_name(rule.name, server.name)
			)
			self.assertIn(f'instance=~"{re.escape(server.name)}"', own_rule.expression)
			self.assertTrue(own_rule.expression.endswith("> 80"))

	def test_per_server_rule_inherits_the_reaction_of_the_shared_rule(self):
		rule = self.create_disk_alert_rule()
		server = self.create_server_with_threshold(rule, 70)

		own_rule = frappe.get_doc("Prometheus Alert Rule", storage_alert_rule_name(rule.name, server.name))

		self.assertEqual(own_rule.press_job_type, rule.press_job_type)
		self.assertEqual(own_rule.severity, rule.severity)
		self.assertEqual(own_rule.get("for"), rule.get("for"))
		self.assertTrue(own_rule.enabled)

	def test_per_server_rule_does_not_split_itself_again(self):
		rule = self.create_disk_alert_rule()
		server = self.create_server_with_threshold(rule, 70)

		own_rule = frappe.get_doc("Prometheus Alert Rule", storage_alert_rule_name(rule.name, server.name))

		self.assertFalse(own_rule.split_by_server_storage_threshold)
		self.assertEqual(own_rule.get_alert_rules()[0]["expr"], own_rule.expression)

	def test_per_server_rule_is_deleted_when_the_server_returns_to_the_default(self):
		rule = self.create_disk_alert_rule()
		server = self.create_server_with_threshold(rule, 70)
		name = storage_alert_rule_name(rule.name, server.name)
		self.assertTrue(frappe.db.exists("Prometheus Alert Rule", name))

		server.storage_alert_threshold_percent = DEFAULT_STORAGE_ALERT_THRESHOLD
		server.save()
		rule.sync_and_push_storage_alert_rules()

		self.assertFalse(frappe.db.exists("Prometheus Alert Rule", name))
		self.assertNotIn(server.name, rule.get_alert_rules()[0]["expr"])

	def test_per_server_rule_follows_a_later_threshold_change(self):
		rule = self.create_disk_alert_rule()
		server = self.create_server_with_threshold(rule, 70)

		server.storage_alert_threshold_percent = 85
		server.save()
		rule.sync_and_push_storage_alert_rules()

		own_rule = frappe.get_doc("Prometheus Alert Rule", storage_alert_rule_name(rule.name, server.name))
		self.assertTrue(own_rule.expression.endswith("> 85"))

	def test_server_holding_a_threshold_outside_the_range_stays_on_the_default_rule(self):
		rule = self.create_disk_alert_rule()
		server = create_test_server()
		# set_value skips validation, the way a stale row or a bad script would
		frappe.db.set_value("Server", server.name, "storage_alert_threshold_percent", 0)

		alert_rules = rule.get_alert_rules()

		self.assertEqual(len(alert_rules), 1)
		self.assertTrue(alert_rules[0]["expr"].endswith("> 90"))
		self.assertNotIn(server.name, alert_rules[0]["expr"])

	def test_alert_name_of_a_per_server_rule_is_the_document_that_reacts_to_it(self):
		"""react_for_instance looks the firing alertname up as a Prometheus Alert Rule."""
		rule = self.create_disk_alert_rule()
		server = self.create_server_with_threshold(rule, 70)
		name = storage_alert_rule_name(rule.name, server.name)

		own_rule = frappe.get_doc("Prometheus Alert Rule", name)

		self.assertEqual(own_rule.get_alert_rules()[0]["alert"], name)

	def test_changing_a_server_threshold_pushes_rules_to_the_monitor_server(self):
		rule = self.create_disk_alert_rule()
		server = create_test_server()

		with patch.object(frappe, "enqueue_doc") as enqueue_doc:
			server.storage_alert_threshold_percent = 85
			server.save()

		pushed_rules = [
			call
			for call in enqueue_doc.call_args_list
			if call.args[:3] == ("Prometheus Alert Rule", rule.name, "sync_and_push_storage_alert_rules")
		]
		self.assertEqual(len(pushed_rules), 1)

	def test_saving_a_server_without_touching_the_threshold_does_not_push_rules(self):
		rule = self.create_disk_alert_rule()
		server = create_test_server()

		with patch.object(frappe, "enqueue_doc") as enqueue_doc:
			server.title = "Renamed Server"
			server.save()

		pushed_rules = [
			call
			for call in enqueue_doc.call_args_list
			if call.args[:2] == ("Prometheus Alert Rule", rule.name)
		]
		self.assertEqual(pushed_rules, [])
