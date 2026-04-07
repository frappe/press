# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import socket
import time
from contextlib import suppress
from itertools import groupby

import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now

from press.agent import Agent
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
from press.runner import Ansible, StepHandler


class IPRemovalLog(Document, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.ip_removal_log_steps.ip_removal_log_steps import IPRemovalLogSteps

		cluster: DF.Link
		error: DF.Text | None
		limit: DF.Int
		nat_server: DF.Link
		removal_steps: DF.Table[IPRemovalLogSteps]
		server_type: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=30):
		table = frappe.qb.DocType("IP Removal Log")
		frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))

	def before_insert(self):
		if self.server_type not in ("Server", "Database Server"):
			frappe.throw(
				"Server Type must be either 'Server' or 'Database Server'. Please select one of those."
			)

		self.status = "Pending"

		filters = {
			"status": "Active",
			"cluster": self.cluster,
			"ip": ("is", "set"),
			"nat_server": ("is", "not set"),
			"is_self_hosted": 0,
		}
		if self.server_type == "Server":
			filters |= {"is_static_ip": 0}

		servers = frappe.get_all(
			self.server_type, filters=filters, limit_page_length=self.limit, pluck="name"
		)
		for server in servers:
			step = {
				"method_name": self.remove_ip_and_add_nat_conf.__name__,
				"status": "Pending",
				"server": server,
				"agent_ping": "Pending",
				"server_ping": "Pending",
			}
			self.append("removal_steps", step)

	@frappe.whitelist()
	def execute_removal_steps(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_execute_steps",
			steps=self.removal_steps,
			queue="long",
			timeout=3600,
			enqueue_after_commit=True,
			job_id=f"ip_removal_{self.name}",
			deduplicate=True,
		)

	def remove_ip_and_add_nat_conf(self, step):
		if not frappe.cache.get_value(f"{self.name}:{self.nat_server}"):
			# set the ip in cache
			nat_private_ip = frappe.db.get_value(
				"NAT Server", self.nat_server, ("private_ip", "secondary_private_ip"), as_dict=True
			)
			frappe.cache.set_value(
				f"{self.name}:{self.nat_server}",
				nat_private_ip.secondary_private_ip or nat_private_ip.private_ip,
			)

		doc = frappe.get_doc(self.server_type, step.server)
		if doc.ip:
			try:
				vm = frappe.get_doc("Virtual Machine", doc.virtual_machine)
				vm.disassociate_auto_assigned_public_ip()
			except frappe.ValidationError:
				step.output = "Failed to disassociate public ip. Possibly failed to get a lock on the VM."
				step.status = "Failure"
				step.save()
				return

			frappe.db.commit()

		doc.reload()
		doc.nat_server = self.nat_server
		doc.save()

		try:
			ansible = Ansible(
				playbook="nat_iptables.yml",
				server=doc,
				user=doc._ssh_user(),
				port=doc._ssh_port(),
				variables={
					"nat_gateway_ip": frappe.cache.get_value(f"{self.name}:{self.nat_server}"),
				},
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			# not raising here - we can sort these out manually, let the rest complete
			return

		if not self.check_local_dns_propagation(step, doc.name, doc.private_ip):
			step.output = (
				"DNS propagation did not complete in expected time. Please check if the server is accessible."
			)
			step.status = "Failure"
			step.save()
			return

		self.server_egress_ping(step)
		self.agent_ping(step)

		step.status = "Failure"
		if step.agent_ping == "Success" and step.server_ping == "Success":
			step.status = "Success"
		step.save()

	def agent_ping(self, step):
		message = ""
		agent = Agent(step.server, self.server_type)
		with suppress(Exception):
			message = agent.ping()

		step.agent_ping = "Success" if message == "pong" else "Failure"
		step.save()

	def server_egress_ping(self, step):
		result = AnsibleAdHoc(sources=f"{step.server},").run("curl ifconfig.me")[0]
		step.server_ping = "Success" if result.get("status") == "Success" else "Failure"
		step.save()

	def check_local_dns_propagation(self, step, server_name, private_ip):
		step.attempt = 0
		while step.attempt < 60:
			try:
				ip = socket.gethostbyname(server_name)
				if ip == private_ip:
					step.save()
					return True
			except socket.gaierror:
				pass

			step.attempt += 1
			time.sleep(10)

		step.save()
		return False

	@frappe.whitelist()
	def reduce_dns_ttl(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_reduce_dns_ttl",
			queue="long",
			timeout=1800,
			enqueue_after_commit=True,
			job_id=f"reduce_dns_ttl_{self.name}",
			deduplicate=True,
		)

	def _reduce_dns_ttl(self):
		servers = [step.server for step in self.removal_steps if step.status == "Pending"]
		server_domains = frappe.get_all(
			self.server_type,
			{"name": ("in", servers)},
			["name", "domain", "ip"],
			order_by="domain",
		)
		for domain_name, servers in groupby(server_domains, lambda x: x["domain"]):
			changes = []
			for server in servers:
				changes.append(
					{
						"Action": "UPSERT",
						"ResourceRecordSet": {
							"Name": server["name"],
							"Type": "A",
							"TTL": 60,
							"ResourceRecords": [{"Value": server["ip"]}],
						},
					}
				)

			domain = frappe.get_doc("Root Domain", domain_name)
			domain.boto3_client.change_resource_record_sets(
				ChangeBatch={"Changes": changes}, HostedZoneId=domain.hosted_zone
			)
