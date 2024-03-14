# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import yaml
import json
from frappe.model.document import Document
from press.agent import Agent


class PrometheusAlertRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		alert_preview: DF.Code | None
		annotations: DF.Code
		description: DF.Data
		enabled: DF.Check
		expression: DF.Code
		group_by: DF.Code
		group_interval: DF.Data
		group_wait: DF.Data
		labels: DF.Code
		repeat_interval: DF.Data
		route_preview: DF.Code | None
		severity: DF.Literal["Critical", "Warning", "Information"]
	# end: auto-generated types

	def validate(self):
		self.alert_preview = yaml.dump(self.get_rule())
		self.route_preview = yaml.dump(self.get_route())

	def get_rule(self):
		labels = json.loads(self.labels)
		labels.update({"severity": self.severity.lower()})

		annotations = json.loads(self.annotations)
		annotations.update({"description": self.description})

		rule = {
			"alert": self.name,
			"expr": self.expression,
			"for": self.get("for"),
			"labels": labels,
			"annotations": annotations,
		}
		return rule

	def get_route(self):
		route = {
			"group_by": json.loads(self.group_by),
			"group_wait": self.group_wait,
			"group_interval": self.group_interval,
			"repeat_interval": self.repeat_interval,
			"matchers": [f'alertname="{self.name}"'],
		}
		return route

	def on_update(self):
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
			rules_dict["groups"][0]["rules"].append(rule_doc.get_rule())

		return rules_dict

	def get_routes(self):
		routes_dict = {
			"route": {"receiver": "web.hook", "routes": []},
			"receivers": [
				{
					"name": "web.hook",
					"webhook_configs": [
						{"url": frappe.utils.get_url("api/method/press.api.monitoring.alert")}
					],
				}
			],
		}

		rules = frappe.get_all(self.doctype, {"enabled": True})
		for rule in rules:
			rule_doc = frappe.get_doc(self.doctype, rule.name)
			routes_dict["route"]["routes"].append(rule_doc.get_route())

		return routes_dict

	def react(self, instance_type: str, instance: str):
		frappe.new_doc(
			"Prometheus Alert Reaction",
			rule=self.name,
			instance_type=instance_type,
			instance=instance,
			method_name=self.reaction_method,
		).insert()
