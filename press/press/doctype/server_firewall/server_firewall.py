# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import ipaddress

import frappe
from frappe import _
from frappe.model.document import Document

from press.overrides import has_permission as has_press_permission
from press.press.doctype.server.server import Server
from press.runner import Ansible
from press.utils import get_current_team, log_error


class ServerFirewall(Document):
	"""Manages firewall rules for a server and syncs them via Ansible and Nginx."""

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

	@staticmethod
	def get_list_query(query):
		"""Filter list query to only show firewalls belonging to the current team."""
		Server = frappe.qb.DocType("Server")
		Firewall = frappe.qb.DocType("Server Firewall")
		current_team = get_current_team()
		return (
			query.inner_join(Server).on(Server.name == Firewall.server_id).where(Server.team == current_team)
		)

	def before_validate(self):
		self.deduplicate_rules()

	def deduplicate_rules(self):
		"""
		Remove duplicate entries from rules. This will not save the doc.
		"""
		rules_seen = set()
		unique_rules = []
		for rule in self.rules:
			rule_tuple = (rule.source, rule.port, rule.protocol, rule.action)
			if rule_tuple not in rules_seen:
				rules_seen.add(rule_tuple)
				unique_rules.append(rule)
		self.rules = unique_rules

	def validate(self):
		"""Run all validations before saving."""
		self.prevent_selfhosted()
		self.validate_rules()

	def prevent_selfhosted(self):
		"""Prevent enabling firewall for self-hosted servers."""
		if self.server.is_self_hosted:
			message = _("Firewall cannot be enabled for self-hosted servers.")
			frappe.throw(message, frappe.ValidationError)

	def validate_rules(self):
		"""Validate IP addresses and ports for all firewall rules."""
		for rule in self.rules:
			self.validate_ip(rule.source)
			self.validate_port(rule.port)

	def on_update(self):
		self.sync()

	@frappe.whitelist()
	def sync(self):
		"""Enqueue a background job to sync firewall and Nginx rules."""
		if frappe.flags.in_test:  # TODO: Remove
			return
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
		"""Sync both firewall and Nginx rules."""
		self._sync_firewall()
		self._sync_nginx()

	def _sync_firewall(self):
		"""Run the Ansible playbook to sync firewall rules on the server."""
		try:
			Ansible(
				playbook="firewall_sync.yml",
				server=self.server,
				user=self.server._ssh_user(),
				port=self.server._ssh_port(),
				variables={
					"enabled": bool(self.enabled),
					"protected_ips": self.get_protected_ips(),
					"rules": list(self.get_rules()),
				},
			).run()
		except Exception:
			log_error("Failed to sync firewall rules", doc=self)

	def _sync_nginx(self):
		"""Update Nginx access rules with allowed and denied IPs."""
		ip_accept = self.get_allowed_ips_for_nginx()
		ip_drop = [rule.source for rule in self.rules if rule.action == "Deny" and rule.source]
		try:
			return self.server.agent.update_nginx_access(ip_accept, ip_drop)
		except Exception:
			log_error("Failed to sync nginx access rules", doc=self)

	def get_allowed_ips_for_nginx(self):
		"""Return list of IPs that should be allowed through Nginx."""
		allowed_ips = [rule.source for rule in self.rules if rule.action == "Allow" and rule.source]
		allowed_ips.extend(self.get_protected_ips())
		return allowed_ips

	def validate_ip(self, ip: str):
		"""Checks if the provided string is a valid IPv4 or IPv6 address."""
		if not ip:
			return
		try:
			ipaddress.ip_network(ip, strict=False)
		except ValueError:
			message = _("{0} is not a valid IP address or CIDR.").format(ip)
			frappe.throw(message, frappe.ValidationError)

	def validate_port(self, port):
		"""Check if the provided port number is within the valid range."""
		port = int(port)
		if not port:
			return
		if port < 1 or port > 65535:
			message = _("{0} is not a valid port number.").format(port)
			frappe.throw(message, frappe.ValidationError)

	def get_rules(self):
		"""Yield firewall rules as dicts suitable for the Ansible playbook."""
		for rule in self.rules:
			entry = {
				"source": rule.source,
				"action": rule.action,
			}
			if rule.port and rule.protocol:
				entry["port"] = rule.port
				entry["protocol"] = rule.protocol
			yield entry

	def get_protected_ips(self) -> list[str]:
		"""Return IPs that should always be allowed through the firewall."""
		ips = frappe.get_all("Monitor Server", pluck="ip")
		if proxy_ip := self.server.get_proxy_ip():
			ips.append(proxy_ip)
		if nat_ip := self.server.get_nat_gateway_ip():
			ips.append(str(ipaddress.ip_network(nat_ip + "/24", strict=False)))
		if self.production_ip:
			ips.append(self.production_ip)
		return ips

	@property
	def production_ip(self) -> str | None:
		"""Return the production server IP from Press Settings."""
		return frappe.db.get_single_value("Press Settings", "production_server_ip", cache=True)

	@property
	def server(self) -> Server:
		"""Return the Server document associated with this firewall."""
		return frappe.get_doc("Server", self.server_id)


def has_permission(doc, user=None, permission_type=None) -> bool:
	"""Check if the user has permission to access this firewall's server."""
	return has_press_permission(doc.server, permission_type, user)


def from_server(doc, method=None) -> ServerFirewall | None:
	"""Get or create a Server Firewall document for the given server."""
	if doc.is_self_hosted:
		return None
	if frappe.db.exists({"doctype": "Server Firewall", "server_id": doc.name}):
		return frappe.get_doc("Server Firewall", doc.name)
	firewall = frappe.new_doc("Server Firewall")
	firewall.server_id = doc.name
	return firewall.insert()
