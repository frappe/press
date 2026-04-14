# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe

from press.runner import Ansible
from press.workflow_engine.doctype.press_workflow.decorators import flow, task
from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class MariaDBUpgrade(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_downgrade_version_in_case_of_failure: DF.Check
		database_server: DF.Link
		downgrade_play: DF.Link | None
		skip_disk_snapshot: DF.Check
		snapshot: DF.Link | None
		status: DF.Literal["Pending", "Running", "Success", "Failure", "Recovering", "Recovered", "Fatal"]
		team: DF.Link | None
		upgrade_play: DF.Link | None
	# end: auto-generated types

	@property
	def database_server_doc(self) -> "DatabaseServer":
		return frappe.get_doc("Database Server", self.database_server)

	def before_insert(self):
		if self.auto_downgrade_version_in_case_of_failure and not self.skip_disk_snapshot:
			frappe.throw(
				"Auto downgrade in case of failure is enabled. Please uncheck it or enable skip disk snapshot to proceed without creating a disk snapshot.<br>Please contact support if you need any help.",
			)

	@frappe.whitelist()
	def start(self):
		if self.status != "Pending":
			frappe.throw(
				"This job has already been started.<br>Please contact support in case of any issues."
			)
		self.run.run_as_workflow()

	@flow
	def run(self):
		if self.status == "Pending":
			self.status = "Running"
			self.save()

		# Create Disk Snapshot as backup
		if not self.skip_disk_snapshot:
			self.create_disk_snapshot()

		# Upgrade MariaDB version
		self.upgrade_mariadb_version()

		# Downgrade MariaDB version in case of failure
		if self.auto_downgrade_version_in_case_of_failure and self.status == "Failure":
			self.downgrade_mariadb_version()

	@task
	def create_disk_snapshot(self):
		vm: VirtualMachine = frappe.get_doc("Virtual Machine", self.database_server_doc.virtual_machine)
		vm.create_snapshots(exclude_boot_volume=True)
		if len(vm.flags.created_snapshots) == 0:
			frappe.throw(
				"Failed to create a snapshot for the database server<br>Please contact support to resolve this issue."
			)
		self.snapshot = vm.flags.created_snapshots[0]
		self.save()

	@task(queue="long", timeout=3600)
	def upgrade_mariadb_version(self):
		database_server = self.database_server_doc
		ansible = Ansible(
			playbook="upgrade_mariadb.yml",
			server=database_server,
			user=database_server.ssh_user or "root",
			port=database_server.ssh_port or 22,
			variables={
				"server": database_server.name,
			},
		)
		assert ansible.play, "Failed to create Ansible play for MariaDB upgrade"
		self.upgrade_play = ansible.play
		self.save()

		if not frappe.flags.in_test:
			frappe.db.commit()
		play = ansible.run()
		if play.status == "Success":
			self.status = "Success"
		else:
			self.status = "Failure" if self.auto_downgrade_version_in_case_of_failure else "Fatal"
		self.save()

	@task(queue="long", timeout=3600)
	def downgrade_mariadb_version(self):
		database_server = self.database_server_doc
		ansible = Ansible(
			playbook="downgrade_mariadb_to_10_6.yml",
			server=database_server,
			user=database_server.ssh_user or "root",
			port=database_server.ssh_port or 22,
			variables={
				"server": database_server.name,
			},
		)
		assert ansible.play, "Failed to create Ansible play for MariaDB downgrade"
		self.downgrade_play = ansible.play
		self.save()

		play = ansible.run()
		if play.status == "Failure":
			self.status = "Fatal"
		else:
			self.status = "Recovered"
		self.save()
