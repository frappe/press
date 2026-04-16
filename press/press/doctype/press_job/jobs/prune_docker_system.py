from contextlib import suppress

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class PruneDockerSystemJob(PressJob):
	@flow
	def execute(self):
		with suppress(Exception):
			self.send_telegram_notification()

		self.prune_docker_system()

	@task
	def send_telegram_notification(self):
		telegram_message = frappe.get_doc("Press Settings").telegram_message
		telegram_message.enqueue(
			f"Pruning docker cache on [{self.server}]({frappe.utils.get_url_to_form(self.server_type, self.server)})",
			"Information",
		)

	@task(queue="long", timeout=8000)
	def prune_docker_system(self):
		self.server_doc._prune_docker_system(throw_on_failure=True)
