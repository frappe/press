import ipaddress

import frappe
from frappe import _

from press.runner import Ansible
from press.utils import log_error


class ServerFirewall:
	@frappe.whitelist()
	def setup_firewall(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_setup_firewall",
		)

	def _setup_firewall(self):
		try:
			Ansible(
				playbook="firewall_setup.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			).run()
		except Exception:
			log_error("Failed to setup firewall", doc=self)

	@frappe.whitelist()
	def teardown_firewall(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_teardown_firewall",
		)

	def _teardown_firewall(self):
		try:
			Ansible(
				playbook="firewall_teardown.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			).run()
		except Exception:
			log_error("Failed to teardown firewall", doc=self)

	def sync_firewall(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_sync_firewall",
			queue="default",
			enqueue_after_commit=True,
			deduplicate=True,
			job_id=f"sync_firewall_{self.name}",
		)

	def _sync_firewall(self):
		try:
			Ansible(
				playbook="firewall_sync.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"enabled": bool(self.firewall_enabled),
					"rules": list(self.transform_rules()),
				},
			).run()
		except Exception:
			log_error("Failed to sync firewall rules", doc=self)

	def deduplicate_firewall_rules(self):
		"""
		Remove duplicate entries from rules. This will not save the doc.
		"""
		rules_seen = []
		rules = self.firewall_rules
		for rule in rules:
			rule_tuple = (rule.source, rule.destination, rule.protocol, rule.action)
			if rule_tuple not in rules_seen:
				rules_seen.append(rule_tuple)
			else:
				self.firewall_rules.remove(rule)

	def validate_firewall_rules(self):
		for rule in self.firewall_rules:
			self.validate_ip(rule.source)
			self.validate_ip(rule.destination)

	def validate_ip(self, ip: str):
		"""Checks if the provided string is a valid IPv4 or IPv6 address."""
		if not ip:
			return
		try:
			ipaddress.ip_network(ip, strict=False)
		except ValueError:
			message = _("{0} is not a valid IP address or CIDR.").format(ip)
			frappe.throw(message, frappe.ValidationError)

	def transform_rules(self):
		for rule in self.firewall_rules:
			rule = {
				"source": rule.source,
				"destination": rule.destination,
				"protocol": rule.protocol,
				"action": self.transform_action(rule.action),
			}
			if not rule["source"]:
				rule.pop("source")
			if not rule["destination"]:
				rule.pop("destination")
			yield rule

	def transform_action(self, action: str):
		match action:
			case "Allow":
				return "ACCEPT"
			case "Block":
				return "DROP"
			case _:
				return "REJECT"
