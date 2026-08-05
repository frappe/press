# Copyright (c) 2021, Frappe and Contributors
# See license.txt
from __future__ import annotations

import json
import typing

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import add_to_date

from press.api.client import get
from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import (
	DISK_FULL_ALERT,
	DISK_FULL_ALERT_WINDOW_HOURS,
	disk_full_servers,
)
from press.press.doctype.prometheus_alert_rule.test_prometheus_alert_rule import (
	create_test_prometheus_alert_rule,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_site

if typing.TYPE_CHECKING:
	from datetime import datetime

	from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import AlertmanagerWebhookLog
	from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import (
		PrometheusAlertRule,
	)
	from press.press.doctype.site.site import Site


def create_test_alertmanager_webhook_log(
	alert: PrometheusAlertRule | None = None,
	creation: datetime | None = None,
	site: Site | None = None,
	status: str = "firing",
	instance: str | None = None,
) -> AlertmanagerWebhookLog:
	alert = alert or create_test_prometheus_alert_rule()
	site = site or create_test_site()
	instance = instance or site.name
	return frappe.get_doc(  # type: ignore
		{
			"doctype": "Alertmanager Webhook Log",
			"alert": alert.name,
			"creation": creation or frappe.utils.now_datetime(),
			"payload": json.dumps(
				{
					"alerts": [
						{
							"annotations": {
								"description": alert.description,
							},
							"endsAt": "0001-01-01T00:00:00Z",
							"fingerprint": "343699f90f81ee7b",
							"labels": {
								"alertname": alert.name,
								"bench": site.bench,
								"cluster": site.cluster,
								"group": "bench-0001",
								"instance": instance,
								"job": "site",
								"server": site.server,
								"severity": alert.severity.lower(),
							},
							"startsAt": "2023-12-15T01:02:56.363Z",
							"status": status,
						}
					],
					"commonAnnotations": {
						"description": alert.description,
					},
					"commonLabels": {
						"alertname": alert.name,
						"severity": alert.severity.lower(),
						"status": status,
						"bench": site.bench,
						"cluster": site.cluster,
						"job": "site",
						"server": site.server,
					},
					"groupKey": f'{{}}/{{alertname="{alert.name}"}}:{{alertname="{alert.name}", bench="{site.bench}", cluster="{site.cluster}", server="{site.server}"}}',
					"groupLabels": {
						"alertname": alert.name,
						"bench": site.bench,
						"cluster": site.cluster,
						"server": site.server,
					},
					"receiver": "web\\.hook",
					"status": status.capitalize(),
					"truncatedAlerts": 0,
					"version": "4",
					"externalURL": "http://localhost:9093",
				}
			),
		},
	).insert()


class TestDiskFullServers(FrappeTestCase):
	def setUp(self):
		self.rule = create_test_prometheus_alert_rule(name=DISK_FULL_ALERT)
		self.server = create_test_server()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def disk_full_alert(self, instance: str, status: str) -> AlertmanagerWebhookLog:
		return create_test_alertmanager_webhook_log(alert=self.rule, instance=instance, status=status)

	def test_alert_on_app_server_reports_that_server(self):
		self.disk_full_alert(self.server.name, "firing")
		self.assertEqual(disk_full_servers(), {self.server.name})

	def test_alert_on_database_server_reports_the_app_server_it_serves(self):
		self.disk_full_alert(self.server.database_server, "firing")
		self.assertEqual(disk_full_servers(), {self.server.name})

	def test_resolved_alert_stops_reporting_the_server(self):
		self.disk_full_alert(self.server.name, "firing")
		self.disk_full_alert(self.server.name, "resolved")
		self.assertEqual(disk_full_servers(), set())

	def test_resolved_alert_keeps_reporting_the_servers_still_out_of_space(self):
		other_server = create_test_server()
		self.disk_full_alert(self.server.name, "firing")
		self.disk_full_alert(other_server.name, "firing")

		self.disk_full_alert(self.server.name, "resolved")

		self.assertEqual(disk_full_servers(), {other_server.name})

	def test_unified_server_is_reported_once(self):
		frappe.db.set_value(
			"Server", self.server.name, {"database_server": self.server.name, "is_unified_server": 1}
		)

		self.disk_full_alert(self.server.name, "firing")

		self.assertEqual(disk_full_servers(), {self.server.name})

	def test_alert_we_have_not_heard_about_for_a_while_is_ignored(self):
		log = self.disk_full_alert(self.server.name, "firing")
		frappe.db.set_value(
			log.doctype,
			log.name,
			"creation",
			add_to_date(frappe.utils.now(), hours=-(DISK_FULL_ALERT_WINDOW_HOURS + 1)),
			update_modified=False,
		)

		self.assertEqual(disk_full_servers(), set())

	def test_alert_on_an_unknown_instance_is_ignored(self):
		self.disk_full_alert("some-server-we-do-not-own.frappe.cloud", "firing")
		self.assertEqual(disk_full_servers(), set())

	def test_site_dashboard_on_a_dedicated_server_is_told_the_disk_is_full(self):
		site = create_test_site(server=self.server.name)
		self.disk_full_alert(self.server.name, "firing")

		frappe.set_user(frappe.db.get_value("Team", site.team, "user"))

		self.assertTrue(get("Site", site.name).is_server_disk_full)

	def test_site_dashboard_on_shared_hosting_is_not_told_the_disk_is_full(self):
		shared_server = create_test_server(public=True)
		site = create_test_site(server=shared_server.name)
		self.disk_full_alert(shared_server.name, "firing")

		frappe.set_user(frappe.db.get_value("Team", site.team, "user"))

		self.assertFalse(get("Site", site.name).is_server_disk_full)
