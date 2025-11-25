# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.runner import Ansible


class ProxyFailover(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		primary: DF.Link
		secondary: DF.Link
	# end: auto-generated types

	def before_insert(self):
		self.status = "Queued"

	def after_insert(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_trigger_failover",
			queue="long",
			timeout=3600,
			at_front_when_starved=True,
			enqueue_after_commit=True,
		)

	# TODO: add a child table with steps and update them?
	def update_step(self):
		pass

	def _trigger_failover(self):
		frappe.db.set_value("Proxy Failover", self.name, "status", "In Progress")
		frappe.db.commit()

		# take both cases - primary up and primary down
		# assume secondary to be up

		# TODO: we'll also need to make sure secondary has the latest conf
		# one easy way is to validate the last X add site to upstream entries in agent job (which succeeded in primary)
		# and cross check it with secondary
		try:
			primary_proxy = frappe.get_doc("Proxy Server", self.primary)
			if not primary_proxy.is_static_ip:
				# TODO: attach the secondary public ip to domain name of primary

				try:
					primary_proxy.ping_agent()
				except Exception:
					# TODO: trigger an agent job to add an nginx config to route all traffic to secondary
					pass


			self.update_dns_records_for_all_sites()
			self.stop_primary_agent_and_replication(primary_proxy)
			self.update_app_servers()
			self.move_wildcard_domains_from_primary()
			self.remove_primary_access_and_start_nginx_in_secondary()
			self.forward_jobs_to_secondary()

			# transfer the primary's static ip to secondary
			if primary_proxy.is_static_ip:
				self.attach_static_ip_to_secondary()

			self.switch_primary()

			if not primary_proxy.is_static_ip:
				# send a mail to people to update their A records or switch to CNAME records
				self.send_failover_email()

			self.add_ssh_users_for_existing_benches()
		except Exception:
			# TODO: we need to mark the proxies broken as well?
			frappe.db.set_value("Proxy Failover", self.name, "status", "Failed")
			self.log_error("Proxy Server Failover Exception")

	def attach_static_ip_to_secondary(self):
		primary_vm = frappe.get_doc(
			"Virtual Machine", frappe.db.get_value("Proxy Server", self.primary, "virtual_machine")
		)
		secondary_vm = frappe.get_doc(
			"Virtual Machine", frappe.db.get_value("Proxy Server", self.secondary, "virtual_machine")
		)

		static_ip = primary_vm.public_ip_address  # assuming this is the static ip
		primary_vm.detach_static_ip()
		secondary_vm.attach_static_ip(static_ip)

	def update_dns_records_for_all_sites(self):
		from itertools import groupby

		servers = frappe.get_all("Server", {"proxy_server": self.primary}, pluck="name")
		sites_domains = frappe.get_all(
			"Site",
			{"status": ("!=", "Archived"), "server": ("in", servers)},
			["name", "domain"],
		)
		for domain_name, sites in groupby(sites_domains, lambda x: x["domain"]):
			domain = frappe.get_doc("Root Domain", domain_name)
			domain.update_dns_records_for_sites([site.name for site in sites], self.secondary)

	def add_ssh_users_for_existing_benches(self):
		if not frappe.db.get_value("Proxy Server", self.secondary, "is_ssh_proxy_setup"):
			return

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

	def update_app_servers(self):
		frappe.db.set_value("Server", {"proxy_server": self.primary}, "proxy_server", self.secondary)

	def switch_primary(self):
		frappe.db.set_value(
			"Proxy Server",
			self.secondary,
			{"is_primary": True, "is_replication_setup": False, "primary": None},
		)

	def forward_jobs_to_secondary(self):
		frappe.db.set_value(
			"Agent Job",
			{"server": self.primary, "status": "Undelivered"},
			"server",
			self.secondary,
		)

	def move_wildcard_domains_from_primary(self):
		frappe.db.set_value(
			"Proxy Server Domain",
			{"parent": self.primary},
			"parent",
			self.secondary,
		)

	def stop_primary_agent_and_replication(self, primary_proxy=None):
		primary = primary_proxy or frappe.get_doc("Proxy Server", self.primary)
		try:
			ansible = Ansible(
				playbook="failover_prepare_primary_proxy.yml",
				server=primary,
				user=primary._ssh_user(),
				port=primary._ssh_port(),
			)
			ansible.run()
		except Exception:
			pass  # may be unreachable

	def remove_primary_access_and_start_nginx_in_secondary(self):
		secondary_proxy = frappe.get_doc("Proxy Server", self.secondary)
		ansible = Ansible(
			playbook="failover_up_secondary_proxy.yml",
			server=secondary_proxy,
			user=secondary_proxy._ssh_user(),
			port=secondary_proxy._ssh_port(),
			variables={
				"primary_public_key": frappe.db.get_value("Proxy Server", self.primary, "frappe_public_key")
			},
		)
		ansible.run()

	def send_failover_email(self):
		pass
