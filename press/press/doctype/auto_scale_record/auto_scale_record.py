# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import calendar
import datetime
import typing

import frappe
from frappe.model.document import Document
from requests.exceptions import ConnectionError, HTTPError, JSONDecodeError

from press.agent import Agent
from press.runner import Ansible, Status, StepHandler
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class AutoScaleStepFailureHandler:
	def handle_step_failure(self):
		team = frappe.db.get_value("Server", self.primary_server, "team")
		press_notification = frappe.get_doc(
			{
				"doctype": "Press Notification",
				"team": team,
				"type": "Auto Scale",
				"document_type": self.doctype,
				"document_name": self.name,
				"class": "Error",
				"traceback": frappe.get_traceback(with_context=False),
				"message": "Error occurred during auto scale",
			}
		)
		press_notification.insert()
		frappe.db.commit()


class AutoScaleRecord(Document, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.scale_step.scale_step import ScaleStep

		action: DF.Literal["Scale Up", "Scale Down"]
		duration: DF.Time | None
		failed_validation: DF.Check
		primary_server: DF.Link
		scale_steps: DF.Table[ScaleStep]
		scheduled_time: DF.Datetime | None
		secondary_server: DF.Link | None
		start_time: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Failure", "Success", "Scheduled"]
	# end: auto-generated types

	dashboard_fields = (
		"secondary_server",
		"action",
		"created_at",
		"modified_at",
		"status",
		"scheduled_time",
		"duration",
	)

	def before_insert(self):
		"""Set metadata attributes"""
		self.duration = None

		if self.action == "Scale Up":
			for step in self.get_steps(
				[
					self.mark_start_time,
					self.start_secondary_server,
					self.wait_for_secondary_server_to_start,
					# Since the secondary is stopped no jobs running on it
					self.stop_all_agent_jobs_on_primary,
					self.wait_for_secondary_server_ping,
					self.switch_to_secondary,
					self.wait_for_switch_to_secondary,
					self.setup_secondary_upstream,
					self.wait_for_secondary_upstream,
					self.mark_server_as_auto_scale,
				]
			):
				self.append("scale_steps", step)

		else:
			for step in self.get_steps(
				[
					# There could be jobs running on both primary and secondary
					self.mark_start_time,
					self.stop_all_agent_jobs_on_primary,
					self.stop_all_agent_jobs_on_secondary,
					self.switch_to_primary,
					self.wait_for_primary_switch,
					self.setup_primary_upstream,
					self.wait_for_primary_upstream_setup,
					self.initiate_secondary_shutdown,
					self.create_usage_record,
				]
			):
				self.append("scale_steps", step)

		self.secondary_server = frappe.db.get_value("Server", self.primary_server, "secondary_server")

	def mark_start_time(self, step: "ScaleStep"):
		"""Mark autoscale start time"""
		# This function is required since scale up and scale down share methods
		# We don't want a function to accidentally override the start time
		step.status = Status.Running
		step.save()

		frappe.db.set_value(
			"Auto Scale Record", self.name, "start_time", frappe.utils.now()
		)  # Set start stime

		step.status = Status.Success
		step.save()

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

	def wait_for_secondary_server_ping(self, step: "ScaleStep"):
		"""Wait for secondary server to respond to agent pings"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		try:
			Agent(self.secondary_server).ping()
		except (HTTPError, ConnectionError, JSONDecodeError):
			step.attempt = 1 if not step.attempt else step.attempt + 1
			step.save()
			return

		step.status = Status.Success
		step.save()

	def setup_secondary_upstream(self, step: "ScaleStep"):
		"""Update proxy server with secondary as upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		primary_server_private_ip = frappe.db.get_value("Server", self.primary_server, "private_ip")
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")

		has_same_plan = frappe.db.get_value("Server", self.primary_server, "plan") == frappe.db.get_value(
			"Server", self.secondary_server, "plan"
		)

		# https://nginx.org/en/docs/http/load_balancing.html
		agent_job = agent.proxy_add_auto_scale_site_to_upstream(
			primary_server_private_ip,
			[
				{secondary_server_private_ip: 1 if has_same_plan else 3}
			],  # Since we allow users to setup a secondary server with the same plan
			# we will divide the load between the servers equally if they have the same plan
		)

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

		frappe.db.set_value("Server", self.primary_server, {"scaled_up": True, "halt_agent_jobs": False})
		duration = frappe.utils.now_datetime() - frappe.db.get_value(
			"Auto Scale Record", self.name, "start_time"
		)
		frappe.db.set_value("Auto Scale Record", self.name, "duration", duration)

		step.status = Status.Success
		step.save()

	# Switch to secondary steps end

	# Switch to primary steps start
	def setup_primary_upstream(self, step: "ScaleStep"):
		"""Setup up primary upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")

		primary_upstream = frappe.db.get_value("Server", self.primary_server, "private_ip")
		agent_job = agent.proxy_remove_auto_scale_site_to_upstream(primary_upstream)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_primary_upstream_setup(self, step: "ScaleStep"):
		"""Wait for primary upstream setup"""
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

		current_user = frappe.session.user
		frappe.set_user("Administrator")

		self._gracefully_stop_benches_on_secondary()
		secondary_server_vm: "VirtualMachine" = frappe.get_doc("Virtual Machine", virtual_machine)
		secondary_server_vm.stop()

		frappe.db.set_value(
			"Server", self.primary_server, {"scaled_up": False, "halt_agent_jobs": False}
		)  # Once the secondary server has stopped
		frappe.db.set_value("Server", self.secondary_server, "halt_agent_jobs", False)

		frappe.set_user(current_user)

		step.status = Status.Success
		step.save()

	def create_usage_record(self, step: "ScaleStep"):
		"""Create a usage when a scale down is completed"""
		step.status = Status.Running
		step.save()

		secondary_server_team, secondary_server_plan = frappe.db.get_value(
			"Server", self.secondary_server, ["team", "plan"]
		)

		secondary_server_hourly_price_with_discount = calculate_secondary_server_price(
			secondary_server_team, secondary_server_plan
		)

		usage_record = frappe.get_doc(
			doctype="Usage Record",
			team=secondary_server_team,
			document_type="Server",
			document_name=self.secondary_server,
			plan_type="Server Plan",
			amount=secondary_server_hourly_price_with_discount,
			plan=secondary_server_plan,
			date=frappe.utils.now_datetime(),
			subscription=frappe.db.get_value(
				"Subscription",
				{
					"document_type": "Server",
					"document_name": self.secondary_server,
				},
			),
			interval="Hourly",
			site=None,
		)
		usage_record.insert()
		usage_record.submit()

		duration = frappe.utils.now_datetime() - frappe.db.get_value(
			"Auto Scale Record", self.name, "start_time"
		)
		frappe.db.set_value("Auto Scale Record", self.name, "duration", duration)

		step.status = Status.Success
		step.save()

	# Primary switch steps end

	# Agent job halt
	def stop_all_agent_jobs_on_primary(self, step: "ScaleStep"):
		"""Stop all other running agent jobs on the primary server"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value("Server", self.primary_server, "halt_agent_jobs", True)
		frappe.db.commit()  # Need immediate effect

		primary_server: "Server" = frappe.get_doc("Server", self.primary_server)

		try:
			ansible = Ansible(
				playbook="restart_agent_workers.yml",
				server=primary_server,
				user=primary_server._ssh_user(),
				port=primary_server._ssh_port(),
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def stop_all_agent_jobs_on_secondary(self, step: "ScaleStep"):
		"""Stop all other running agent jobs on the secondary server"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value("Server", self.secondary_server, "halt_agent_jobs", True)
		frappe.db.commit()  # Need immediate effect

		secondary_server: "Server" = frappe.get_doc("Server", self.secondary_server)

		try:
			ansible = Ansible(
				playbook="restart_agent_workers.yml",
				server=secondary_server,
				user=secondary_server._ssh_user(),
				port=secondary_server._ssh_port(),
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def execute_scale_steps(self):
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
		if self.status != "Scheduled":
			self.execute_scale_steps()

	@frappe.whitelist()
	def force_continue(self):
		self.execute_scale_steps()


def create_autoscale_failure_notification(team: str, name: str, exc: str):
	press_notification = frappe.get_doc(
		{
			"doctype": "Press Notification",
			"team": team,
			"type": "Auto Scale",
			"document_type": "Auto Scale Record",
			"document_name": name,
			"class": "Error",
			"traceback": exc,
			"message": "Error occurred during auto scale",
		}
	)
	press_notification.insert()


def validate_scheduled_autoscale(primary_server: str) -> None:
	"""Throw if invalid auto scale schedule"""
	server: "Server" = frappe.get_doc("Server", primary_server)
	server.validate_scale()


def run_scheduled_scale_records():
	"""Run 5 scale scheduled scale records at a time"""
	scale_records = frappe.get_all(
		"Auto Scale Record",
		{
			"status": "Scheduled",
			"scheduled_time": ("<=", frappe.utils.now_datetime()),
		},
		pluck="name",
		limit=5,
	)
	for record in scale_records:
		auto_scale_record: AutoScaleRecord = frappe.get_doc("Auto Scale Record", record)
		try:
			validate_scheduled_autoscale(primary_server=auto_scale_record.primary_server)
			auto_scale_record.execute_scale_steps()  # Will take the status to running directly bypassing after insert
		except frappe.ValidationError as e:
			frappe.db.set_value(
				"Auto Scale Record", auto_scale_record.name, {"status": "Failure", "failed_validation": True}
			)
			create_autoscale_failure_notification(
				exc=e,
				name=auto_scale_record.name,
				team=frappe.db.get_value("Server", auto_scale_record.primary_server, "team"),
			)

		frappe.db.commit()


def calculate_secondary_server_price(team: str, secondary_server_plan: str) -> float:
	"""Calculate secondary server proice with a discount"""
	is_inr = frappe.db.get_value("Team", team, "currency") == "INR"
	price_field = "price_inr" if is_inr else "price_usd"

	server_price = frappe.db.get_value("Server Plan", secondary_server_plan, price_field)
	autoscale_discount = frappe.db.get_single_value("Press Settings", "autoscale_discount")
	server_price_with_discount = server_price * autoscale_discount

	_, days_in_this_month = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)
	return round(server_price_with_discount / days_in_this_month / 24, 2)
