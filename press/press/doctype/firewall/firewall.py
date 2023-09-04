# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.runner import Ansible
from press.utils import log_error


class Firewall(Document):
	def get_details(self):
		return {
			"firewall_name": self.firewall_name,
			"server": self.server,
			"server_type": self.server_type,
			"rules": self.get_rules(),
		}

	def get_rules(self):
		from press.press.doctype.firewall_rule.firewall_rule import FirewallRule

		return FirewallRule.fetch_firewall_rules(
			self.firewall_name, self.server_type, self.server
		)

	def update_firewall_rules(self, firewall_rules):
		from press.press.doctype.firewall_rule.firewall_rule import FirewallRule

		_rules = []
		for rule in firewall_rules:
			if rule.get("name"):
				_rules.append(rule.get("name"))
			else:
				_rules.append(FirewallRule.create_firewall_rule(rule, firewall=self))

		for rule in [rule for rule in self.get_rules() if rule.name not in _rules]:
			FirewallRule.delete_firewall_rule(rule.name)

	def _update_firewall(self):
		try:
			Ansible.run_playbook(
				"playbooks/firewall.yml",
				extra_vars={"rules": self.get_rules()},
			)
		except Exception as e:
			log_error(title="Firewall Update Failed", message=e)

	@staticmethod
	def create_firewall(server, server_type, firewall_name) -> Document:
		try:
			return frappe.get_doc(
				{
					"doctype": "Firewall",
					"firewall_name": firewall_name,
					"server": server,
					"server_type": server_type,
				}
			).insert(ignore_permissions=True)

		except frappe.DuplicateEntryError:
			pass

	@staticmethod
	def fetch_firewall_rules(server, server_type):
		firewall_name = frappe.db.get_value(
			"Firewall",
			{"server": server, "server_type": server_type},
			"firewall_name",
			cache=True,
		)

		if not firewall_name:
			return {}

		return frappe.get_cached_doc("Firewall", firewall_name).get_details()

	@staticmethod
	def update_firewall(firewall, firewall_rules):
		firewall.update_firewall_rules(firewall_rules)
