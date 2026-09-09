# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import re
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import PrometheusAlertRule
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

	def test_server_with_custom_threshold_gets_its_own_rule_and_is_excluded_from_the_default_one(self):
		rule = self.create_disk_alert_rule()
		server = create_test_server()
		server.storage_alert_threshold_percent = 75
		server.save()

		default_rule, custom_rule = rule.get_alert_rules()

		self.assertIn(f'instance!~"{re.escape(server.name)}"', default_rule["expr"])
		self.assertTrue(default_rule["expr"].endswith("> 90"))
		self.assertIn(f'instance=~"{re.escape(server.name)}"', custom_rule["expr"])
		self.assertTrue(custom_rule["expr"].endswith("> 75"))

	def test_servers_sharing_a_threshold_share_one_rule(self):
		rule = self.create_disk_alert_rule()
		servers = []
		for _ in range(2):
			server = create_test_server()
			server.storage_alert_threshold_percent = 80
			server.save()
			servers.append(server)

		alert_rules = rule.get_alert_rules()

		self.assertEqual(len(alert_rules), 2)
		for server in servers:
			self.assertIn(re.escape(server.name), alert_rules[1]["expr"])

	def test_server_holding_a_threshold_outside_the_range_stays_on_the_default_rule(self):
		rule = self.create_disk_alert_rule()
		server = create_test_server()
		# set_value skips validation, the way a stale row or a bad script would
		frappe.db.set_value("Server", server.name, "storage_alert_threshold_percent", 0)

		alert_rules = rule.get_alert_rules()

		self.assertEqual(len(alert_rules), 1)
		self.assertTrue(alert_rules[0]["expr"].endswith("> 90"))
		self.assertNotIn(server.name, alert_rules[0]["expr"])

	def test_alert_name_stays_the_same_across_split_rules(self):
		rule = self.create_disk_alert_rule()
		server = create_test_server()
		server.storage_alert_threshold_percent = 70
		server.save()

		self.assertEqual([alert_rule["alert"] for alert_rule in rule.get_alert_rules()], [rule.name] * 2)

	def test_changing_a_server_threshold_pushes_rules_to_the_monitor_server(self):
		rule = self.create_disk_alert_rule()
		server = create_test_server()

		with patch.object(frappe, "enqueue_doc") as enqueue_doc:
			server.storage_alert_threshold_percent = 85
			server.save()

		pushed_rules = [
			call
			for call in enqueue_doc.call_args_list
			if call.args[:3] == ("Prometheus Alert Rule", rule.name, "push_rules_to_monitor_server")
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
