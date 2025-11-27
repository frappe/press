# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import os
from contextlib import suppress
from itertools import groupby

import frappe
from frappe.model.document import Document

from press.runner import Ansible, Status, StepHandler


class ProxyFailover(Document, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.proxy_failover_steps.proxy_failover_steps import ProxyFailoverSteps

		failover_steps: DF.Table[ProxyFailoverSteps]
		primary: DF.Link
		secondary: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	# take both cases - primary up and primary down
	# assume secondary to be up

	# TODO: we'll also need to make sure secondary has the latest conf
	# one easy way is to validate the last X add site to upstream entries in agent job (which succeeded in primary)
	# and cross check it with secondary

	def before_insert(self):
		self.status = "Pending"

		for step in self.get_steps(
			[
				self.create_agent_job_for_routing_requests,
				self.wait_for_secondary_proxy_routing,
				self.update_dns_records_for_all_sites,
				self.stop_primary_agent_and_replication,
				self.update_app_servers,
				self.move_wildcard_domains_from_primary,
				self.remove_primary_access_and_start_nginx_in_secondary,
				self.forward_jobs_to_secondary,
				self.attach_static_ip_to_secondary,
				self.switch_primary,
				self.send_failover_email,
				self.add_ssh_users_for_existing_benches,
			]
		):
			self.append("failover_steps", step)

	def after_insert(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_execute_steps",
			steps=self.failover_steps,
			queue="long",
			timeout=3600,
			at_front_when_starved=True,
			enqueue_after_commit=True,
		)

	@frappe.whitelist()
	def create_agent_job_for_routing_requests(self, step=None):
		"""Route all traffic from primary to secondary proxy server"""

		def _update_status(comments, step=None, step_status=None, job=None):
			if step:
				step.status = step_status
				step.job = job
				step.output = comments
				step.save()
			else:
				frappe.msgprint(comments)

		primary_proxy = frappe.get_doc("Proxy Server", self.primary)
		if primary_proxy.is_static_ip:
			comments = "Primary proxy server has a static IP. Skipping routing."
			_update_status(comments, step, Status.Skipped)
			return

		# not pinging agent directly as:
		# maybe primary is up and we retried the failover - so agent might've gone down
		response = os.system(f"ping -c 1 {primary_proxy.ip}")
		if response != 0:
			comments = "Primary proxy server is not reachable. Skipping routing."
			_update_status(comments, step, Status.Skipped)
			return

		# TODO: trigger an agent job to add an nginx config to route all traffic to secondary
		# job = primary_proxy.route_traffic_to_secondary(self.secondary)
		_update_status("Queued", step, Status.Success)  # job.name)

	def wait_for_secondary_proxy_routing(self, step):
		job = frappe.db.get_value(
			"Proxy Failover Steps",
			{
				"parent": self.name,
				"step_name": "Route all traffic from primary to secondary proxy server",
			},
			"job",
		)

		if not job:
			step.status = Status.Skipped
			step.output = "No routing job found. Skipping wait step."
			step.save()
			return

		step.status = Status.Running

		with suppress(Exception):
			# this can be handled externally too using create_agent_job_for_routing_requests
			self.handle_agent_job(step, job)

	def attach_static_ip_to_secondary(self, step):
		primary = frappe.db.get_value(
			"Proxy Server", self.primary, ["is_static_ip", "virtual_machine"], as_dict=True
		)
		if not primary.is_static_ip:
			step.status = Status.Skipped
			step.output = "Primary proxy server does not have a static IP. Skipping static IP attachment."
			step.save()
			return

		step.status = Status.Running
		step.save()

		primary_vm = frappe.get_doc("Virtual Machine", primary.virtual_machine)
		secondary_vm = frappe.get_doc(
			"Virtual Machine", frappe.db.get_value("Proxy Server", self.secondary, "virtual_machine")
		)

		static_ip = primary_vm.public_ip_address  # assuming this is the static ip
		primary_vm.detach_static_ip()
		secondary_vm.attach_static_ip(static_ip)

		step.status = Status.Success
		step.save()

	def update_dns_records_for_all_sites(self, step):
		step.status = Status.Running
		step.save()

		servers = frappe.get_all("Server", {"proxy_server": self.primary}, pluck="name")
		sites_domains = frappe.get_all(
			"Site",
			{"status": ("!=", "Archived"), "server": ("in", servers)},
			["name", "domain"],
		)
		for domain_name, sites in groupby(sites_domains, lambda x: x["domain"]):
			domain = frappe.get_doc("Root Domain", domain_name)
			domain.update_dns_records_for_sites([site.name for site in sites], self.secondary)

		step.status = Status.Success
		step.save()

	def add_ssh_users_for_existing_benches(self, step):
		if not frappe.db.get_value("Proxy Server", self.secondary, "is_ssh_proxy_setup"):
			step.status = Status.Skipped
			step.output = "SSH Proxy is not set up on the secondary proxy server. Skipping SSH user addition."
			step.save()
			return

		step.status = Status.Running
		step.save()

		benches = frappe.qb.DocType("Bench")
		servers = frappe.qb.DocType("Server")
		active_benches = (
			frappe.qb.from_(benches)
			.join(servers)
			.on(servers.name == benches.server)
			.select(benches.name)
			.where(benches.status == "Active")
			.where(servers.proxy_server == self.secondary)
			.run(as_dict=True)
		)
		for bench_name in active_benches:
			bench = frappe.get_doc("Bench", bench_name)
			bench.add_ssh_user()

		step.status = Status.Success
		step.save()

	def update_app_servers(self, step):
		frappe.db.set_value("Server", {"proxy_server": self.primary}, "proxy_server", self.secondary)

		step.status = Status.Success
		step.save()

	def switch_primary(self, step):
		frappe.db.set_value(
			"Proxy Server",
			self.secondary,
			{"is_primary": True, "is_replication_setup": False, "primary": None},
		)

		step.status = Status.Success
		step.save()

	def forward_jobs_to_secondary(self, step):
		frappe.db.set_value(
			"Agent Job",
			{"server": self.primary, "status": "Undelivered"},
			"server",
			self.secondary,
		)

		step.status = Status.Success
		step.save()

	def move_wildcard_domains_from_primary(self, step):
		frappe.db.set_value(
			"Proxy Server Domain",
			{"parent": self.primary},
			"parent",
			self.secondary,
		)
		step.status = Status.Success
		step.save()

	def stop_primary_agent_and_replication(self, step):
		step.status = Status.Running

		try:
			primary_proxy = frappe.get_doc("Proxy Server", self.primary)
			ansible = Ansible(
				playbook="failover_prepare_primary_proxy.yml",
				server=primary_proxy,
				user=primary_proxy._ssh_user(),
				port=primary_proxy._ssh_port(),
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			# no need to raise an error here as even if primary is down, we need to proceed

	def remove_primary_access_and_start_nginx_in_secondary(self, step):
		step.status = Status.Running

		try:
			secondary_proxy = frappe.get_doc("Proxy Server", self.secondary)
			ansible = Ansible(
				playbook="failover_up_secondary_proxy.yml",
				server=secondary_proxy,
				user=secondary_proxy._ssh_user(),
				port=secondary_proxy._ssh_port(),
				variables={
					"primary_public_key": frappe.db.get_value(
						"Proxy Server", self.primary, "frappe_public_key"
					)
				},
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def send_failover_email(self, step):
		step.status = Status.Skipped
		step.save()
