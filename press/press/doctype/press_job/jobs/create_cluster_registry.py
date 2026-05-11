from typing import TYPE_CHECKING

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

if TYPE_CHECKING:
	from press.press.doctype.cluster_registry.cluster_registry import ClusterRegistry
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class CreateClusterRegistryJob(PressJob):
	@flow
	def execute(self):
		self.provision_cluster_registry()
		self.wait_for_server_to_start()
		self.execute_setup_steps()

	@task
	def provision_cluster_registry(self):
		virtual_machine: VirtualMachine = frappe.get_doc("Virtual Machine", self.virtual_machine)
		virtual_machine.provision()

	@task
	def wait_for_server_to_start(self):
		retry_later = True
		try:
			self.virtual_machine_doc.sync()
		except (frappe.QueryDeadlockError, frappe.QueryTimeoutError, frappe.TimestampMismatchError):
			retry_later = True
		except Exception as e:
			if "rate_limit_exceeded" in str(e):
				retry_later = True
			else:
				raise e

		if self.virtual_machine_doc.status == "Running":
			retry_later = False

		if retry_later:
			self.defer_current_task()

	@task
	def execute_setup_steps(self):
		cluster_registry: ClusterRegistry = frappe.get_doc("Cluster Registry", self.server)
		cluster_registry.setup_server()
