# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import typing

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.auto_scale_record.auto_scale_record import AutoScaleStepFailureHandler
from press.runner import Ansible, Status, StepHandler

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.nfs_server.nfs_server import NFSServer
	from press.press.doctype.nfs_volume_detachment_step.nfs_volume_detachment_step import (
		NFSVolumeDetachmentStep,
	)
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class NFSVolumeDetachment(Document, AutoScaleStepFailureHandler, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.nfs_volume_detachment_step.nfs_volume_detachment_step import (
			NFSVolumeDetachmentStep,
		)

		nfs_volume_detachment_steps: DF.Table[NFSVolumeDetachmentStep]
		primary_server: DF.Link
		secondary_server: DF.Link | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	def mark_servers_as_installing(self, step: "NFSVolumeDetachmentStep"):
		"""Mark primary and secondary servers as `Installing`"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value("Server", self.primary_server, "status", "Installing")
		frappe.db.set_value("Server", self.secondary_server, "status", "Installing")

		step.status = Status.Success
		step.save()

	def start_secondary_server(self, step: "NFSVolumeDetachmentStep"):
		"""Start secondary server"""
		step.status = Status.Running
		step.save()

		secondary_server_vm = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")
		virtual_machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", secondary_server_vm)

		if virtual_machine.status != "Running":
			virtual_machine.start()

		step.status = Status.Success
		step.save()

	def wait_for_secondary_server_to_start(self, step: "NFSVolumeDetachmentStep"):
		"""Wait for secondary server to start"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		virtual_machine = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")

		self.handle_vm_status_job(step, virtual_machine=virtual_machine, expected_status="Running")

	def stop_all_benches(self, step: "NFSVolumeDetachmentStep"):
		"""Stop all running benches"""
		server: Server = frappe.get_doc("Server", self.primary_server)
		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="stop_benches.yml",
				server=server,
				user=server._ssh_user(),
				port=server._ssh_port(),
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def unlink_benches_from_shared(self, step: "NFSVolumeDetachmentStep"):
		"""Sync data from shared to /home/frappe/benches"""
		primary_server: Server = frappe.get_cached_doc("Server", self.primary_server)
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")
		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="unlink_benches_from_nfs.yml",
				server=primary_server,
				user=primary_server._ssh_user(),
				port=primary_server._ssh_port(),
				variables={"shared_directory": shared_directory},
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def run_bench_on_primary_server(self, step: "NFSVolumeDetachmentStep"):
		"""Change bench directory"""
		secondary_server_private_ip = frappe.db.get_value(
			"Server",
			self.secondary_server,
			"private_ip",
		)

		agent_job = Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip="localhost",
			directory="/home/frappe/benches/",
			secondary_server_private_ip=secondary_server_private_ip,
			is_primary=True,
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_job_completion(self, step: "NFSVolumeDetachmentStep") -> None:
		"""Wait for agent job completion"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"NFS Volume Detachment Step",
			{
				"parent": self.name,
				"step_name": "Change bench directory",
			},
			"job",
		)
		self.handle_agent_job(step, job, poll=True)

	def umount_from_primary_server(self, step: "NFSVolumeDetachmentStep") -> None:
		"""Umount /shared from primary server and remove from fstab"""
		primary_server: Server = frappe.get_cached_doc("Server", self.primary_server)
		nfs_server_private_ip = frappe.db.get_value("NFS Server", self.nfs_server, "private_ip")
		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="umount_and_cleanup_shared.yml",
				server=primary_server,
				user=primary_server._ssh_user(),
				port=primary_server._ssh_port(),
				variables={
					"nfs_server_private_ip": nfs_server_private_ip,
					"shared_directory": f"/home/frappe/nfs/{self.primary_server}",
				},
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def remove_servers_from_acl(self, step: "NFSVolumeDetachmentStep") -> None:
		"""Remove primary and secondary servers from acl"""
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")

		try:
			agent_job = Agent(self.primary_server).remove_servers_from_acl(
				secondary_server_private_ip=secondary_server_private_ip,
			)
			step.job_type = "Agent Job"
			step.job = agent_job.name
			step.status = Status.Success
			step.save()
		except Exception as e:
			self._fail_job_step(step, e)
			raise

	def wait_for_acl_deletion(self, step: "NFSVolumeDetachmentStep"):
		"""Wait for servers to be remove from the ACL"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"NFS Volume Detachment Step",
			{
				"parent": self.name,
				"step_name": "Remove primary and secondary servers from acl",
			},
			"job",
		)

		# Jobs go undelivered for some reason, need to manually get status
		job_doc: "AgentJob" = frappe.get_doc("Agent Job", job)
		job_doc.get_status()

		self.handle_agent_job(step, job)

	def umount_volume_from_nfs_server(self, step: "NFSVolumeDetachmentStep") -> None:
		"""Umount volume from NFS Server"""
		step.status = Status.Running
		step.save()

		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.nfs_server)

		try:
			ansible = Ansible(
				playbook="umount_volume_nfs_server.yml",
				server=nfs_server,
				user=nfs_server._ssh_user(),
				port=nfs_server._ssh_port(),
				variables={
					"shared_directory": f"/home/frappe/nfs/{self.primary_server}",
				},
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def detach_and_delete_volume_from_nfs_server(self, step: "NFSVolumeDetachmentStep") -> None:
		"""Detach and delete volume from nfs server"""
		step.status = Status.Running
		step.save()

		virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", self.nfs_server)
		volume_id = frappe.get_value(
			"NFS Volume Attachment", {"primary_server": self.primary_server}, "volume_id"
		)
		try:
			virtual_machine.delete_volume(volume_id)
			step.status = Status.Success
			step.save()
		except Exception as e:
			self._fail_job_step(step, e)
			raise

	def mark_attachment_as_archived(self, step: "NFSVolumeDetachmentStep") -> None:
		"""Mark the attachment doc as archived"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value(
			"NFS Volume Attachment", {"primary_server": self.primary_server}, "status", "Archived"
		)

		step.status = Status.Success
		step.save()

	def not_ready_to_auto_scale(self, step: "NFSVolumeDetachmentStep"):
		"""Mark server as not ready to auto scale & drop secondary server"""
		step.status = Status.Running
		step.save()

		try:
			# Drop secondary server
			primary_server: "Server" = frappe.get_doc("Server", self.primary_server)
			primary_server.drop_secondary_server()

			# Mark secondary server field as empty on the primary server
			frappe.db.set_value(
				"Server",
				self.primary_server,
				{"benches_on_shared_volume": False, "secondary_server": None, "status": "Active"},
			)

			step.status = Status.Success
			step.save()
		except Exception:
			raise

	def remove_subscription_record(self, step: "NFSVolumeDetachmentStep"):
		"""Disable the subscription record for secondary server"""
		step.status = Status.Running
		step.save()

		team = frappe.db.get_value("Server", self.primary_server, "team")

		if frappe.db.exists(
			"Subscription",
			{"document_name": self.secondary_server, "team": team, "plan_type": "Server Plan"},
		):
			frappe.db.set_value(
				"Subscription",
				{"document_name": self.secondary_server, "team": team, "plan_type": "Server Plan"},
				"enabled",
				0,
			)

		step.status = Status.Success
		step.save()

	def before_insert(self):
		"""Append defined steps to the document before saving."""
		for step in self.get_steps(
			[
				self.mark_servers_as_installing,
				self.start_secondary_server,
				self.wait_for_secondary_server_to_start,
				self.unlink_benches_from_shared,
				self.run_bench_on_primary_server,
				self.wait_for_job_completion,
				self.remove_servers_from_acl,
				self.wait_for_acl_deletion,
				self.mark_attachment_as_archived,
				self.remove_subscription_record,
				self.not_ready_to_auto_scale,
			]
		):
			self.append("nfs_volume_detachment_steps", step)

		self.secondary_server = frappe.db.get_value("Server", self.primary_server, "secondary_server")

	def validate(self):
		is_server_auto_scaled = frappe.db.get_value("Server", self.primary_server, "scaled_up")
		if is_server_auto_scaled:
			frappe.throw("Benches are currently running on the secondary server!")

		has_triggers = frappe.db.get_value(
			"Prometheus Alert Rule",
			filters={
				"name": [
					"in",
					[
						f"Auto Scale Up Trigger - {self.primary_server}",
						f"Auto Scale Down Trigger - {self.primary_server}",
					],
				],
				"enabled": 1,
			},
			pluck="name",
		)

		if has_triggers:
			frappe.throw("Please remove all auto scale triggers before dropping the secondary server")

	@frappe.whitelist()
	def force_continue(self):
		self.execute_mount_steps()

	def execute_mount_steps(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_execute_steps",
			steps=self.nfs_volume_detachment_steps,
			timeout=18000,
			at_front=True,
			queue="auto-scale",
			enqueue_after_commit=True,
		)

	def after_insert(self):
		self.execute_mount_steps()
