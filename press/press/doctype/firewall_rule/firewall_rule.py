# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FirewallRule(Document):
	@staticmethod
	def fetch_firewall_rules(server, server_type):
		rules = frappe.db.get_all(
			"Firewall Rule",
			fields=[
				"name",
				"server",
				"server_type",
				"action",
				"protocol",
				"service",
				"description",
				"from_port",
				"to_port",
				"source_type",
				"source",
			],
			filters={"server": server, "server_type": server_type},
		)

		if not rules:
			rules = FirewallRule.get_default_rules_for_cluster(server, server_type)

		return FirewallRule.simplified_rules(rules, server_type, server)

	@staticmethod
	def get_default_rules_for_cluster(server, server_type):
		cluster = frappe.db.get_value(server_type, server, "cluster")
		cluster_doc = frappe.get_cached_doc("Cluster", cluster)

		if server_type == "Proxy Server":
			return cluster_doc.get_proxy_ip_permissions()
		else:
			return cluster_doc.get_ip_permissions()

	@staticmethod
	def simplified_rules(rules, server_type=None, server=None):
		simplified_rules = []
		for rule in rules:
			simplified_rule = frappe._dict(
				{
					"server": rule.get("server", server),
					"server_type": rule.get("server_type", server_type),
					"name": rule.get("name") or "",
					"firewall_status": "Enabled",  # if rule.get('name') else 'Disabled'
				}
			)

			simplified_rule.action = rule.get("action") or "Allow"
			simplified_rule.protocol = rule.get("protocol") or rule.get("IpProtocol")
			simplified_rule.protocol = simplified_rule.protocol.upper()

			simplified_rule.from_port = rule.get("from_port") or rule.get("FromPort")
			simplified_rule.to_port = rule.get("to_port") or rule.get("ToPort")
			simplified_rule.service = port_mapper(simplified_rule.from_port)

			simplified_rule.description = (
				rule.get("description") or rule["IpRanges"][0]["Description"]
			)
			simplified_rule.source_type = rule.get("source_type") or "Custom"
			simplified_rule.source = rule.get("source") or rule["IpRanges"][0]["CidrIp"]

			if simplified_rule.from_port == simplified_rule.to_port:
				simplified_rule.port_range = f"{simplified_rule.from_port}"
			else:
				simplified_rule.port_range = (
					f"{simplified_rule.from_port} - {simplified_rule.to_port}"
				)

			simplified_rules.append(simplified_rule)

		return simplified_rules


def port_mapper(port):
	return {
		80: "HTTP",
		443: "HTTPS",
		22: "SSH",
		3306: "MariaDB",
		2222: "Proxy SSH",
		-1: "ICMP",
	}.get(port, port)
