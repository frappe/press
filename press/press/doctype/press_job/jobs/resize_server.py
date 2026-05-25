from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.server.server import Server


class ResizeServerJob(PressJob):
	@flow
	def execute(self):
		self.stop_virtual_machine()
		self.wait_for_virtual_machine_to_stop()

		self.resize_virtual_machine()

		self.start_virtual_machine()
		self.wait_for_virtual_machine_to_start()

		self.wait_for_server_to_be_accessible()
		self.set_additional_config()
		self.increase_disk_size()

	@task
	def stop_virtual_machine(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Stopped":
			return

		self.virtual_machine_doc.stop()

	@task
	def wait_for_virtual_machine_to_stop(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Stopped":
			return

		self.defer_current_task()

	@task
	def resize_virtual_machine(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if (
			self.arguments_dict.get("upgrade_disk", False)
			and self.virtual_machine_doc.machine_type == self.arguments_dict.machine_type
		):
			return

		self.virtual_machine_doc.resize(
			self.arguments_dict.machine_type, self.arguments_dict.get("upgrade_disk", False)
		)

	@task
	def start_virtual_machine(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

			if self.virtual_machine_doc.status == "Running":
				return

		try:
			self.virtual_machine_doc.start()
		except Exception:
			self.defer_current_task()

	@task
	def wait_for_virtual_machine_to_start(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

		if self.virtual_machine_doc.status == "Running":
			return

		self.defer_current_task()

	@task
	def wait_for_server_to_be_accessible(self):
		play = self.server_doc.ping_ansible()
		if not play or play.status != "Success":
			self.defer_current_task()

	@task
	def set_additional_config(self):
		if self.server_type not in ["Server", "Database Server"]:
			return

		if self.server_type == "Server" and self.server_doc.is_unified_server:
			server_doc: Server = frappe.get_doc("Server", self.server)
			server_doc.auto_scale_workers()
			db_doc: DatabaseServer = frappe.get_doc("Database Server", self.server)
			db_doc.adjust_memory_config()
		else:
			if self.server_type == "Database Server":
				self.server_doc.adjust_memory_config()
			elif self.server_type == "Server":
				self.server_doc.auto_scale_workers()

	@task
	def increase_disk_size(self):
		if not self.server_doc.plan:
			return

		plan_disk_size = frappe.db.get_value("Server Plan", self.server_doc.plan, "disk")
		if not plan_disk_size or plan_disk_size <= self.virtual_machine_doc.disk_size:
			return

		with suppress(Exception):
			self.server_doc.increase_disk_size(increment=plan_disk_size - self.virtual_machine_doc.disk_size)
