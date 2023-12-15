# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch
import frappe
import unittest


from press.agent import Agent


@patch.object(Agent, "update_monitor_rules", new=Mock())
def create_test_prometheus_alert_rule():
	return frappe.get_doc(
		{
			"doctype": "Prometheus Alert Rule",
			"name": "Sites Down",
			"description": "Sites didn't respond with http 200",
			"severity": "Critical",
			"group_wait": "1m",
			"group_interval": "1m",
			"repeat_interval": "1h",
			"group_by": '["alertname", "cluster", "server", "instance"]',
			"expression": 'probe_success{job="site"} == 0 and probe_http_status_code != 429',
			"for": "4m",
		},
	).insert(ignore_if_duplicate=True)


class TestPrometheusAlertRule(unittest.TestCase):
	pass
