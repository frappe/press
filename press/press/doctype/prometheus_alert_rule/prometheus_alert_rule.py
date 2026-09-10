# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import frappe
import yaml
from frappe.core.utils import find
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.server.server import (
	DEFAULT_STORAGE_ALERT_THRESHOLD,
	MAX_STORAGE_ALERT_THRESHOLD,
	MIN_STORAGE_ALERT_THRESHOLD,
)

if TYPE_CHECKING:
	from press.press.doctype.server.server import Server

THRESHOLD_PLACEHOLDER = "{{ threshold }}"
INSTANCES_PLACEHOLDER = "{{ instances }}"
SERVER_TYPES_WITH_STORAGE_ALERT_THRESHOLD = ("Server", "Database Server")


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
		annotations: DF.Code
		description: DF.Data
		enabled: DF.Check
		expression: DF.Code | None
		group_by: DF.Code
		group_interval: DF.Data
		group_wait: DF.Data
		ignore_on_clusters: DF.TableMultiSelect[PrometheusAlertRuleCluster]
		labels: DF.Code
		only_on_shared: DF.Check
		press_job_type: DF.Link | None
		repeat_interval: DF.Data
		route_preview: DF.Code | None
		severity: DF.Literal["Critical", "Warning", "Information"]
		silent: DF.Check
		split_by_server_storage_threshold: DF.Check
	# end: auto-generated types

	def validate(self):
		if self.enabled and not self.expression:
			frappe.throw("Please add an expression for this alert rule before enabling it.")

		self.validate_split_placeholders()
		self.alert_preview = yaml.dump(self.get_alert_rules())
		self.route_preview = yaml.dump(self.get_route())

	def validate_split_placeholders(self):
		"""Without both placeholders a split rule repeats one hardcoded threshold, alerting twice."""
		if not self.split_by_server_storage_threshold:
			return

		missing = [
			placeholder
			for placeholder in (THRESHOLD_PLACEHOLDER, INSTANCES_PLACEHOLDER)
			if placeholder not in (self.expression or "")
		]
		if missing:
			frappe.throw(
				f"Splitting by storage alert threshold needs {' and '.join(missing)} in the expression."
			)

	def get_alert_rules(self) -> list[dict]:
		"""One rule per storage alert threshold, so each server alerts at the level its team picked."""
		if not self.split_by_server_storage_threshold:
			return [self.get_rule()]

		overrides = servers_by_storage_alert_threshold()
		overridden_servers = [server for servers in overrides.values() for server in servers]

		rules = [self.get_rule_for_threshold(DEFAULT_STORAGE_ALERT_THRESHOLD, overridden_servers, True)]
		rules.extend(
			self.get_rule_for_threshold(threshold, servers, False) for threshold, servers in overrides.items()
		)
		return rules

	def get_rule_for_threshold(self, threshold: int, servers: list[str], exclude: bool) -> dict:
		rule = self.get_rule()
		expression: str = self.expression or ""
		rule["expr"] = (
			expression.replace(THRESHOLD_PLACEHOLDER, str(threshold))
			.replace(INSTANCES_PLACEHOLDER, instance_matcher(servers, exclude))
			.strip()
		)
		return rule

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

	def get_route(self):
		return {
			"group_by": json.loads(self.group_by),
			"group_wait": self.group_wait,
			"group_interval": self.group_interval,
			"repeat_interval": self.repeat_interval,
			"matchers": [f'alertname="{self.name}"'],
		}

	def on_update(self):
		self.push_rules_to_monitor_server()

	def push_rules_to_monitor_server(self):
		rules = yaml.dump(self.get_rules())
		routes = yaml.dump(self.get_routes())

		monitoring_server = frappe.db.get_single_value("Press Settings", "monitor_server")
		agent = Agent(monitoring_server, "Monitor Server")
		agent.update_monitor_rules(rules, routes)

	def get_rules(self):
		rules_dict = {"groups": [{"name": "All", "rules": []}]}

		rules = frappe.get_all(self.doctype, {"enabled": True})
		for rule in rules:
			rule_doc = frappe.get_doc(self.doctype, rule.name)
			rules_dict["groups"][0]["rules"].extend(rule_doc.get_alert_rules())

		return rules_dict

	def get_routes(self):
		webhook_token = frappe.db.get_value(
			"Monitor Server", frappe.db.get_single_value("Press Settings", "monitor_server"), "webhook_token"
		)

		callback_url = frappe.utils.get_url("api/method/press.api.monitoring.alert")
		if webhook_token:
			callback_url = f"{callback_url}?webhook_token={webhook_token}"

		routes_dict = {
			"route": {"receiver": "web.hook", "routes": []},
			"receivers": [
				{
					"name": "web.hook",
					"webhook_configs": [{"url": callback_url}],
				}
			],
		}

		rules = frappe.get_all(self.doctype, {"enabled": True})
		for rule in rules:
			rule_doc = frappe.get_doc(self.doctype, rule.name)
			routes_dict["route"]["routes"].append(rule_doc.get_route())

		return routes_dict

	def react(self, instance_type: str, instance: str, labels: dict | None = None):
		return self.run_press_job(self.press_job_type, instance_type, instance, labels)  # type: ignore[arg-type]

	def run_press_job(
		self, job_name: str, server_type: str, server_name: str, labels: dict | None = None, arguments=None
	):
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


def servers_by_storage_alert_threshold() -> dict[int, list[str]]:
	"""Active servers that alert at something other than the default threshold, grouped by threshold."""
	overrides: dict[int, list[str]] = {}
	for doctype in SERVER_TYPES_WITH_STORAGE_ALERT_THRESHOLD:
		servers = frappe.get_all(
			doctype,
			{
				"status": "Active",
				"storage_alert_threshold_percent": ("!=", DEFAULT_STORAGE_ALERT_THRESHOLD),
			},
			["name", "storage_alert_threshold_percent"],
		)
		for server in servers:
			threshold = server.storage_alert_threshold_percent
			if not MIN_STORAGE_ALERT_THRESHOLD <= threshold <= MAX_STORAGE_ALERT_THRESHOLD:
				# never went through validation, so leave it on the default rule
				# instead of alerting the server at, say, 0%
				continue
			overrides.setdefault(threshold, []).append(server.name)
	return overrides


def instance_matcher(servers: list[str], exclude: bool) -> str:
	"""PromQL matcher selecting these instances, or every instance but these."""
	if not servers:
		return 'instance!=""'

	pattern = "|".join(re.escape(server) for server in servers)
	return f'instance!~"{pattern}"' if exclude else f'instance=~"{pattern}"'


def update_rules_on_storage_alert_threshold_change(server, method=None):
	"""Rebuild the split rules so the server starts alerting at its new threshold."""
	previous = server.get_doc_before_save()
	previous_threshold = (
		previous.storage_alert_threshold_percent if previous else DEFAULT_STORAGE_ALERT_THRESHOLD
	)
	if previous_threshold == server.storage_alert_threshold_percent:
		return

	# Any split rule will do, pushing one rebuilds the rules of every enabled alert
	rule = frappe.db.get_value(
		"Prometheus Alert Rule", {"split_by_server_storage_threshold": 1, "enabled": 1}
	)
	if not rule:
		return

	frappe.enqueue_doc(
		"Prometheus Alert Rule",
		rule,
		"push_rules_to_monitor_server",
		enqueue_after_commit=True,
		job_id="push_storage_alert_rules",
		deduplicate=True,
	)
