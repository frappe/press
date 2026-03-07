# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class NATServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cluster: DF.Link | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		hostname: DF.Data | None
		ip: DF.Data | None
		is_server_setup: DF.Check
		is_static_ip: DF.Check
		private_ip: DF.Data | None
		provider: DF.Literal["AWS EC2"]
		root_public_key: DF.Code | None
		secondary_private_ip: DF.Data | None
		ssh_port: DF.Data | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_cluster()

	@frappe.whitelist()
	def setup_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_setup_server", queue="long", timeout=2400)

	def _setup_server(self):
		try:
			ansible = Ansible(
				playbook="nat_server.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"primary_ip": self.private_ip,
					"secondary_ip": self.secondary_private_ip,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Server Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def trigger_failover(self, secondary: str):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_trigger_failover",
			secondary=secondary,
			queue="long",
			timeout=1200,
			at_front=True,
		)
		return "Failover Queued"

	def _trigger_failover(self, secondary: str):
		if not self.secondary_private_ip:
			frappe.throw("Secondary IP not configured on current NAT Server")

		secondary_nat_server = frappe.get_doc("NAT Server", secondary)
		if secondary_nat_server.secondary_private_ip:
			frappe.throw("Secondary NAT Server already has a secondary IP configured")

		vm = frappe.get_doc("Virtual Machine", self.virtual_machine)
		secondary_vm = frappe.get_doc("Virtual Machine", secondary_nat_server.virtual_machine)
		if self.is_static_ip and not secondary_vm.is_static_ip:
			ip = self.ip
			vm.detach_static_ip()
			secondary_vm.attach_static_ip(ip)

		try:
			secondary_private_ip = self.secondary_private_ip
			vm.detach_secondary_private_ip()
			secondary_vm.attach_secondary_private_ip(secondary_private_ip)

			ansible = Ansible(
				playbook="configure_secondary_ip_in_secondary_nat.yml",
				server=secondary_nat_server,
				user=secondary_nat_server._ssh_user(),
				port=secondary_nat_server._ssh_port(),
				variables={
					"primary_ip": secondary_vm.private_ip_address,
					"secondary_ip": secondary_private_ip,
				},
			)
			play = ansible.run()
			if play.status != "Success":
				raise
		except Exception:
			log_error(
				"NAT Server Failover Exception",
				secondary=secondary,
				primary=self.name,
				reference_doctype="NAT Server",
				reference_name=secondary,
			)
