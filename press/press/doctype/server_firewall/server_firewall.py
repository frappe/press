# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import ipaddress

import frappe
from frappe import _
from frappe.model.document import Document

from press.press.doctype.server.server import Server
from press.runner import Ansible
from press.utils import log_error


class ServerFirewall(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.server_firewall_rule.server_firewall_rule import ServerFirewallRule

		enabled: DF.Check
		rules: DF.Table[ServerFirewallRule]
		server_id: DF.Link
	# end: auto-generated types

	dashboard_fields = (
		"enabled",
		"rules",
	)

	def has_permission(self, permtype="read", *, debug=False, user=None) -> bool:
		return self.server.has_permission(permtype, debug=debug, user=user)

	def after_insert(self):
		self.setup()

	@frappe.whitelist()
	def setup(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_setup",
		)

	def _setup(self):
		try:
			Ansible(
				playbook="firewall_setup.yml",
				server=self.server,
				user=self.server._ssh_user(),
				port=self.server._ssh_port(),
			).run()
		except Exception:
			log_error("Failed to setup firewall", doc=self)

	def on_trash(self):
		self.teardown()

	@frappe.whitelist()
	def teardown(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_teardown",
		)

	def _teardown(self):
		try:
			Ansible(
				playbook="firewall_teardown.yml",
				server=self.server,
				user=self.server._ssh_user(),
				port=self.server._ssh_port(),
			).run()
		except Exception:
			log_error("Failed to teardown firewall", doc=self)

	def before_validate(self):
		self.deduplicate_rules()

	def deduplicate_rules(self):
		"""
		Remove duplicate entries from rules. This will not save the doc.
		"""
		rules_seen = set()
		unique_rules = []
		for rule in self.rules:
			rule_tuple = (rule.source, rule.destination, rule.protocol, rule.action)
			if rule_tuple not in rules_seen:
				rules_seen.add(rule_tuple)
				unique_rules.append(rule)
		self.rules = unique_rules

	def validate(self):
		self.prevent_selfhosted()
		self.validate_rules()

	def prevent_selfhosted(self):
		if self.server.is_self_hosted:
			message = _("Firewall cannot be enabled for self-hosted servers.")
			frappe.throw(message, frappe.ValidationError)

	def validate_rules(self):
		for rule in self.rules:
			self.validate_ip(rule.source)
			self.validate_ip(rule.destination)

	def on_update(self):
		self.sync()

	@frappe.whitelist()
	def sync(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_sync",
			queue="default",
			enqueue_after_commit=True,
			deduplicate=True,
			job_id=f"sync_firewall_{self.name}",
		)

	def _sync(self):
		self._sync_firewall()
		self._sync_nginx()

	def _sync_firewall(self):
		try:
			Ansible(
				playbook="firewall_sync.yml",
				server=self.server,
				user=self.server._ssh_user(),
				port=self.server._ssh_port(),
				variables={
					"enabled": bool(self.enabled),
					"rules": list(self.get_rules()),
					"rules_bypass": self.get_bypass_rules(),
				},
			).run()
		except Exception:
			log_error("Failed to sync firewall rules", doc=self)

	def _sync_nginx(self):
		ip_accept = [rule.source for rule in self.rules if rule.action == "Allow" and rule.source]
		ip_drop = [rule.source for rule in self.rules if rule.action == "Block" and rule.source]
		try:
			return self.server.agent.update_nginx_access(ip_accept, ip_drop)
		except Exception:
			log_error("Failed to sync nginx access rules", doc=self)

	def validate_ip(self, ip: str):
		"""Checks if the provided string is a valid IPv4 or IPv6 address."""
		if not ip:
			return
		try:
			ipaddress.ip_network(ip, strict=False)
		except ValueError:
			message = _("{0} is not a valid IP address or CIDR.").format(ip)
			frappe.throw(message, frappe.ValidationError)

	def get_rules(self):
		for rule in self.rules:
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

	def get_bypass_rules(self):
		monitors = frappe.get_all("Monitor Server", pluck="ip")
		rules = []
		for monitor in monitors:
			rules.append(
				{
					"source": monitor,
					"protocol": "TCP",
					"action": "ACCEPT",
				}
			)
			rules.append(
				{
					"destination": monitor,
					"protocol": "TCP",
					"action": "ACCEPT",
				}
			)
		return rules

	def transform_action(self, action: str):
		match action:
			case "Allow":
				return "ACCEPT"
			case "Block":
				return "DROP"
			case _:
				return "REJECT"

	@property
	def server(self) -> Server:
		return frappe.get_doc("Server", self.server_id)
