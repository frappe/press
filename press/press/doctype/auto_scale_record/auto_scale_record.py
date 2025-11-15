# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.runner import Ansible
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class AutoScaleRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		primary_server: DF.Link
		scale_down: DF.Check
		scale_up: DF.Check
		secondary_server: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		"""Set metadata attributes"""
		self.secondary_server = frappe.db.get_value("Server", self.primary_server, "secondary_server")

	def after_insert(self):
		"""Trigger auto scaling"""

		if self.scale_up:
			self.switch_to_secondary()

		if self.scale_down:
			self.switch_to_primary()

	def _gracefully_stop_benches_on_secondary(self) -> None:
		secondary_server: "Server" = frappe.get_cached_doc("Server", self.secondary_server)
		try:
			ansible = Ansible(
				playbook="stop_benches.yml",
				server=secondary_server,
				user=secondary_server._ssh_user(),
				port=secondary_server._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Stop Benches Exception", server=secondary_server.as_dict())

	def switch_to_secondary(self):
		"""
		Updates common site config with redis connection string and
		bench directories in all the configs.
		"""
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)
		primary_server_private_ip = frappe.db.get_value("Server", self.primary_server, "private_ip")
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")
		frappe.db.set_value("Server", self.primary_server, "scaled_up", True)

		self.setup_secondary_upstream()

		return Agent(self.secondary_server).change_bench_directory(
			redis_connection_string_ip=primary_server_private_ip,
			secondary_server_private_ip=secondary_server_private_ip,
			directory=shared_directory,
			is_primary=False,
			registry_settings={
				"url": settings.docker_registry_url,
				"username": settings.docker_registry_username,
				"password": settings.docker_registry_password,
			},
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.secondary_server,
		)

	def switch_to_primary(self) -> "AgentJob":
		"""
		Updates common site config with redis connection string and
		bench directories in all the configs.
		"""
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")

		self.setup_primary_upstream()

		return Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip="localhost",
			secondary_server_private_ip=secondary_server_private_ip,
			is_primary=True,
			directory=shared_directory,
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

	def initiate_secondary_shutdown(self) -> None:
		"""
		Initiates a shutdown of the secondary server once it is safe to do so.

		This method checks whether all "Remove Site from Upstream" jobs related to the
		secondary server have finished. These jobs must be fully completed before the
		secondary server can be shut down.

		If the secondary server's virtual machine is already stopped, the method exits
		immediately.

		Once all upstream-removal jobs are finished and the server is confirmed to be
		running, this method gracefully stops all benches on the secondary server and
		then triggers the shutdown of the virtual machine.
		"""
		virtual_machine = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")
		secondary_server_status = frappe.db.get_value("Virtual Machine", virtual_machine, "status")

		if secondary_server_status in ["Stopping", "Stopped"]:
			return

		non_terminal_states = ["Pending", "Undelivered", "Running"]
		remove_upstream_jobs = frappe.db.get_all(
			"Agent Job",
			{
				"job_type": "Remove Site from Upstream",
				"upstream": self.secondary_server,
				"status": ("IN", non_terminal_states),
			},
		)

		if remove_upstream_jobs:
			return

		current_user = frappe.session.user
		frappe.set_user("Administrator")

		self._gracefully_stop_benches_on_secondary()
		secondary_server_vm: "VirtualMachine" = frappe.get_doc("Virtual Machine", virtual_machine)
		secondary_server_vm.stop()
		frappe.db.set_value("Server", self.primary_server, "scaled_up", False)

		frappe.set_user(current_user)

	def setup_secondary_upstream(self) -> "AgentJob":
		"""Update proxy server with secondary as upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		active_sites = frappe.get_all("Site", {"server": self.primary_server}, pluck="name")

		for site in active_sites:
			agent.new_upstream_file(server=self.secondary_server, site=site)
			frappe.db.set_value("Site", site, "server", self.secondary_server)

		frappe.db.commit()  # Commit for sanity

	def setup_primary_upstream(self) -> "AgentJob":
		"""Fallback to older primary servers upstream by removing the secondary servers upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		active_sites = frappe.get_all("Site", {"server": self.secondary_server}, pluck="name")

		for site in active_sites:
			agent.new_upstream_file(server=self.primary_server, site=site)
			agent.remove_upstream_file(server=self.secondary_server, site=site)
			frappe.db.set_value("Site", site, "server", self.primary_server)

		frappe.db.commit()  # Commit for sanity
