from contextlib import suppress

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class StopAndStartServerJob(PressJob):
	@flow
	def execute(self):
		self.stop_virtual_machine()
		self.wait_for_virtual_machine_to_stop()

		self.start_virtual_machine()
		self.wait_for_virtual_machine_to_start()

		self.wait_for_server_to_be_accessible()

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
	def start_virtual_machine(self):
		with suppress(Exception):
			self.virtual_machine_doc.sync()

			if self.virtual_machine_doc.status == "Running":
				return

		self.virtual_machine_doc.start()

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
