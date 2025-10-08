# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import time
import typing
from enum import Enum

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.nfs_volume_attachment.nfs_volume_attachment import StepHandler
from press.runner import Ansible

if typing.TYPE_CHECKING:
	from press.press.doctype.nfs_volume_detachment_step.nfs_volume_detachment_step import (
		NFSVolumeDetachmentStep,
	)
	from press.press.doctype.server.server import Server


class Status(str, Enum):
	Pending = "Pending"
	Running = "Running"
	Success = "Success"
	Failure = "Failure"

	def __str__(self):
		return self.value


class NFSVolumeDetachment(Document, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.nfs_volume_detachment_step.nfs_volume_detachment_step import (
			NFSVolumeDetachmentStep,
		)

		nfs_server: DF.Link | None
		nfs_volume_detachment_steps: DF.Table[NFSVolumeDetachmentStep]
		primary_server: DF.Link | None
		secondary_server: DF.Link | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	def stop_all_benches(self, step: "NFSVolumeDetachmentStep"):
		"""Stop all benches running on /shared"""
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

	def sync_data(self, step: "NFSVolumeDetachmentStep"):
		"""Sync data from /shared to /home/frappe/benches"""
		primary_server: Server = frappe.get_cached_doc("Server", self.primary_server)
		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="sync_bench_data.yml",
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

	def run_bench_on_primary_server(self, step: "NFSVolumeDetachmentStep"):
		"""Change bench directory"""
		secondary_server_private_ip = frappe.db.get_value(
			"Server",
			self.secondary_server,
			"private_ip",
		)

		agent_job = Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip=None,
			directory="/home/frappe/benches/",
			secondary_server_private_ip=secondary_server_private_ip,
			is_primary=True,
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

		step.status = Status.Running
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def wait_for_job_completion(self, step: "NFSVolumeDetachmentStep") -> None:
		"""Wait for agent job completion"""
		step.status = Status.Running
		step.save()

		job = frappe.db.get_value(
			"NFS Volume Detachment Step",
			{
				"parent": self.name,
				"step_name": "Change bench directory",
			},
			"job",
		)
		job_status = frappe.db.get_value("Agent Job", job, "status")

		status_map = {
			"Delivery Failure": Status.Failure,
			"Undelivered": Status.Pending,
		}
		job_status = status_map.get(job_status, job_status)

		if job_status not in (Status.Success, Status.Failure):
			step.attempt += 1
			step.save()
			time.sleep(5)
			frappe.db.commit()  # avoid long-running transactions
			self.wait_for_job_completion(step)
			return

		step.status = job_status
		step.save()

		if step.status == Status.Failure:
			raise

	def umount_from_primary_server(self, step: "NFSVolumeDetachmentStep"):
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
			self._run_ansible_step(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def umount_from_secondary_server(self, step: "NFSVolumeDetachmentStep"):
		"""Umount /shared from secondary server and remove from fstab"""
		secondary_server: Server = frappe.get_cached_doc("Server", self.secondary_server)
		nfs_server_private_ip = frappe.db.get_value("NFS Server", self.nfs_server, "private_ip")
		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="umount_and_cleanup_shared.yml",
				server=secondary_server,
				user=secondary_server._ssh_user(),
				port=secondary_server._ssh_port(),
				variables={
					"nfs_server_private_ip": nfs_server_private_ip,
					"shared_directory": f"/home/frappe/nfs/{self.primary_server}",
				},
			)
			self._run_ansible_step(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def before_insert(self):
		"""Append defined steps to the document before saving."""
		for step in self.get_steps(
			[
				self.stop_all_benches,
				self.sync_data,
				self.run_bench_on_primary_server,
				self.wait_for_job_completion,
				self.umount_from_primary_server,
				self.umount_from_secondary_server,
			]
		):
			self.append("nfs_volume_detachment_steps", step)

	def validate(self):
		is_server_auto_scaled = frappe.db.get_value("Server", self.primary_server, "auto_scale")
		if is_server_auto_scaled:
			frappe.throw("Benches are currently being run on the secondary server!")

	def execute_mount_steps(self):
		self._execute_steps(steps=self.nfs_volume_detachment_steps)
		# frappe.enqueue_doc(
		# 	self.doctype,
		# 	self.name,
		# 	"_execute_steps",
		# 	steps=self.nfs_volume_detachment_steps,
		# 	timeout=18000,
		# 	at_front=True,
		# 	queue="long",
		# )

	def after_insert(self):
		self.execute_mount_steps()
