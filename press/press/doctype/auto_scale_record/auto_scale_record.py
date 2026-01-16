# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import calendar
import contextlib
import datetime
import typing
from typing import Literal, TypedDict

import frappe
from frappe.model.document import Document
from requests.exceptions import ConnectionError, HTTPError, JSONDecodeError

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.runner import Ansible, Status, StepHandler
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import PrometheusAlertRule
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class PrometheusAlertRuleRow(TypedDict):
	expression: str


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


class AutoScaleRecord(Document, AutoScaleStepFailureHandler, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.scale_step.scale_step import ScaleStep

		action: DF.Literal["Scale Up", "Scale Down"]
		duration: DF.Time | None
		failed_validation: DF.Check
		is_automatically_triggered: DF.Check
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

	@staticmethod
	def get_list_query(query, filters: dict[str, str] | None = None, **args):
		"""Fetch the secondary server from the primary server doc"""
		AutoScaleRecord = frappe.qb.DocType("Auto Scale Record")
		secondary_server = frappe.db.get_value(
			"Server", filters.get("primary_server", None) if filters else None, "secondary_server"
		)
		query = query.where(AutoScaleRecord.secondary_server == secondary_server)

		return query.run(as_dict=True)

	def before_insert(self):
		"""Set metadata attributes"""
		self.duration = None

		if self.action == "Scale Up":
			for step in self.get_steps(
				[
					self.mark_start_time,
					self.stop_all_agent_jobs_on_primary,
					self.start_secondary_server,
					self.wait_for_secondary_server_to_start,
					# Since the secondary is stopped no jobs running on it
					self.wait_for_secondary_server_ping,
					self.remove_redis_localhost_bind,
					self.wait_for_redis_localhost_bind_removal,
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
		if not self.secondary_server:
			frappe.throw("Primary server must have a secondary server to auto scale")

	def get_doc(self, doc):
		doc.steps = self.get_steps_for_dashboard()
		doc.start_time = self.start_time
		doc.duration = self.duration
		return doc

	@dashboard_whitelist()
	def get_steps_for_dashboard(self) -> list[dict[str, str]]:
		"""Format steps for dashboard job step"""
		ret = []

		for step in self.scale_steps:
			ret.append(
				{
					"name": step.method_name,
					"status": step.status,
					"output": step.output,
					"title": step.step_name,
				}
			)

		return ret

	def mark_start_time(self, step: "ScaleStep"):
		"""Mark Autoscale Start Time"""
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
		"""Start Secondary Server"""
		step.status = Status.Running
		step.save()

		secondary_server_vm = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")
		virtual_machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", secondary_server_vm)

		if virtual_machine.status != "Running":
			virtual_machine.start()

		step.status = Status.Success
		step.save()

	def wait_for_secondary_server_to_start(self, step: "ScaleStep"):
		"""Wait For Secondary Server To Start"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		virtual_machine = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")

		self.handle_vm_status_job(step, virtual_machine=virtual_machine, expected_status="Running")

	def wait_for_secondary_server_ping(self, step: "ScaleStep"):
		"""Wait For Secondary Server Agent"""
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
		"""Update Proxy With Secondary Server Upstream"""
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
		"""Wait For Proxy Server Upstream Addition"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Update Proxy With Secondary Server Upstream",
			},
			"job",
		)

		self.handle_agent_job(step, job, poll=True)

	def switch_to_secondary(self, step: "ScaleStep"):
		"""Prepare Agent To Switch To Secondary"""
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)

		primary_server_private_ip, primary_server_cluster = frappe.db.get_value(
			"Server", self.primary_server, ["private_ip", "cluster"]
		)
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")
		cluster_repository = frappe.db.get_value("Cluster", primary_server_cluster, "repository")

		agent_job = Agent(self.secondary_server).change_bench_directory(
			redis_connection_string_ip=primary_server_private_ip,
			secondary_server_private_ip=secondary_server_private_ip,
			directory=shared_directory,
			is_primary=False,
			registry_settings={
				"url": cluster_repository
				or settings.docker_registry_url,  # Use the cluster repository if present
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
		"""Wait For Benches To Run On Shared Volume"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Prepare Agent To Switch To Secondary",
			},
			"job",
		)

		self.handle_agent_job(step, job, poll=True)

	def remove_redis_localhost_bind(self, step: "ScaleStep"):
		"""Expose Redis Of Primary Server"""
		agent_job = Agent(self.primary_server).remove_redis_localhost_bind(
			reference_doctype="Server", reference_name=self.primary_server
		)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_redis_localhost_bind_removal(self, step: "ScaleStep"):
		"""Wait For Redis To Be Exposed"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Expose Redis Of Primary Server",
			},
			"job",
		)

		self.handle_agent_job(step, job, poll=True)

	def mark_server_as_auto_scale(self, step: "ScaleStep"):
		"""Mark Server As Auto Scaled"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value("Server", self.primary_server, {"scaled_up": True, "halt_agent_jobs": False})

		# Enable monitoring on the secondary server
		frappe.db.set_value(
			"Server", self.secondary_server, {"status": "Active", "is_monitoring_disabled": False}
		)

		duration = frappe.utils.now_datetime() - frappe.db.get_value(
			"Auto Scale Record", self.name, "start_time"
		)
		frappe.db.set_value("Auto Scale Record", self.name, "duration", duration)

		emails = get_communication_info("Email", "Server Activity", "Server", self.primary_server)
		server_title = frappe.db.get_value("Server", self.primary_server, "title") or self.primary_server

		if self.is_automatically_triggered and emails:
			send_autoscale_notification(
				server_title=server_title,
				server_name=self.primary_server,
				action=self.action,
				emails=emails,
				auto_scale_name=self.name,
			)

		with contextlib.suppress(frappe.DoesNotExistError):
			# In case there is a scale down trigger setup for the server, enable it
			# since we are scaled up now
			auto_scale_trigger: PrometheusAlertRule = frappe.get_doc(
				"Prometheus Alert Rule", f"Auto Scale Down Trigger - {self.primary_server}"
			)
			# Only set it to enabled if a valid expression exists
			if auto_scale_trigger.expression:
				auto_scale_trigger.enabled = 1
				auto_scale_trigger.save()

		step.status = Status.Success
		step.save()

	# Switch to secondary steps end

	# Switch to primary steps start
	def setup_primary_upstream(self, step: "ScaleStep"):
		"""Setup Primary Upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")

		primary_upstream = frappe.db.get_value("Server", self.primary_server, "private_ip")
		agent_job = agent.proxy_remove_auto_scale_site_to_upstream(primary_upstream)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_primary_upstream_setup(self, step: "ScaleStep"):
		"""Wait For Primary Upstream Setup"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Setup Primary Upstream",
			},
			"job",
		)

		self.handle_agent_job(step, job, poll=True)

	def switch_to_primary(self, step: "ScaleStep"):
		"""Prepare Agent To Switch To Primary"""
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")

		agent_job = Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip="localhost",
			secondary_server_private_ip=secondary_server_private_ip,
			is_primary=True,
			directory=shared_directory,
			restart_benches=False,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_primary_switch(self, step: "ScaleStep"):
		"""Wait For Benches To Run On Primary"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"Scale Step",
			{
				"parent": self.name,
				"step_name": "Prepare Agent To Switch To Primary",
			},
			"job",
		)

		self.handle_agent_job(step, job, poll=True)

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
		"""Initiates A Graceful Secondary Server Shutdown"""
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
		frappe.db.set_value(
			"Server", self.secondary_server, {"halt_agent_jobs": False, "is_monitoring_disabled": True}
		)

		frappe.set_user(current_user)

		step.status = Status.Success
		step.save()

	def create_usage_record(self, step: "ScaleStep"):
		"""Create Usage Record"""
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

		emails = get_communication_info("Email", "Server Activity", "Server", self.primary_server)
		server_title = frappe.db.get_value("Server", self.primary_server, "title") or self.primary_server

		if self.is_automatically_triggered and emails:
			send_autoscale_notification(
				server_title=server_title,
				server_name=self.primary_server,
				action=self.action,
				emails=emails,
				auto_scale_name=self.name,
			)

		with contextlib.suppress(frappe.DoesNotExistError):
			# In case there is a scale down trigger setup for the server, disable it
			# since we are already scaled down
			auto_scale_trigger: PrometheusAlertRule = frappe.get_doc(
				"Prometheus Alert Rule", f"Auto Scale Down Trigger - {self.primary_server}"
			)
			if auto_scale_trigger.enabled and auto_scale_trigger.expression:
				auto_scale_trigger.enabled = 0
				auto_scale_trigger.save()

		step.status = Status.Success
		step.save()

	# Primary switch steps end

	# Agent job halt
	def stop_all_agent_jobs_on_primary(self, step: "ScaleStep"):
		"""Stop All Agent Jobs On the Primary Server"""
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
		"""Stop All Agent Jobs On the Secondary Server"""
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
			queue="auto-scale",
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


