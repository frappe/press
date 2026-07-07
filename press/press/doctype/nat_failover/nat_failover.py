# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
from press.runner import Ansible, StepHandler


class NATFailover(Document, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.nat_failover_steps.nat_failover_steps import NATFailoverSteps

		error: DF.Text | None
		failover_steps: DF.Table[NATFailoverSteps]
		primary: DF.Link
		secondary: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	def before_insert(self):
		self.status = "Pending"

		primary = frappe.db.get_value("NAT Server", self.primary, ("secondary_private_ip"), as_dict=True)
		if not primary.secondary_private_ip:
			frappe.throw(
				"Secondary IP not configured on primary NAT Server. Cannot proceed with the failover."
			)

		secondary = frappe.db.get_value("NAT Server", self.secondary, ("secondary_private_ip"), as_dict=True)
		if secondary.secondary_private_ip:
			frappe.throw(
				"Secondary NAT Server already has a secondary IP configured. Please choose a nat server without a secondary IP configured."
			)

		for step in self.get_steps(
			[
				self.attach_static_ip_to_secondary,
				self.attach_secondary_private_ip_to_secondary,
				self.configure_secondary_private_ip_on_secondary,
				self.update_servers,
				self.test_server_egress,
			]
		):
			self.append("failover_steps", step)

	def after_insert(self):
		self.execute_failover_steps()

	def execute_failover_steps(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_execute_steps",
			steps=self.failover_steps,
			queue="long",
			timeout=3600,
			at_front=True,
			enqueue_after_commit=True,
			job_id=f"nat_failover_{self.name}",
			deduplicate=True,
		)

	def attach_static_ip_to_secondary(self, step):
		primary_vm_name = frappe.db.get_value("NAT Server", self.primary, "virtual_machine")
		secondary_vm_name = frappe.db.get_value("NAT Server", self.secondary, "virtual_machine")

		primary_vm = frappe.get_doc("Virtual Machine", primary_vm_name)
		secondary_vm = frappe.get_doc("Virtual Machine", secondary_vm_name)
		if not primary_vm.is_static_ip or secondary_vm.is_static_ip:
			step.status = "Skipped"
			step.save()
			return

		ip = primary_vm.ip
		primary_vm.detach_static_ip()
		secondary_vm.attach_static_ip(ip)

		step.status = "Success"
		step.save()

	def attach_secondary_private_ip_to_secondary(self, step):
		primary_vm_name = frappe.db.get_value("NAT Server", self.primary, "virtual_machine")
		secondary_vm_name = frappe.db.get_value("NAT Server", self.secondary, "virtual_machine")

		primary_vm = frappe.get_doc("Virtual Machine", primary_vm_name)
		secondary_vm = frappe.get_doc("Virtual Machine", secondary_vm_name)

		secondary_private_ip = primary_vm.secondary_private_ip
		primary_vm.detach_secondary_private_ip()
		secondary_vm.attach_secondary_private_ip(secondary_private_ip)

		step.status = "Success"
		step.save()

	def configure_secondary_private_ip_on_secondary(self, step):
		secondary_nat_server = frappe.get_doc("NAT Server", self.secondary)

		try:
			ansible = Ansible(
				playbook="configure_secondary_ip.yml",
				server=secondary_nat_server,
				user=secondary_nat_server._ssh_user(),
				port=secondary_nat_server._ssh_port(),
				variables={
					"primary_ip": secondary_nat_server.private_ip,
					"secondary_ip": secondary_nat_server.secondary_private_ip,
				},
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def update_servers(self, step):
		for dt in ("Server", "Database Server"):
			frappe.db.set_value(
				dt,
				{"nat_server": self.primary},
				"nat_server",
				self.secondary,
			)

		step.status = "Success"
		step.save()

	def test_server_egress(self, step):
		server = frappe.db.get_value("Server", {"status": "Active", "nat_server": self.secondary}, "name")
		if not server:
			step.status = "Skipped"
			step.save()
			return

		result = AnsibleAdHoc(sources=f"{server},").run("curl ifconfig.me")[0]
		step.status = "Success" if result.get("status") == "Success" else "Failure"
		step.save()

	@frappe.whitelist()
	def force_continue(self):
		self.error = None

		for step in self.failover_steps:
			if step.status == "Failure":
				step.status = "Pending"

		self.save()

		self.execute_failover_steps()
		frappe.msgprint("Failover steps re-queued.", alert=True)
