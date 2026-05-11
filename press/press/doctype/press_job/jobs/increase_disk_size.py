from contextlib import suppress

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class IncreaseDiskSizeJob(PressJob):
	@flow
	def execute(self):
		self.increase_disk_size()

		provider = self.server_doc.provider
		if provider == "AWS EC2":
			self.wait_for_partition_to_resize_for_aws_ec2()

		elif provider == "OCI":
			self.wait_for_server_to_start_start_oci()
			self.wait_for_server_to_be_accessible_oci()
			self.add_glass_file_oci()

		if self.server_type == "Server":
			self.restart_active_benches()

	@task
	def increase_disk_size(self):
		mountpoint = self.arguments_dict.labels.get("mountpoint")
		self.server_doc.calculated_increase_disk_size(mountpoint=mountpoint)

		if not frappe.db.get_value(self.server_type, self.server, "auto_increase_storage"):
			return

	@task
	def wait_for_partition_to_resize_for_aws_ec2(self):
		"""Wait for partition to resize (AWS)"""
		if self.server_doc.provider != "AWS EC2":
			return

		plays = frappe.get_all(
			"Ansible Play",
			{"server": self.server, "play": "Extend EC2 Volume"},
			["status"],
			order_by="creation desc",
			limit=1,
		)
		if not plays:
			self.defer_current_task()

		if plays[0].status == "Success":
			return

		if plays[0].status == "Failure":
			raise Exception("Failed to extend EC2 volume")

		self.defer_current_task()

	@task
	def wait_for_server_to_start_start_oci(self):
		"""Wait for server to start (OCI)"""
		if self.server_doc.provider != "OCI":
			return

		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Running":
			return

		self.defer_current_task()

	@task(queue="long", timeout=600)
	def wait_for_server_to_be_accessible_oci(self):
		"""Wait for server to be accessible (OCI)"""
		if self.server_doc.provider != "OCI":
			return

		play = self.server_doc.ping_ansible()
		if play and play.status == "Success":
			return

		self.defer_current_task()

	@task
	def add_glass_file_oci(self):
		"""Add glass file back (OCI)"""
		if self.server_doc.provider != "OCI":
			return

		self.server_doc._add_glass_file()

	@task
	def restart_active_benches(self):
		if self.server_type != "Server":
			return

		self.server_doc._start_active_benches(
			benches=frappe.get_all(
				"Bench",
				{
					"server": self.server,
					"status": "Active",
				},
				pluck="name",
			)
		)
