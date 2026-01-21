import frappe

from press.runner import Ansible
from press.utils import log_error


class ServerFirewall:
	@frappe.whitelist()
	def setup_firewall(self):
		Ansible(
			playbook="firewall_setup.yml",
			server=self,
			user=self._ssh_user(),
			port=self._ssh_port(),
		).run()

	@frappe.whitelist()
	def teardown_firewall(self):
		Ansible(
			playbook="firewall_teardown.yml",
			server=self,
			user=self._ssh_user(),
			port=self._ssh_port(),
		).run()

	def sync_firewall(self):
		frappe.enqueue_doc(self.doctype, self.name, "_sync_firewall")

	def _sync_firewall(self):
		try:
			Ansible(
				playbook="firewall_sync.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"enabled": bool(self.firewall_enabled),
					"rules": [
						{
							"source": rule.source,
							"destination": rule.destination,
							"protocol": rule.protocol,
							"action": self.transform_action(rule.action),
						}
						for rule in self.firewall_rules
					],
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

	def transform_action(self, action: str):
		match action:
			case "Allow":
				return "ACCEPT"
			case "Block":
				return "DROP"
			case _:
				return "REJECT"
