# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing
from enum import Enum

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.runner import Ansible
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.nfs_server.nfs_server import NFSServer
	from press.press.doctype.nfs_volume_attachment_step.nfs_volume_attachment_step import (
		NFSVolumeAttachmentStep,
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


class NFSVolumeAttachment(Document):
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
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		volume_id: DF.Data | None
		volume_size: DF.Int
	# end: auto-generated types

	def validate(self):
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

		if not self.secondary_server:
			frappe.throw("Please select a primary server that has a secondary server provisioned!")

	def get_steps(self) -> list[dict]:
		"""Generate a list of steps to be executed for NFS volume attachment."""
		methods = [
			self.attach_volume_on_nfs_server,
			self.allow_servers_to_mount,
			self.format_and_mount_fs,
			self.allow_ssh_access_to_primary_server,
			self.mount_shared_folder_on_primary_server,
			self.mount_shared_folder_on_secondary_server,
			self.move_benches_to_shared,
			self.run_primary_server_benches_on_shared_fs,
		]

		return [
			{
				"step_name": method.__doc__,
				"method_name": method.__name__,
				"status": "Pending",
			}
			for method in methods
		]

	def _run_ansible_step(step: "NFSVolumeAttachmentStep", ansible: Ansible) -> None:
		step.job_type = "Ansible Play"
		step.job = ansible.play
		step.save()
		ansible.run()
		step.status = Status.Success
		step.save()

	def _fail_ansible_step(
		step: "NFSVolumeAttachmentStep",
		ansible: Ansible,
		e: Exception | None = None,
	) -> None:
		step.job = getattr(ansible, "play", None)
		step.status = Status.Failure
		step.output = str(e)
		step.save()

	def _fail_job_step(self, step: "NFSVolumeAttachmentStep", e: Exception | None = None) -> None:
		step.status = Status.Failure
		step.output = str(e)
		step.save()

	def allow_servers_to_mount(self, step: "NFSVolumeAttachmentStep"):
		"""Allow primary and secondary server to share fs"""
		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.nfs_server)
		primary_server_private_ip = frappe.db.get_value("Server", self.primary_server, "private_ip")
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")

		step.status = Status.Running
		step.save()
		try:
			# Allow primary server to mount
			nfs_server.agent.post(
				"/nfs/exports",
				data={
					"server": self.primary_server,
					"private_ip": primary_server_private_ip,
					"share_file_system": True,
					"use_file_system_of_server": None,
				},
			)

			# Allow secondary server to mount
			nfs_server.agent.post(
				"/nfs/exports",
				data={
					"server": self.secondary_server,
					"private_ip": secondary_server_private_ip,
					"share_file_system": False,
					"use_file_system_of_server": self.primary_server,
				},
			)

			step.status = Status.Success
			step.save()
		except Exception as e:
			self._fail_job_step(step, e)
			raise

	def attach_volume_on_nfs_server(self, step: "NFSVolumeAttachmentStep") -> None:
		"""Attach a new volume on the NFS server."""
		step.status = Status.Running
		step.save()

		virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", self.nfs_server)
		try:
			self.volume_id = virtual_machine.attach_new_volume(
				self.volume_size,
				iops=3000,
				throughput=124,
				log_activity=False,
			)

			step.status = Status.Success
			self.save()
		except Exception as e:
			self._fail_job_step(step, e)
			raise

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

			log_error(
				title="Error mounting volume on NFS server",
				message=str(e),
				server=self.as_dict(),
			)
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

			log_error("Exception While Giving SSH Access", server=self.as_dict())
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

			log_error("Exception While Mounting Shared FS", server=self.as_dict())
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

			log_error("Exception While Mounting Shared FS", server=self.as_dict())
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

			log_error(
				"Exception while moving benches to shared FS",
				message=str(e),
				server=self.as_dict(),
			)
			raise

	def run_primary_server_benches_on_shared_fs(
		self,
		step: "NFSVolumeAttachmentStep",
	) -> None:
		"""
		Run benches on shared volume
		"""
		# Runs the following steps:
		# 	1. Changes benches_directory to `/shared`
		# 	2. Updates agent nginx config file to include `/shared/*/nginx.conf`
		# 	3. Updates benches nginx config file update the root dir
		# 	4. Restarts benches
		secondary_server_private_ip = frappe.db.get_value(
			"Server",
			self.secondary_server,
			"private_ip",
		)

		agent_job = Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip=None,
			directory="/shared",
			secondary_server_private_ip=secondary_server_private_ip,
			is_primary=True,
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.save()

	def fail(self):
		self.status = Status.Failure
		self.save()
		frappe.db.commit()

	def succeed(self):
		self.status = Status.Success
		self.save()
		frappe.db.commit()

	def before_insert(self):
		"""Append defined steps to the document before saving."""
		self.volume_size = frappe.db.get_value("Virtual Machine", self.primary_server, "disk_size")
		for step in self.get_steps():
			self.append("nfs_volume_attachment_steps", step)

	def _get_method(self, method_name: str):
		"""Retrieve a method object by name."""
		return getattr(self, method_name)

	def _execute_steps(self):
		"""Sequentially execute defined NFS attachment steps."""
		self.status = Status.Running
		self.save()
		frappe.db.commit()

		for step in self.nfs_volume_attachment_steps:
			method = self._get_method(step.method_name)

			try:
				method(step)  # Each step updates its own state
			except Exception:
				self.fail()  # We can however fail here
				return  # Stop on first failure

			frappe.db.commit()

	def execute_mount_steps(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_execute_steps", timeout=18000, at_front=True, queue="long"
		)

	def after_insert(self):
		self.execute_mount_steps()

	@classmethod
	def process_run_shared_benches_job(cls, job: "AgentJob") -> None:
		"""Since this is the last job it can decide the status of the NFS volume attachment"""
		try:
			nfs_volume_attachment: NFSVolumeAttachment = frappe.get_doc(
				"NFS Volume Attachment", {"primary_server": job.reference_name, "status": "Running"}
			)
		except frappe.DoesNotExistError:
			return

		status_map = {
			"Delivery Failure": Status.Failure,
			"Undelivered": Status.Pending,
		}
		job_status = status_map.get(job.status, job.status)

		last_step = nfs_volume_attachment.nfs_volume_attachment_steps[-1]
		last_step.status = job_status
		last_step.save()

		if job.status == Status.Success:
			nfs_volume_attachment.succeed()

		elif job.status == Status.Failure:
			nfs_volume_attachment.fail()


