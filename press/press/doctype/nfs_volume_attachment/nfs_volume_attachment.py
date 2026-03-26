# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import typing

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.auto_scale_record.auto_scale_record import AutoScaleStepFailureHandler
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import is_image_in_registry
from press.runner import Ansible, Status, StepHandler

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.nfs_volume_attachment_step.nfs_volume_attachment_step import (
		NFSVolumeAttachmentStep,
	)
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class NFSVolumeAttachment(Document, AutoScaleStepFailureHandler, StepHandler):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.nfs_volume_attachment_step.nfs_volume_attachment_step import (
			NFSVolumeAttachmentStep,
		)

		nfs_volume_attachment_steps: DF.Table[NFSVolumeAttachmentStep]
		primary_server: DF.Link
		secondary_server: DF.Link | None
		status: DF.Literal["Pending", "Running", "Success", "Failure", "Archived"]
	# end: auto-generated types

	def validate(self):
		"""Check if the primary server has a secondary server provisioned with no existing attachments"""
		has_shared_volume_setup = frappe.db.exists(
			"NFS Volume Attachment",
			{
				"primary_server": self.primary_server,
				"secondary_server": self.secondary_server,
				"status": "Success",
			},
		)

		if has_shared_volume_setup:
			frappe.throw(
				f"{self.primary_server} is already sharing benches with {self.secondary_server}!",
			)

	def mark_servers_as_installing(self, step: "NFSVolumeAttachmentStep"):
		"""Mark primary and secondary servers as `Installing`"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value("Server", self.primary_server, "status", "Installing")
		frappe.db.set_value("Server", self.secondary_server, "status", "Installing")

		step.status = Status.Success
		step.save()

	def start_secondary_server(self, step: "NFSVolumeAttachmentStep"):
		"""Start secondary server"""
		step.status = Status.Running
		step.save()

		secondary_server_vm = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")
		virtual_machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", secondary_server_vm)

		if virtual_machine.status != "Running":
			virtual_machine.start()

		step.status = Status.Success
		step.save()

	def wait_for_secondary_server_to_start(self, step: "NFSVolumeAttachmentStep"):
		"""Wait for secondary server to start"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		virtual_machine = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")

		self.handle_vm_status_job(step, virtual_machine=virtual_machine, expected_status="Running")

	def setup_nfs_common_on_secondary(self, step: "NFSVolumeAttachmentStep"):
		"""Install nfs common on secondary server for sanity"""
		server: Server = frappe.get_doc("Server", self.secondary_server)
		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="install_nfs_common.yml",
				server=server,
				user=server._ssh_user(),
				port=server._ssh_port(),
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def allow_servers_to_mount(self, step: "NFSVolumeAttachmentStep"):
		"""Allow primary and secondary server to share fs"""
		primary_server: Server = frappe.get_cached_doc("Server", self.primary_server)
		secondary_server_private_ip = frappe.db.get_value(
			"Server", primary_server.secondary_server, "private_ip"
		)

		try:
			agent_job = Agent(primary_server.name).add_servers_to_acl(
				secondary_server_private_ip=secondary_server_private_ip,
				reference_doctype=primary_server.doctype,
				reference_name=primary_server.name,
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

		# Jobs go undelivered for some reason, need to manually get status
		job_doc: "AgentJob" = frappe.get_doc("Agent Job", job)
		job_doc.get_status()

		self.handle_agent_job(step, job)

	def mount_shared_folder_on_secondary_server(self, step: "NFSVolumeAttachmentStep") -> None:
		"""Mount shared folder on secondary server"""
		secondary_server: Server = frappe.get_cached_doc("Server", self.secondary_server)
		primary_server_private_ip = frappe.db.get_value("Server", secondary_server.primary, "private_ip")
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")

		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="mount_shared_folder.yml",
				server=secondary_server,
				user=secondary_server._ssh_user(),
				port=secondary_server._ssh_port(),
				variables={
					"primary_server_private_ip": primary_server_private_ip,
					"using_fs_of_server": self.primary_server,
					"shared_directory": shared_directory,
				},
			)

			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def link_benches_to_shared(self, step: "NFSVolumeAttachmentStep") -> None:
		"""Link benches to the shared NFS directory."""
		primary_server: Server = frappe.get_cached_doc("Server", self.primary_server)
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")

		step.status = Status.Running
		step.save()

		try:
			ansible = Ansible(
				playbook="link_benches_to_nfs.yml",
				server=primary_server,
				user=primary_server._ssh_user(),
				port=primary_server._ssh_port(),
				variables={"shared_directory": shared_directory},
			)

			self.handle_ansible_play(step, ansible)
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
		shared_directory = frappe.db.get_single_value("Press Settings", "shared_directory")

		agent_job = Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip="localhost",
			directory=shared_directory,
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

		self.handle_agent_job(step, job, poll=True)

	def add_loopback_rule(self, step: "NFSVolumeAttachmentStep"):
		"""Allow loopback requests from container"""
		step.status = Status.Running
		step.save()

		primary_server: "Server" = frappe.get_doc("Server", self.primary_server)

		try:
			ansible = Ansible(
				playbook="allow_docker_loopback.yml",
				server=primary_server,
				user=primary_server._ssh_user(),
				port=primary_server._ssh_port(),
			)
			self.handle_ansible_play(step, ansible)
		except Exception as e:
			self._fail_ansible_step(step, ansible, e)
			raise

	def stop_secondary_server(self, step: "NFSVolumeAttachmentStep"):
		"""Stop secondary server"""
		step.status = Status.Running
		step.save()

		secondary_server_vm = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")
		virtual_machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", secondary_server_vm)

		if virtual_machine.status == "Running":
			virtual_machine.stop()

		step.status = Status.Success
		step.save()

	def wait_for_secondary_server_to_stop(self, step: "NFSVolumeAttachmentStep"):
		"""Wait for secondary server to stop"""
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		virtual_machine = frappe.db.get_value("Server", self.secondary_server, "virtual_machine")

		self.handle_vm_status_job(step, virtual_machine=virtual_machine, expected_status="Stopped")

	def create_subscription_record(self, step: "NFSVolumeAttachmentStep"):
		"""Create a subscription record for secondary server"""
		step.status = Status.Running
		step.save()

		team = frappe.db.get_value("Server", self.primary_server, "team")

		if not frappe.db.exists(
			"Subscription",
			{"document_name": self.secondary_server, "team": team, "plan_type": "Server Plan"},
		):
			frappe.get_doc(
				doctype="Subscription",
				team=team,
				plan_type="Server Plan",
				plan=frappe.db.get_value("Server", self.secondary_server, "plan"),
				document_type="Server",
				document_name=self.secondary_server,
				interval="Hourly",
				enabled=1,
			).insert()

		step.status = Status.Success
		step.save()

	def push_missing_images_to_registry(self, step: "NFSVolumeAttachmentStep"):
		"""Push missing bench images present on server to registry"""
		# We know for a fact that newer benches will have images present in the registry
		# due to the s3 storage backend, therefore this only needs to be done for older benches
		# which might not have their image in the registry making it a one time step

		step.status = Status.Running
		step.save()

		missing_images = []
		registry_settings = frappe.db.get_value(
			"Press Settings",
			None,
			[
				"domain",
				"docker_registry_url",
				"docker_registry_namespace",
				"docker_registry_username",
				"docker_registry_password",
			],
			as_dict=True,
		)
		Bench = frappe.qb.DocType("Bench")
		DeployCandidateBuild = frappe.qb.DocType("Deploy Candidate Build")
		active_bench_images_on_server = (
			frappe.qb.from_(Bench)
			.join(DeployCandidateBuild)
			.on(Bench.build == DeployCandidateBuild.name)
			.select(DeployCandidateBuild.name, DeployCandidateBuild.group, DeployCandidateBuild.docker_image)
			.where(Bench.server == self.primary_server)
			.where(Bench.status == "Active")
			.run(as_dict=True)
		)

		for image_on_server in active_bench_images_on_server:
			is_image_present = is_image_in_registry(
				image_on_server["name"], image_on_server["group"], registry_settings
			)
			if not is_image_present:
				missing_images.append(image_on_server["docker_image"])

		if not missing_images:
			# Successful if all images are in registry
			step.status = Status.Success
			step.save()
			return

		# At this point we can trigger a agent job to push missing docker images
		agent_job = Agent(self.primary_server).push_docker_images(
			images=missing_images, reference_doctype="Server", reference_name=self.primary_server
		)

		step.status = Status.Success
		step.job_type = "Agent Job"
		step.job = agent_job.name
		step.is_waiting = True

		step.output = "Pushing the following missing images to registry:\n{}".format(
			"\n".join(missing_images)
		)
		step.save()

	def wait_for_missing_images(self, step: "NFSVolumeAttachmentStep"):
		"Wait for missing images push to complete"
		step.status = Status.Running
		step.is_waiting = True
		step.save()

		job = frappe.db.get_value(
			"NFS Volume Attachment Step",
			{
				"parent": self.name,
				"step_name": "Push missing bench images present on server to registry",
			},
			"job",
		)

		if not job:
			# All images were preset
			step.status = Status.Success
			step.save()
			return

		self.handle_agent_job(step, job)

	def ready_to_auto_scale(self, step: "NFSVolumeAttachmentStep"):
		"""Mark server as ready to auto scale"""
		step.status = Status.Running
		step.save()

		frappe.db.set_value(
			"Server", self.primary_server, {"benches_on_shared_volume": True, "status": "Active"}
		)
		frappe.db.set_value(
			"Server", self.secondary_server, {"status": "Active", "is_monitoring_disabled": True}
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
				self.setup_nfs_common_on_secondary,
				self.allow_servers_to_mount,
				self.wait_for_acl_addition,
				self.mount_shared_folder_on_secondary_server,
				self.link_benches_to_shared,
				self.run_primary_server_benches_on_shared_fs,
				self.wait_for_benches_to_run_on_shared,
				self.add_loopback_rule,
				self.stop_secondary_server,
				self.wait_for_secondary_server_to_stop,
				self.create_subscription_record,
				self.push_missing_images_to_registry,
				self.wait_for_missing_images,
				self.ready_to_auto_scale,
			]
		):
			self.append("nfs_volume_attachment_steps", step)

		self.secondary_server = frappe.db.get_value("Server", self.primary_server, "secondary_server")

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
			queue="auto-scale",
			enqueue_after_commit=True,
		)

	def after_insert(self):
		self.execute_mount_steps()
