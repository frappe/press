# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

import frappe
import yaml
from frappe.core.utils import find
from frappe.model.document import Document

from press.agent import Agent

if TYPE_CHECKING:
	from press.press.doctype.press_job.press_job import PressJob
	from press.press.doctype.server.server import Server


class PrometheusAlertRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.prometheus_alert_rule_cluster.prometheus_alert_rule_cluster import (
			PrometheusAlertRuleCluster,
		)

		alert_preview: DF.Code | None
		annotations: DF.JSON
		description: DF.Data
		enabled: DF.Check
		expression: DF.Code | None
		group_by: DF.Code
		group_interval: DF.Data
		group_wait: DF.Data
		ignore_on_clusters: DF.TableMultiSelect[PrometheusAlertRuleCluster]
		labels: DF.JSON
		only_on_shared: DF.Check
		press_job_type: DF.Link | None
		repeat_interval: DF.Data
		route_preview: DF.Code | None
		severity: DF.Literal["Critical", "Warning", "Information"]
		silent: DF.Check
	# end: auto-generated types

	def validate(self):
		self.alert_preview = yaml.dump(self.get_rule())
		self.route_preview = yaml.dump(self.get_route())
		if self.enabled and not self.expression:
			frappe.throw("Enabled alert rules require an expression")

	def on_update(self):
		PrometheusAlertRule.update_alert_rules_on_monitor()

	def get_rule(self):
		labels = json.loads(self.labels)
		labels.update({"severity": self.severity.lower()})

		annotations = json.loads(self.annotations)
		annotations.update({"description": self.description})

		return {
			"alert": self.name,
			"expr": self.expression,
			"for": self.get("for"),
			"labels": labels,
			"annotations": annotations,
		}

	def get_route(self) -> dict[str, list[Any] | dict[Any, Any]]:
		return {
			"group_by": json.loads(self.group_by),
			"group_wait": self.group_wait,
			"group_interval": self.group_interval,
			"repeat_interval": self.repeat_interval,
			"matchers": [f'alertname="{self.name}"'],
		}

	def react(self, instance_type: str, instance: str, labels: dict | None = None) -> PressJob | None:
		assert self.press_job_type is not None
		return self.run_press_job(self.press_job_type, instance_type, instance, labels)

	def run_press_job(
		self, job_name: str, server_type: str, server_name: str, labels: dict | None = None, arguments=None
	) -> PressJob | None:
		server: "Server" = frappe.get_doc(server_type, server_name)
		if self.only_on_shared and not server.public:
			return None
		if find(self.ignore_on_clusters, lambda x: x.cluster == server.cluster):
			return None

		if arguments is None:
			arguments = {}

		if not labels:
			labels = {}

		arguments.update({"labels": labels})

		if existing_jobs := frappe.get_all(
			"Press Job",
			{
				"status": ("in", ["Pending", "Running"]),
				"server_type": server_type,
				"server": server_name,
			},
			pluck="name",
		):
			return frappe.get_doc("Press Job", existing_jobs[0])

		return frappe.get_doc(
			{
				"doctype": "Press Job",
				"job_type": job_name,
				"server_type": server_type,
				"server": server_name,
				"virtual_machine": server.virtual_machine,
				"arguments": json.dumps(arguments, indent=2, sort_keys=True),
			}
		).insert()

	@staticmethod
	def get_rules() -> dict[str, list | dict]:
		rules_dict: dict[str, list[Any] | dict[Any, Any]] = {"groups": [{"name": "All", "rules": []}]}

		rules = frappe.get_all("Prometheus Alert Rule", {"enabled": True})
		for rule in rules:
			rule_doc = frappe.get_doc("Prometheus Alert Rule", rule.name)
			cast("list", cast("dict", rules_dict["groups"][0])["rules"]).append(rule_doc.get_rule())

		return rules_dict

	@staticmethod
	def get_routes() -> dict[str, list[Any] | dict[Any, Any]]:
		webhook_token = frappe.db.get_value(
			"Monitor Server", frappe.db.get_single_value("Press Settings", "monitor_server"), "webhook_token"
		)

		callback_route = "api/method/press.api.monitoring.alert"
		if press_url := frappe.conf.get("press_url"):
			press_url = press_url.rstrip("/") + "/"
			callback_url = frappe.utils.get_url(f"{press_url}{callback_route}")
		else:
			callback_url = frappe.utils.get_url(callback_route)

		if webhook_token:
			callback_url = f"{callback_url}?webhook_token={webhook_token}"

		routes_dict: dict[str, list[Any] | dict[Any, Any]] = {
			"route": {"receiver": "web.hook", "routes": []},
			"receivers": [
				{
					"name": "web.hook",
					"webhook_configs": [{"url": callback_url}],
				}
			],
		}

		rules = frappe.get_all("Prometheus Alert Rule", {"enabled": True})
		for rule in rules:
			rule_doc = frappe.get_doc("Prometheus Alert Rule", rule.name)
			cast("list", cast("dict", routes_dict["route"])["routes"]).append(rule_doc.get_route())

		return routes_dict

	@staticmethod
	def update_alert_rules_on_monitor(monitoring_server: str | None = None):
		if not monitoring_server:
			monitoring_server = frappe.db.get_single_value("Press Settings", "monitor_server")

		rules = yaml.dump(PrometheusAlertRule.get_rules())
		routes = yaml.dump(PrometheusAlertRule.get_routes())

		agent = Agent(monitoring_server, "Monitor Server")
		agent.update_monitor_rules(rules, routes)
