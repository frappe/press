# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import time
import typing
from enum import Enum

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.runner import Ansible

if typing.TYPE_CHECKING:
	from press.press.doctype.nfs_server.nfs_server import NFSServer
	from press.press.doctype.nfs_volume_attachment_step.nfs_volume_attachment_step import (
		NFSVolumeAttachmentStep,
	)
	from press.press.doctype.nfs_volume_detachment_step.nfs_volume_detachment_step import (
		NFSVolumeDetachmentStep,
	)
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class Status(str, Enum):
	Pending = "Pending"
	Running = "Running"
	Success = "Success"
	Failure = "Failure"

	def __str__(self):
		return self.value


class StepHandler:
	def handle_async_job(self, step: "NFSVolumeAttachmentStep" | "NFSVolumeDetachmentStep", job: str) -> None:
		job_status = frappe.db.get_value("Agent Job", job, "status")

		status_map = {
			"Delivery Failure": Status.Failure,
			"Undelivered": Status.Pending,
		}
		job_status = status_map.get(job_status, job_status)
		step.attempt = 1 if not step.attempt else step.attempt + 1

		step.status = job_status
		step.save()

		if step.status == Status.Failure:
			raise

	def _run_ansible_step(
		self, step: "NFSVolumeAttachmentStep" | "NFSVolumeDetachmentStep", ansible: Ansible
	) -> None:
		step.job_type = "Ansible Play"
		step.job = ansible.play
		step.save()
		ansible_play = ansible.run()
		step.status = ansible_play.status
		step.save()

		if step.status == Status.Failure:
			raise

	def _fail_ansible_step(
		self,
		step: "NFSVolumeAttachmentStep" | "NFSVolumeDetachmentStep",
		ansible: Ansible,
		e: Exception | None = None,
	) -> None:
		step.job = getattr(ansible, "play", None)
		step.status = Status.Failure
		step.output = str(e)
		step.save()

	def _fail_job_step(
		self, step: "NFSVolumeAttachmentStep" | "NFSVolumeDetachmentStep", e: Exception | None = None
	) -> None:
		step.status = Status.Failure
		step.output = str(e)
		step.save()

	def fail(self):
		self.status = Status.Failure
		self.save()
		frappe.db.commit()

	def succeed(self):
		self.status = Status.Success
		self.save()
		frappe.db.commit()

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
				"message": f"Error occurred during auto scale {'setup' if self.doctype == 'NFS Volume Attachment' else 'teardown'}",
			}
		)
		press_notification.insert()
		frappe.db.commit()

	def get_steps(self, methods: list) -> list[dict]:
		"""Generate a list of steps to be executed for NFS volume attachment."""
		return [
			{
				"step_name": method.__doc__,
				"method_name": method.__name__,
				"status": "Pending",
			}
			for method in methods
		]

	def _get_method(self, method_name: str):
		"""Retrieve a method object by name."""
		return getattr(self, method_name)

	def next_step(
		self, steps: list["NFSVolumeAttachmentStep" | "NFSVolumeDetachmentStep"]
	) -> "NFSVolumeAttachmentStep" | "NFSVolumeDetachmentStep" | None:
		for step in steps:
			if step.status not in (Status.Success, Status.Failure):
				return step

		return None

	def _execute_steps(self, steps: list["NFSVolumeAttachmentStep" | "NFSVolumeDetachmentStep"]):
		"""Sequentially execute defined NFS attachment steps."""
		self.status = Status.Running
		self.save()
		frappe.db.commit()

		while True:
			step = self.next_step(steps)
			if not step:
				break  # We are done here

			step = step.reload()
			method = self._get_method(step.method_name)

			try:
				method(step)  # Each step updates its own state
			except Exception:
				self.reload()
				self.fail()
				self.handle_step_failure()
				return  # Stop on first failure

			self.reload()
			frappe.db.commit()
			time.sleep(1)

		self.succeed()


def get_restart_benches_play(server: str) -> Ansible:
	"""Get restart benches play"""
	primary_server: Server = frappe.get_cached_doc("Server", server)
	benches = frappe.get_all("Bench", {"server": server, "status": "Active"}, pluck="name")
	return Ansible(
		playbook="start_benches.yml",
		server=primary_server,
		user=primary_server._ssh_user(),
		port=primary_server._ssh_port(),
		variables={"benches": " ".join(benches)},
	)


