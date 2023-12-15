# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from datetime import datetime
import json
import frappe
import unittest
import typing

from press.press.doctype.prometheus_alert_rule.test_prometheus_alert_rule import (
	create_test_prometheus_alert_rule,
)
from press.press.doctype.site.test_site import create_test_site

if typing.TYPE_CHECKING:
	from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import (
		PrometheusAlertRule,
	)
	from press.press.doctype.site.site import Site


def create_test_alertmanager_webhook_log(
	alert: "PrometheusAlertRule" = None, creation: datetime = None, site: "Site" = None
):
	alert = alert or create_test_prometheus_alert_rule()
	site = site or create_test_site()
	return frappe.get_doc(
		{
			"doctype": "Alertmanager Webhook Log",
			"alert": alert.name,
			"creation": creation or datetime.now(),
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
								"instance": site.name,
								"job": "site",
								"server": site.server,
								"severity": alert.severity.lower(),
							},
							"startsAt": "2023-12-15T01:02:56.363Z",
							"status": "firing",
						}
					],
					"commonAnnotations": {
						"description": alert.description,
					},
					"commonLabels": {
						"alertname": alert.name,
						"severity": alert.severity.lower(),
						"status": "firing",
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
					"status": "firing",
					"truncatedAlerts": 0,
					"version": "4",
					"externalURL": "http://localhost:9093",
				}
			),
		},
	).insert()


class TestAlertmanagerWebhookLog(unittest.TestCase):
	pass
