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
FIELDS_COPIED_TO_PER_SERVER_RULE = (
	"severity",
	"for",
	"group_by",
	"group_wait",
	"group_interval",
	"repeat_interval",
	"labels",
	"annotations",
	"press_job_type",
	"only_on_shared",
	"silent",
	"enabled",
)


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
		"""The shared rule, minus the servers that carry a rule of their own."""
		if not self.split_by_server_storage_threshold:
			return [self.get_rule()]

		overriding_servers = list(servers_by_storage_alert_threshold())
		return [
			self.get_rule_for_threshold(DEFAULT_STORAGE_ALERT_THRESHOLD, overriding_servers, exclude=True)
		]

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
		if frappe.flags.syncing_storage_alert_rules:
			# the base rule pushes once for the whole sync
			return

		if self.split_by_server_storage_threshold:
			sync_storage_alert_rules(self)

		self.push_rules_to_monitor_server()

	def sync_and_push_storage_alert_rules(self):
		sync_storage_alert_rules(self)
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


def servers_by_storage_alert_threshold() -> dict[str, int]:
	"""Active servers that alert at something other than the default threshold, and the level each picked."""
	overrides: dict[str, int] = {}
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
			overrides[server.name] = threshold
	return overrides


def instance_matcher(servers: list[str], exclude: bool) -> str:
	"""PromQL matcher selecting these instances, or every instance but these."""
	if not servers:
		return 'instance!=""'

	pattern = "|".join(re.escape(server) for server in servers)
	return f'instance!~"{pattern}"' if exclude else f'instance=~"{pattern}"'


def base_storage_alert_rule() -> str | None:
	return frappe.db.get_value(
		"Prometheus Alert Rule", {"split_by_server_storage_threshold": 1, "enabled": 1}
	)


def storage_alert_rule_name(base_rule: str, server: str) -> str:
	return f"{base_rule} - {server}"


def sync_storage_alert_rules(base_rule: PrometheusAlertRule):
	"""Give every overriding server a rule of its own, and drop the ones no longer needed."""
	overrides = servers_by_storage_alert_threshold()

	frappe.flags.syncing_storage_alert_rules = True
	try:
		for server, threshold in overrides.items():
			upsert_storage_alert_rule(base_rule, server, threshold)
		delete_stale_storage_alert_rules(base_rule, set(overrides))
	finally:
		frappe.flags.syncing_storage_alert_rules = False


def upsert_storage_alert_rule(base_rule: PrometheusAlertRule, server: str, threshold: int):
	name = storage_alert_rule_name(base_rule.name, server)
	values = storage_alert_rule_values(base_rule, server, threshold)

	if frappe.db.exists("Prometheus Alert Rule", name):
		rule: PrometheusAlertRule = frappe.get_doc("Prometheus Alert Rule", name)
		rule.update(values)
		rule.save()
		return

	frappe.get_doc({"doctype": "Prometheus Alert Rule", "name": name, **values}).insert()


def storage_alert_rule_values(base_rule: PrometheusAlertRule, server: str, threshold: int) -> dict:
	"""Everything the per-server rule inherits, with its own threshold baked into the expression."""
	values = {field: base_rule.get(field) for field in FIELDS_COPIED_TO_PER_SERVER_RULE}
	values.update(
		{
			"description": f"{base_rule.description} ({server} alerts at {threshold}%)",
			"expression": base_rule.get_rule_for_threshold(threshold, [server], exclude=False)["expr"],
			# the per-server rule is the split, splitting it again would exclude the server from itself
			"split_by_server_storage_threshold": 0,
		}
	)
	return values


def delete_stale_storage_alert_rules(base_rule: PrometheusAlertRule, overriding_servers: set[str]):
	"""Drop the rules of servers that went back to the default, or were archived."""
	prefix = storage_alert_rule_name(base_rule.name, "")
	for name in frappe.get_all("Prometheus Alert Rule", {"name": ("like", f"{prefix}%")}, pluck="name"):
		if name[len(prefix) :] not in overriding_servers:
			frappe.delete_doc("Prometheus Alert Rule", name)


def update_rules_on_storage_alert_threshold_change(server, method=None):
	"""Rebuild the per-server rules so the server starts alerting at its new threshold."""
	previous = server.get_doc_before_save()
	previous_threshold = (
		previous.storage_alert_threshold_percent if previous else DEFAULT_STORAGE_ALERT_THRESHOLD
	)
	if previous_threshold == server.storage_alert_threshold_percent:
		return

	rule = base_storage_alert_rule()
	if not rule:
		return

	frappe.enqueue_doc(
		"Prometheus Alert Rule",
		rule,
		"sync_and_push_storage_alert_rules",
		enqueue_after_commit=True,
		job_id="push_storage_alert_rules",
		deduplicate=True,
	)
