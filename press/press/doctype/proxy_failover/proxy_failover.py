# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from contextlib import suppress
from itertools import groupby

import frappe
from frappe.model.document import Document

from press.press.doctype.agent_job.agent_job import Agent, handle_polled_jobs, poll_random_jobs
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
from press.runner import Ansible, Status, StepHandler


class ProxyFailover(Document, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.proxy_failover_steps.proxy_failover_steps import ProxyFailoverSteps

		error: DF.Text | None
		failover_steps: DF.Table[ProxyFailoverSteps]
		primary: DF.Link
		secondary: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	def before_insert(self):
		self.status = "Pending"

		primary = frappe.db.get_value("Proxy Server", self.primary, ["cluster", "is_static_ip"], as_dict=True)
		secondary = frappe.db.get_value(
			"Proxy Server", self.secondary, ["cluster", "is_static_ip"], as_dict=True
		)

		if secondary.cluster != primary.cluster:
			frappe.throw("Failover can only be initiated between Proxy Servers in the same Cluster")

		if not primary.is_static_ip and not secondary.is_static_ip:
			frappe.throw("Failover can only be initiated if one of the proxy server has a static IP")

		# TODO: people keep bringing up ttl - what's it's significance?
		# TODO: get recursive hash from primary & seconary and check what's the difference

		for step in self.get_steps(
			[
				self.halt_agent_jobs_on_primary,
				self.wait_for_pending_agent_jobs_to_complete,
				self.stop_replication,
				self.replicate_once_manually,
				self.attach_static_ip_to_secondary,
				self.update_dns_records_for_all_sites,
				self.route_requests_from_primary_to_secondary,
				self.move_wildcard_domains_from_primary,  # TODO: dont know the significance of this
				self.wait_for_wildcard_domains_setup,
				self.update_app_servers,
				self.forward_undelivered_jobs_to_secondary,
				self.switch_primary,
				self.add_ssh_users_for_existing_benches,
				self.remove_primary_access_and_ensure_nginx_started_in_secondary,
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
			job_id=f"proxy_failover_{self.name}",
			deduplicate=True,
		)

	@frappe.whitelist()
	def route_requests_from_primary_to_secondary(self, step=None):
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

		# TODO: trigger an ansible job to add an nginx config to route all traffic to secondary
		_update_status("Queued", step, Status.Success, job.name)

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
			.where(servers.proxy_server == self.primary)
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

	def forward_undelivered_jobs_to_secondary(self, step):
		frappe.db.set_value(
			"Agent Job",
			{"server": self.primary, "status": "Undelivered"},
			"server",
			self.secondary,
		)

		step.status = Status.Success
		step.save()

	def halt_agent_jobs_on_primary(self, step):
		frappe.db.set_value("Proxy Server", self.primary, "halt_agent_jobs", True)

		step.status = Status.Success
		step.save()

	def wait_for_pending_agent_jobs_to_complete(self, step):
		step.status = Status.Running
		step.save()

		pending_jobs = frappe.get_all(
			"Agent Job",
			fields=["name", "job_id", "status", "callback_failure_count"],
			filters={
				"status": ("in", ["Pending", "Running"]),
				"job_id": ("!=", 0),
				"server": self.primary,
			},
			order_by="job_id",
			ignore_ifnull=True,
		)

		if not pending_jobs:
			step.status = Status.Success
			step.save()
			return

		agent = Agent(self.primary, server_type="Proxy Server")
		pending_ids = [j.job_id for j in pending_jobs]
		if not (polled_jobs := poll_random_jobs(agent, pending_ids)):
			return

		handle_polled_jobs(polled_jobs, pending_jobs)

	def move_wildcard_domains_from_primary(self, step):
		domains = set(
			frappe.get_all(
				"Proxy Server Domain",
				filters={"parent": ["in", (self.primary, self.secondary)]},
				fields=["domain", "code_server"],
				as_list=True,
			)
		)

		secondary = frappe.get_doc("Proxy Server", self.secondary)
		secondary.domains = []
		for domain in domains:
			secondary.append("domains", {"domain": domain[0], "code_server": domain[1]})

		if secondary.domains:
			secondary.save()

			job = secondary.setup_wildcard_hosts()
			step.job = job.name
			step.job_type = "Agent Job"

		step.status = Status.Success
		step.save()

	def wait_for_wildcard_domains_setup(self, step):
		job = frappe.db.get_value(
			"Proxy Failover Steps",
			{
				"parent": self.name,
				"method_name": "move_wildcard_domains_from_primary",
			},
			"job",
		)

		if not job:
			step.status = Status.Skipped
			step.output = "No wildcard setup job found. Skipping wait step."
			step.save()
			return

		step.status = Status.Running

		with suppress(Exception):
			self.handle_agent_job(step, job)

	def stop_replication(self, step):
		try:
			primary_proxy = frappe.get_doc("Proxy Server", self.primary)
			ansible = Ansible(
				playbook="stop_primary_proxy_replication.yml",
				server=primary_proxy,
				user=primary_proxy._ssh_user(),
				port=primary_proxy._ssh_port(),
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			# no need to raise an error here as even if primary is down, we need to proceed
			# TODO: only raise if this fails due to some other reason

	def replicate_once_manually(self, step):
		step.status = Status.Running
		step.save()

		result = self.ansible_run(
			self.primary,
			f"rsync -aAXvz /home/frappe/agent/nginx/ frappe@{self.secondary}:/home/frappe/agent/nginx/",
		)
		if result.get("status") != "Success":
			print(result)
			step.status = Status.Failure
			step.output = "Failed to replicate nginx config to secondary"
			step.save()
			raise

		step.status = Status.Success
		step.save()

	def remove_primary_access_and_ensure_nginx_started_in_secondary(self, step):
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
			# not really that big of an issue if we couldnt remove access (if the replication was stopped properly)

	def handle_step_failure(self):
		self.error = frappe.get_traceback(with_context=True)
		self.save()

	def ansible_run(self, proxy, command):
		inventory = f"{frappe.db.get('Proxy Server', proxy, 'ip')},"
		return AnsibleAdHoc(sources=inventory).run(command, self.name)[0]

	@frappe.whitelist()
	def force_continue(self):
		self.error = None
		self.save()

		self.execute_failover_steps()
		frappe.msgprint("Failover steps re-queued from the point of failure.", alert=True)