class NFSVolumeAttachment(Document, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.nfs_volume_attachment_step.nfs_volume_attachment_step import (
			NFSVolumeAttachmentStep,
		)

		nfs_server: DF.Link
		nfs_volume_attachment_steps: DF.Table[NFSVolumeAttachmentStep]
		primary_server: DF.Link
		secondary_server: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure", "Archived"]
		volume_id: DF.Data | None
	# end: auto-generated types

	def validate(self):
		"""Check if the primary server has a secondary server provisioned with no existing attachments"""
		secondary_server_status = frappe.db.get_value("Server", self.secondary_server, "status")

		if not secondary_server_status or secondary_server_status != "Active":
			frappe.throw("Please select a primary server that has a secondary server provisioned!")

		has_shared_volume_setup = frappe.db.exists(
			"NFS Volume Attachment",
			{
				"nfs_server": self.nfs_server,
				"primary_server": self.primary_server,
				"secondary_server": self.secondary_server,
				"status": "Success",
			},
		)

		if has_shared_volume_setup:
			frappe.throw(
				f"{self.primary_server} is already sharing benches with {self.secondary_server}!",
			)

	def stop_all_benches(self, step: "NFSVolumeAttachmentStep"):
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
			self._run_ansible_step(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def attach_volume_on_nfs_server(self, step: "NFSVolumeAttachmentStep") -> None:
		"""Attach a new volume on the NFS server."""
		step.status = Status.Running
		step.save()

		volume_size = frappe.db.get_value("Virtual Machine", self.primary_server, "disk_size")
		virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", self.nfs_server)
		try:
			volume_id = virtual_machine.attach_new_volume(
				volume_size,
				iops=3000,
				throughput=124,
				log_activity=False,
			)
			frappe.db.set_value(
				"NFS Volume Attachment", self.name, "volume_id", volume_id
			)  # Need to do this otherwise a reload is required
			step.status = Status.Success
			step.save()
		except Exception as e:
			self._fail_job_step(step, e)
			raise

	def allow_servers_to_mount(self, step: "NFSVolumeAttachmentStep"):
		"""Allow primary and secondary server to share fs"""
		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.nfs_server)
		primary_server_private_ip = frappe.db.get_value("Server", self.primary_server, "private_ip")
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")

		try:
			agent_job = nfs_server.agent.add_servers_to_acl(
				primary_server_private_ip=primary_server_private_ip,
				secondary_server_private_ip=secondary_server_private_ip,
				shared_directory=self.primary_server,
			)
			step.job_type = "Agent Job"
			step.job = agent_job.name
			step.status = Status.Success
			step.save()
		except Exception as e:
			self._fail_job_step(step, e)
			raise

	def wait_for_acl_addition(self, step: "NFSVolumeAttachmentStep"):
		"""Wait for servers to be added to ACL"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"NFS Volume Attachment Step",
			{
				"parent": self.name,
				"step_name": "Allow primary and secondary server to share fs",
			},
			"job",
		)
		self.handle_async_job(step, job)

	def format_and_mount_fs(self, step: "NFSVolumeAttachmentStep") -> None:
		"""Create a filesystem on the new volume and mount the shared directory."""
		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.nfs_server)

		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="mount_ebs_on_nfs_server.yml",
				server=nfs_server,
				user=nfs_server._ssh_user(),
				port=nfs_server._ssh_port(),
				variables={
					"shared_directory": f"/home/frappe/nfs/{self.primary_server}",
					"volume_id": self.volume_id.replace("vol-", ""),
				},
			)

			self._run_ansible_step(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def allow_ssh_access_to_primary_server(self, step: "NFSVolumeAttachmentStep"):
		"""Add primary server keys to nfs server"""
		primary_server: Server = frappe.get_cached_doc("Server", self.primary_server)

		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="ssh_access_to_rsync.yml",
				server=primary_server,
				user=primary_server._ssh_user(),
				port=primary_server._ssh_port(),
				variables={
					"ssh_user": primary_server._ssh_user(),
					"ssh_key_path": "/root/.ssh/id_ed25519",
					"destination_host": self.nfs_server,  # This is the nfs server
				},
			)

			self._run_ansible_step(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def mount_shared_folder_on_primary_server(self, step: "NFSVolumeAttachmentStep") -> None:
		"""Mount shared folder on primary server"""
		primary_server: Server = frappe.get_cached_doc("Server", self.primary_server)
		nfs_server_private_ip = frappe.db.get_value("NFS Server", self.nfs_server, "private_ip")

		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="mount_shared_folder.yml",
				server=primary_server,
				user=primary_server._ssh_user(),
				port=primary_server._ssh_port(),
				variables={
					"nfs_server_private_ip": nfs_server_private_ip,
					"using_fs_of_server": self.primary_server,
					"shared_directory": "/shared",
				},
			)

			self._run_ansible_step(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def mount_shared_folder_on_secondary_server(self, step: "NFSVolumeAttachmentStep") -> None:
		"""Mount shared folder on secondary server"""
		secondary_server: Server = frappe.get_cached_doc("Server", self.secondary_server)
		nfs_server_private_ip = frappe.db.get_value("NFS Server", self.nfs_server, "private_ip")

		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="mount_shared_folder.yml",
				server=secondary_server,
				user=secondary_server._ssh_user(),
				port=secondary_server._ssh_port(),
				variables={
					"nfs_server_private_ip": nfs_server_private_ip,
					"using_fs_of_server": self.primary_server,
					"shared_directory": "/shared",
				},
			)

			self._run_ansible_step(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def move_benches_to_shared(self, step: "NFSVolumeAttachmentStep") -> None:
		"""Move benches to the shared NFS directory."""
		primary_server: Server = frappe.get_cached_doc("Server", self.primary_server)

		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="share_benches_on_nfs.yml",
				server=primary_server,
				user=primary_server._ssh_user(),
				port=primary_server._ssh_port(),
				variables={
					"nfs_server": self.nfs_server,
					"client_server": primary_server.name,
				},
			)

			self._run_ansible_step(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def run_primary_server_benches_on_shared_fs(
		self,
		step: "NFSVolumeAttachmentStep",
	) -> None:
		"""Run benches on shared volume"""
		secondary_server_private_ip = frappe.db.get_value(
			"Server",
			self.secondary_server,
			"private_ip",
		)

		agent_job = Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip="localhost",
			directory="/shared",
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

	def wait_for_benches_to_run_on_shared(self, step: "NFSVolumeAttachmentStep"):
		"""Wait for benches to run on shared volume"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"NFS Volume Attachment Step",
			{
				"parent": self.name,
				"step_name": "Run benches on shared volume",
			},
			"job",
		)

		self.handle_async_job(step, job)

	def ready_to_auto_scale(self, step: "NFSVolumeAttachmentStep"):
		"""Mark server as ready to auto scale"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value("Server", self.primary_server, "benches_on_shared_volume", True)

		step.status = Status.Success
		step.save()

	def before_insert(self):
		"""Append defined steps to the document before saving."""
		for step in self.get_steps(
			[
				self.stop_all_benches,
				self.attach_volume_on_nfs_server,
				self.allow_servers_to_mount,
				self.wait_for_acl_addition,
				self.format_and_mount_fs,
				self.allow_ssh_access_to_primary_server,
				self.mount_shared_folder_on_primary_server,
				self.mount_shared_folder_on_secondary_server,
				self.move_benches_to_shared,
				self.run_primary_server_benches_on_shared_fs,
				self.wait_for_benches_to_run_on_shared,
				self.ready_to_auto_scale,
			]
		):
			self.append("nfs_volume_attachment_steps", step)

	@frappe.whitelist()
	def force_continue(self):
		self.execute_mount_steps()

	def execute_mount_steps(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_execute_steps",
			steps=self.nfs_volume_attachment_steps,
			timeout=18000,
			at_front=True,
			queue="long",
			enqueue_after_commit=True,
		)

	def after_insert(self):
		self.execute_mount_steps()