### Umount (No support for this currently)
def remove_server_from_nfs_acl(self):
	nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.parent)

	if self.share_file_system and self.is_file_system_being_shared:
		frappe.throw("File system is being used by another server please unmount that first!")

	private_ip = frappe.db.get_value("Server", self.server, "private_ip")
	nfs_server.agent.delete(
		"/nfs/exports",
		data={
			"private_ip": private_ip,
			"file_system": self.use_file_system_of_server if not self.share_file_system else self.server,
		},
	)


def umount_and_delete_shared_directory_on_client(client_server: str, nfs_server: str, shared_directory: str):
	client_server: Server = frappe.get_cached_doc("Server", client_server)
	nfs_server_private_ip = frappe.db.get_value("NFS Server", nfs_server, "private_ip")
	try:
		ansible = Ansible(
			playbook="umount_and_cleanup_shared.yml",
			server=client_server,
			user=client_server._ssh_user(),
			port=client_server._ssh_port(),
			variables={
				"nfs_server_private_ip": nfs_server_private_ip,
				"shared_directory": f"/home/frappe/nfs/{shared_directory}",
			},
		)
		ansible.run()
	except Exception:
		log_error("Exception While Cleaning Up Shared Directory")


def detach_umount_and_delete_volume_on_nfs(nfs_server: str, volume_id: str, shared_directory: str):
	virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", nfs_server)

	try:
		virtual_machine.detach(volume_id)
		virtual_machine.delete_volume(volume_id)
	except Exception:
		pass  # Generally throws unable to detach volume, but the volume is detached

	nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", nfs_server)

	try:
		ansible = Ansible(
			playbook="umount_volume_nfs_server.yml",
			server=nfs_server,
			user=nfs_server._ssh_user(),
			port=nfs_server._ssh_port(),
			variables={
				"shared_directory": f"/home/frappe/nfs/{shared_directory}",
			},
		)
		ansible.run()
	except Exception:
		log_error("Exception While Cleaning Up NFS Server")
