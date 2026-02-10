# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from contextlib import suppress
from itertools import groupby

import frappe
from frappe.model.document import Document

from press.press.doctype.agent_job.agent_job import Agent, handle_polled_jobs, poll_random_jobs
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
from press.runner import Ansible, Status, StepHandler
from press.utils import servers_using_alternative_port_for_communication


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
		routing_steps = []

		primary = frappe.db.get_value("Proxy Server", self.primary, ["cluster", "is_static_ip"], as_dict=True)
		secondary = frappe.db.get_value(
			"Proxy Server", self.secondary, ["cluster", "is_static_ip"], as_dict=True
		)

		if secondary.cluster != primary.cluster:
			frappe.throw("Failover can only be initiated between Proxy Servers in the same cluster")

		if (not primary.is_static_ip and not secondary.is_static_ip) or (
			primary.is_static_ip and secondary.is_static_ip
		):
			frappe.throw("Failover can only be initiated if one of the proxy server has a static ip")

		if not primary.is_static_ip:
			routing_steps.extend(
				[self.build_nginx_with_stream_module, self.route_requests_from_primary_to_secondary]
			)

		for step in self.get_steps(
			[
				self.halt_agent_jobs_on_primary,
				self.wait_for_pending_agent_jobs_to_complete,
				self.stop_replication,
				self.replicate_once_manually,
				self.use_secondary_as_proxy_for_agent_and_metrics,
				self.move_wildcard_domains_from_primary,
				self.wait_for_wildcard_domains_setup,
				self.attach_static_ip_to_secondary,
				self.update_dns_records_for_all_sites,
				self.update_app_servers,
				self.forward_undelivered_jobs_to_secondary,
				*routing_steps,
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

	def route_requests_from_primary_to_secondary(self, step=None):
		"""Route all traffic from primary to secondary proxy server"""
		step.status = Status.Running
		step.save()

		primary_proxy = frappe.get_doc("Proxy Server", self.primary)

		try:
			ansible = Ansible(
				playbook="nginx_conf_changes_for_tcp_streaming.yml",
				server=primary_proxy,
				user=primary_proxy._ssh_user(),
				port=primary_proxy._ssh_port(),
				variables={"secondary_proxy": self.secondary},
			)
			ansible_play = ansible.run()
			if ansible_play.status != Status.Success:
				raise Exception("Failed making changes for nginx tcp streaming")
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			return

		cluster = frappe.get_doc("Cluster", primary_proxy.cluster)
		if cluster.cloud_provider == "AWS EC2":
			client = cluster.get_aws_client()
			client.authorize_security_group_ingress(
				GroupId=cluster.proxy_security_group_id,
				IpPermissions=[
					{
						"FromPort": 8443,
						"IpProtocol": "tcp",
						"IpRanges": [
							{
								"CidrIp": "0.0.0.0/0",
								"Description": "HTTPS Alternative Port for Agent and Prometheus",
							}
						],
						"ToPort": 8443,
					},
				],
			)

		if self.primary not in (alt_port_servers := servers_using_alternative_port_for_communication()):
			alt_port_servers.append(self.primary)
			frappe.db.set_single_value(
				"Press Settings",
				"servers_using_alternative_http_port_for_communication",
				"\n".join(alt_port_servers),
			)

		step.status = Status.Success
		step.save()

	def build_nginx_with_stream_module(self, step):
		primary_proxy = frappe.get_doc("Proxy Server", self.primary)
		try:
			frappe.db.set_value("Proxy Server", self.primary, "status", "Installing")
			ansible = Ansible(
				playbook="build_nginx_with_stream.yml",
				server=primary_proxy,
				user=primary_proxy._ssh_user(),
				port=primary_proxy._ssh_port(),
			)
			self.handle_ansible_play(step, ansible)
			frappe.db.set_value("Proxy Server", self.primary, "status", "Active")
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			frappe.db.set_value("Proxy Server", self.primary, "status", "Broken")
			raise

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
			domain.update_dns_records_for_sites([site.name for site in sites], self.secondary, batch_size=200)

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

	def use_secondary_as_proxy_for_agent_and_metrics(self, step):
		if frappe.db.get_value("Proxy Server", self.primary, "use_as_proxy_for_agent_and_metrics"):
			frappe.db.set_value(
				"Proxy Server",
				self.secondary,
				{"use_as_proxy_for_agent_and_metrics": 1},
			)

			frappe.db.set_value(
				"Proxy Server",
				self.primary,
				{"use_as_proxy_for_agent_and_metrics": 0},
			)

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
		from frappe.utils import add_to_date

		threshold = add_to_date(None, days=-2)
		frappe.db.set_value(
			"Agent Job",
			{
				"server": self.primary,
				"status": "Undelivered",
				"creation": (">=", threshold),
			},  # only last 2 days
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
		if step.status == Status.Pending:
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
		step.status = Status.Running
		step.save()

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
		if step.status == Status.Pending:
			step.status = Status.Running
			step.save()

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
			raise

	def replicate_once_manually(self, step):
		result = AnsibleAdHoc(sources=[{"name": self.primary}]).run(
			f"rsync -aAXvz /home/frappe/agent/nginx/ frappe@{frappe.db.get_value('Proxy Server', self.secondary, 'private_ip')}:/home/frappe/agent/nginx/",
			raw_params=True,
			become_user="frappe",
		)[0]

		if result.get("status") != "Success":
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
			# not really that big of an issue if we couldn't remove access (if the replication was stopped properly)

	def handle_step_failure(self):
		self.error = frappe.get_traceback(with_context=True)
		self.save()

	@frappe.whitelist()
	def force_continue(self):
		self.error = None

		for step in self.failover_steps:
			if step.status == "Failure":
				step.status = "Pending"

		self.save()

		self.execute_failover_steps()
		frappe.msgprint("Failover steps re-queued.", alert=True)


def reduce_ttl_of_sites(primary_proxy_name, secondary_proxy_name):
	primary_proxy = frappe.db.get_value(
		"Proxy Server", primary_proxy_name, ["name", "domain", "ip", "is_static_ip"], as_dict=True
	)
	if primary_proxy.is_static_ip:
		# reduce ttl for proxy domain A record
		secondary_proxy = frappe.db.get_value(
			"Proxy Server", secondary_proxy_name, ["name", "domain", "ip"], as_dict=True
		)
		for proxy in (primary_proxy, secondary_proxy):
			domain = frappe.get_doc("Root Domain", proxy.domain)
			changes = [
				{
					"Action": "UPSERT",
					"ResourceRecordSet": {
						"Name": proxy.name,
						"Type": "A",
						"TTL": 60,
						"ResourceRecords": [
							{"Value": proxy.ip},
						],
					},
				}
			]

			domain.boto3_client.change_resource_record_sets(
				ChangeBatch={"Changes": changes}, HostedZoneId=domain.hosted_zone
			)

	# reduce ttl for all sites using this proxy
	servers = frappe.get_all("Server", {"proxy_server": primary_proxy.name}, pluck="name")
	sites_domains = frappe.get_all(
		"Site",
		{"status": ("!=", "Archived"), "server": ("in", servers)},
		["name", "domain"],
	)
	for domain_name, sites in groupby(sites_domains, lambda x: x["domain"]):
		domain = frappe.get_doc("Root Domain", domain_name)
		domain.update_dns_records_for_sites(
			[site.name for site in sites], primary_proxy.name, ttl=60, batch_size=200
		)
