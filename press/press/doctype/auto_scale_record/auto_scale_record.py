# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.runner import Ansible, Status, StepHandler
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class AutoScaleRecord(Document, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.scale_step.scale_step import ScaleStep

		primary_server: DF.Link
		scale_down: DF.Check
		scale_steps: DF.Table[ScaleStep]
		scale_up: DF.Check
		secondary_server: DF.Link | None
		status: DF.Literal["Pending", "Running", "Failure", "Success"]
	# end: auto-generated types

	def before_insert(self):
		"""Set metadata attributes"""
		if self.scale_up:
			for step in self.get_steps(
				[
					self.start_secondary_server,
					self.wait_for_secondary_server_to_start,
					self.setup_secondary_upstream,
					self.wait_for_secondary_upstream,
					self.switch_to_secondary,
					self.wait_for_switch_to_secondary,
					self.mark_server_as_auto_scale,
				]
			):
				self.append("scale_steps", step)

		else:
			for step in self.get_steps(
				[
					self.setup_primary_upstream,
					self.wait_for_primary_upstream,
					self.switch_to_primary,
					self.wait_for_primary_switch,
					self.initiate_secondary_shutdown,
				]
			):
				self.append("scale_steps", step)

		self.secondary_server = frappe.db.get_value("Server", self.primary_server, "secondary_server")

	# Steps to switch to secondary
	def start_secondary_server(self, step: "ScaleStep"):
		"""Start secondary server"""
		step.status = Status.Running
		step.save()

		secondary_server_vm = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")
		virtual_machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", secondary_server_vm)

		if virtual_machine.status != "Running":
			virtual_machine.start()

		step.status = Status.Success
		step.save()

	def wait_for_secondary_server_to_start(self, step: "ScaleStep"):
		"""Wait for secondary server to starts"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		virtual_machine = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")

		self.handle_vm_status_job(step, virtual_machine=virtual_machine, expected_status="Running")

	def setup_secondary_upstream(self, step: "ScaleStep"):
		"""Update proxy server with secondary as upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		active_sites = frappe.get_all("Site", {"server": self.primary_server}, pluck="name")

		agent_job = agent.new_upstream_file(server=self.secondary_server, site=active_sites)
		frappe.db.set_value("Site", {"name": ("IN", active_sites)}, "server", self.secondary_server)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_secondary_upstream(self, step: "ScaleStep"):
		"""Wait for secondary upstream to be added"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Update proxy server with secondary as upstream",
			},
			"job",
		)

		self.handle_agent_job(step, job)

	def switch_to_secondary(self, step: "ScaleStep"):
		"""Prepare agent for switch to secondary"""
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)
		primary_server_private_ip = frappe.db.get_value("Server", self.primary_server, "private_ip")
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")

		agent_job = Agent(self.secondary_server).change_bench_directory(
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

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_switch_to_secondary(self, step: "ScaleStep"):
		"""Wait for benches to run on shared volume"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Prepare agent for switch to secondary",
			},
			"job",
		)

		self.handle_agent_job(step, job)

	def mark_server_as_auto_scale(self, step: "ScaleStep"):
		"""Mark server as ready to auto scale"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value("Server", self.primary_server, "scaled_up", True)

		step.status = Status.Success
		step.save()

	# Switch to secondary steps end

	# Switch to primary steps start
	def setup_primary_upstream(self, step: "ScaleStep"):
		"""Setup up primary upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		active_sites = frappe.get_all("Site", {"server": self.secondary_server}, pluck="name")

		agent_job = agent.new_upstream_file(server=self.primary_server, site=active_sites)

		# Since this will be checked when trying to shutdown the server we can fire and forget
		for site in active_sites:
			agent.remove_upstream_file(server=self.secondary_server, site=site)

		frappe.db.set_value("Site", {"name": ("IN", active_sites)}, "server", self.primary_server)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_primary_upstream(self, step: "ScaleStep"):
		"""Wait for primary upstream to be added"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Setup up primary upstream",
			},
			"job",
		)

		self.handle_agent_job(step, job)

	def switch_to_primary(self, step: "ScaleStep"):
		"""Switch to primary server"""
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")

		agent_job = Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip="localhost",
			secondary_server_private_ip=secondary_server_private_ip,
			is_primary=True,
			directory=shared_directory,
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_primary_switch(self, step: "ScaleStep"):
		"""Wait for switch to primary server"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Switch to primary server",
			},
			"job",
		)

		self.handle_agent_job(step, job)

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

	def initiate_secondary_shutdown(self, step: "ScaleStep"):
		"""Initiates a shutdown of the secondary server once it is safe to do so."""
		# This method checks whether all "Remove Site from Upstream" jobs related to the
		# secondary server have finished. These jobs must be fully completed before the
		# secondary server can be shut down.

		# If the secondary server's virtual machine is already stopped, the method exits
		# immediately.

		# Once all upstream-removal jobs are finished and the server is confirmed to be
		# running, this method gracefully stops all benches on the secondary server and
		# then triggers the shutdown of the virtual machine.

		step.status = Status.Running
		step.is_waiting = True
		step.save()

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
			step.attempt = 1 if not step.attempt else step.attempt + 1
			step.save()
			return

		current_user = frappe.session.user
		frappe.set_user("Administrator")

		self._gracefully_stop_benches_on_secondary()
		secondary_server_vm: "VirtualMachine" = frappe.get_doc("Virtual Machine", virtual_machine)
		secondary_server_vm.stop()
		frappe.db.set_value(
			"Server", self.primary_server, "scaled_up", False
		)  # Once the secondary server has stopped

		frappe.set_user(current_user)

		step.status = Status.Success
		step.save()

	# Primary switch steps end

	def execute_mount_steps(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_execute_steps",
			steps=self.scale_steps,
			timeout=18000,
			at_front=True,
			queue="long",
			enqueue_after_commit=True,
		)

	def after_insert(self):
		self.execute_mount_steps()
