# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.press_job.press_job import PressJob
from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import PrometheusAlertRule
from press.press.doctype.server.test_server import create_test_server


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
	pass


def create_disk_warning_log(server: str, mountpoint: str = "/"):
	return frappe.get_doc(
		{"doctype": "Add On Storage Log", "server": server, "mountpoint": mountpoint, "is_warning": True}
	).insert(ignore_permissions=True)


@patch.object(PressJob, "after_insert", new=Mock())
class TestIncreaseDiskSizeReaction(FrappeTestCase):
	def react(self, server: str, mountpoint: str = "/"):
		rule = create_test_prometheus_alert_rule()
		return rule.run_press_job("Increase Disk Size", "Server", server, labels={"mountpoint": mountpoint})

	def test_skips_job_when_auto_increase_disabled_and_team_already_warned(self):
		server = create_test_server(auto_increase_storage=False)
		create_disk_warning_log(server.name)

		self.assertIsNone(self.react(server.name))
		self.assertFalse(frappe.db.exists("Press Job", {"server": server.name}))

	def test_creates_job_to_warn_when_auto_increase_disabled_and_no_recent_warning(self):
		server = create_test_server(auto_increase_storage=False)

		job = self.react(server.name)
		self.assertEqual(job.job_type, "Increase Disk Size")

	def test_warning_on_one_mountpoint_does_not_suppress_another(self):
		server = create_test_server(auto_increase_storage=False)
		create_disk_warning_log(server.name, mountpoint="/opt/volumes/benches")

		job = self.react(server.name, mountpoint="/opt/volumes/mariadb")
		self.assertEqual(job.job_type, "Increase Disk Size")

	def test_creates_job_when_auto_increase_enabled(self):
		server = create_test_server(auto_increase_storage=True)
		create_disk_warning_log(server.name)

		job = self.react(server.name)
		self.assertEqual(job.job_type, "Increase Disk Size")
