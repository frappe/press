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

		agent_password: DF.Password | None
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
		tls_certificate_renewal_failed: DF.Check
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_cluster()
		self.validate_agent_password()

	def get_config(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		agent_branch = self.get_agent_repository_branch()
		monitoring_password = frappe.get_doc("Cluster", self.cluster).get_password("monitoring_password")
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)

		return {
			"certificate_private_key": certificate.private_key,
			"certificate_full_chain": certificate.full_chain,
			"certificate_intermediate_chain": certificate.intermediate_chain,
			"monitoring_password": monitoring_password,
			"agent_repository_url": agent_repository_url,
			"agent_password": agent_password,
			"agent_branch": agent_branch,
			"workers": 1,
			"server": self.name,
		}

	@frappe.whitelist()
	def setup_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_setup_server", queue="long", timeout=2400)

	def _setup_server(self):
		try:
			config = self.get_config() | {
				"primary_ip": self.private_ip,
				"secondary_ip": self.secondary_private_ip,
			}
			ansible = Ansible(
				playbook="nat_server.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables=config,
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
		failover = frappe.get_doc(
			{
				"doctype": "NAT Failover",
				"primary": self.name,
				"secondary": secondary,
			}
		).insert()

		return f"Failover Reference: {frappe.get_desk_link(failover.doctype, failover.name)}"

	@frappe.whitelist()
	def configure_monitoring(self):
		try:
			ansible = Ansible(
				playbook="configure_monitoring_for_nat.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables=self.get_config(),
			)
			ansible.run()
		except Exception as e:
			log_error("Configure Monitoring Failed", server=self.as_dict(), error=str(e))

	@frappe.whitelist()
	def attach_nat_security_group(self):
		vm = frappe.get_doc("Virtual Machine", self.virtual_machine)
		ec2 = vm.client()
		response = ec2.describe_instances(InstanceIds=[vm.instance_id])
		sgs = [
			sg["GroupId"]
			for reservation in response["Reservations"]
			for instance in reservation["Instances"]
			for sg in instance["SecurityGroups"]
		]

		nat_sg = frappe.db.get_value("Cluster", self.cluster, "nat_security_group_id")
		if not nat_sg:
			frappe.throw(
				"NAT Security Group not found for the cluster. Please set it in the Cluster doctype."
			)

		if nat_sg in sgs:
			frappe.throw(
				"NAT Security Group is already attached to the instance. No changes are required to be made."
			)

		sgs.append(nat_sg)
		ec2.modify_instance_attribute(InstanceId=vm.instance_id, Groups=sgs)

		return "NAT Security Group attached successfully"