def _is_scale_up_colliding_with_a_existing_scaling_window(
	primary_server: str, scale_up_time: datetime.datetime
):
	AutoScaleRecord = frappe.qb.DocType("Auto Scale Record")

	last_scale_up = (
		frappe.qb.from_(AutoScaleRecord)
		.select(AutoScaleRecord.scheduled_time)
		.where(AutoScaleRecord.primary_server == primary_server)
		.where(AutoScaleRecord.action == "Scale Up")
		.where(AutoScaleRecord.scheduled_time <= scale_up_time)
		.where(AutoScaleRecord.status == "Scheduled")
		.orderby(AutoScaleRecord.scheduled_time, order=frappe.qb.desc)
		.limit(1)
		.run(pluck=True)
	)
	next_scale_down = None
	if last_scale_up:
		next_scale_down = (
			frappe.qb.from_(AutoScaleRecord)
			.select(AutoScaleRecord.scheduled_time)
			.where(AutoScaleRecord.primary_server == primary_server)
			.where(AutoScaleRecord.action == "Scale Down")
			.where(AutoScaleRecord.status == "Scheduled")
			.where(AutoScaleRecord.scheduled_time >= last_scale_up[0])
			.orderby(AutoScaleRecord.scheduled_time)
			.limit(1)
			.run(pluck=True)
		)

	# If we find a scale window we can check if the scale up is between that window
	if last_scale_up and next_scale_down and last_scale_up[0] <= scale_up_time <= next_scale_down[0]:
		frappe.throw(
			f"Scale Up at {scale_up_time} conflicts with an existing scale window "
			f"({last_scale_up[0]} - {next_scale_down[0]})"
		)


