# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import yaml
import json
from frappe.model.document import Document
from press.agent import Agent


class PrometheusAlertRule(Document):
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