def _is_scale_down_colliding_with_a_existing_scaling_window(
	primary_server: str, scale_down_time: datetime.datetime
):
	AutoScaleRecord = frappe.qb.DocType("Auto Scale Record")

	next_scale_down = (
		frappe.qb.from_(AutoScaleRecord)
		.select(AutoScaleRecord.scheduled_time)
		.where(AutoScaleRecord.primary_server == primary_server)
		.where(AutoScaleRecord.action == "Scale Down")
		.where(
			AutoScaleRecord.scheduled_time >= scale_down_time
		)  # There is no window between scale down and up
		.where(AutoScaleRecord.status == "Scheduled")
		.orderby(AutoScaleRecord.scheduled_time)
		.limit(1)
		.run(pluck=True)
	)
	last_scale_up = None
	if next_scale_down:
		last_scale_up = (
			frappe.qb.from_(AutoScaleRecord)
			.select(AutoScaleRecord.scheduled_time)
			.where(AutoScaleRecord.primary_server == primary_server)
			.where(AutoScaleRecord.action == "Scale Up")
			.where(AutoScaleRecord.scheduled_time <= next_scale_down[0])
			.where(AutoScaleRecord.status == "Scheduled")
			.orderby(AutoScaleRecord.scheduled_time, order=frappe.qb.desc)
			.limit(1)
			.run(pluck=True)
		)

	# If we find a scale window we can check if the scale up is between that window
	if last_scale_up and next_scale_down and last_scale_up[0] <= scale_down_time <= next_scale_down[0]:
		frappe.throw(
			f"Scale Down at {scale_down_time} conflicts with an existing scale window "
			f"({last_scale_up[0]} - {next_scale_down[0]})"
		)


def validate_scaling_schedule(
	name: str, scale_up_time: datetime.datetime, scale_down_time: datetime.datetime
):
	"""Throw if the scaling schedule violates any of these conditions"""

	now = frappe.utils.now_datetime()
	if (
		scale_down_time <= now
		or scale_up_time <= now
		or scale_down_time <= now
		or scale_down_time <= scale_up_time
	):
		frappe.throw(
			"Scale down time must be in the future & scale down must be after a scale up",
			frappe.ValidationError,
		)

	# Check existing scales with same schedule time
	existing_scheduled_scales = frappe.db.get_value(
		"Auto Scale Record",
		{
			"primary_server": name,
			"status": "Scheduled",
			"scheduled_time": ("IN", [scale_up_time, scale_down_time]),
		},
	)

	if existing_scheduled_scales:
		frappe.throw("Scale is already scheduled for this time", frappe.ValidationError)

	_is_scale_up_colliding_with_a_existing_scaling_window(name, scale_up_time)
	_is_scale_down_colliding_with_a_existing_scaling_window(name, scale_down_time)


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


def is_secondary_ready_for_scale_down(server: Server) -> bool:
	"""Check if the secondary server is ready for scaling down based on CPU or Memory usage."""
	from press.api.server import get_cpu_and_memory_usage

	scale_down_thresholds = frappe.db.get_values(
		"Auto Scale Trigger",
		{"parent": server.name, "action": "Scale Down"},
		["metric", "threshold"],
		as_dict=True,
	)

	if not scale_down_thresholds:
		return True

	secondary_server_usage = get_cpu_and_memory_usage(server.secondary_server)
	secondary_server_cpu_usage = secondary_server_usage["vcpu"] * 100
	secondary_server_memory_usage = secondary_server_usage["memory"] * 100

	for config in scale_down_thresholds:
		if (config["metric"] == "CPU") and (secondary_server_cpu_usage < config["threshold"]):
			return True

		if (config["metric"] == "Memory") and (secondary_server_memory_usage < config["threshold"]):
			return True

	return False


def _get_query_map(instance_name: str, time_range: str = "4m"):
	return {
		"CPU": f"""
		(
			1 - avg by (instance) (
				rate(node_cpu_seconds_total{{instance="{instance_name}", job="node", mode="idle"}}[{time_range}])
			)
		) * 100
		""".strip(),
		"Memory": f"""
		(
			1 -
			(
				avg_over_time(node_memory_MemAvailable_bytes{{instance="{instance_name}", job="node"}}[{time_range}])
				/
				avg_over_time(node_memory_MemTotal_bytes{{instance="{instance_name}", job="node"}}[{time_range}])
			)
		) * 100
		""".strip(),
	}


def update_or_delete_prometheus_rule_for_scaling(
	instance_name: str,
	metric: Literal["CPU", "Memory"],
	action: Literal["Scale Up", "Scale Down"],
) -> None:
	rule_name = f"Auto {action} Trigger - {instance_name}"
	existing: PrometheusAlertRule | None
	try:
		existing = frappe.get_doc(
			"Prometheus Alert Rule",
			rule_name,
			for_update=True,
		)
	except frappe.DoesNotExistError:
		existing = None

	if not existing:
		return

	query_map = _get_query_map(instance_name)
	base_query = query_map[metric]
	expression = existing.expression or ""  # Ideally we should have an expression here

	parts = [p.strip() for p in expression.split(" OR ") if p.strip()]
	parts = [p for p in parts if base_query not in p]

	if not parts:
		# This was the only expression present don't delete just disable
		existing.enabled = False
		existing.expression = ""
	else:
		new_expression = " OR ".join(parts)  # Part without the removed metric
		existing.expression = new_expression

	existing.save()


def _should_enable_trigger(instance_name: str, action: Literal["Scale Up", "Scale Down"]) -> bool:
	"""Only enable scale down trigger if server is already scaled up"""
	if action == "Scale Up":
		return True

	scaled_up = frappe.db.get_value("Server", instance_name, "scaled_up")
	return bool(scaled_up)


def create_prometheus_rule_for_scaling(
	instance_name: str,
	metric: Literal["CPU", "Memory"],
	threshold: float,
	action: Literal["Scale Up", "Scale Down"],
) -> None:
	"""Create or update a Prometheus autoscaling alert rule."""
	query_map = _get_query_map(instance_name)

	base_query = query_map[metric]
	query_with_threshold = f"({base_query} {'>' if action == 'Scale Up' else '<'} {threshold})"

	rule_name = f"Auto {action} Trigger - {instance_name}"
	existing: PrometheusAlertRule | None

	try:
		existing = frappe.get_doc(
			"Prometheus Alert Rule",
			rule_name,
			for_update=True,
		)
	except frappe.DoesNotExistError:
		existing = None

	if existing:
		expression = existing.expression or ""

		parts = [p.strip() for p in expression.split(" OR ") if p.strip()]
		parts = [p for p in parts if base_query not in p]

		# Add updated metric expression
		parts.append(query_with_threshold)

		new_expression = " OR ".join(parts)

		existing.expression = new_expression
		existing.enabled = _should_enable_trigger(instance_name, action)
		existing.save()  # Need to call this to allow on_update to trigger

	else:
		doc = frappe.get_doc(
			{
				"doctype": "Prometheus Alert Rule",
				"name": rule_name,
				"description": f"Autoscale trigger for {instance_name}",
				"expression": query_with_threshold,
				"enabled": _should_enable_trigger(instance_name, action),
				"for": "5m",
				"repeat_interval": "1h"
				if action == "Scale Up"
				else "5m",  # Quicker checks for scaling down [Price sensitive?]
				"press_job_type": "Auto Scale Up Application Server"
				if action == "Scale Up"
				else "Auto Scale Down Application Server",
			}
		)
		doc.insert()


def send_autoscale_notification(
	server_title: str,
	server_name: str,
	action: Literal["Scale Up", "Scale Down"],
	emails: list[str],
	auto_scale_name: str,
):
	frappe.sendmail(
		recipients=emails,
		subject=f"Autoscale - {server_title}",
		template="auto_scale_notification",
		args={
			"message": f"Automatic {action} triggered for server {server_title}",
			"link": f"dashboard/servers/{server_name}/auto-scale-steps/{auto_scale_name}",
		},
	)
