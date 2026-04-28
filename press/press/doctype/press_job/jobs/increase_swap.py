from contextlib import suppress

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class IncreaseSwapJob(PressJob):
	@flow
	def execute(self):
		with suppress(Exception):
			self.send_telegram_notification()

		self.add_swap_on_server()

	@task
	def send_telegram_notification(self):
		telegram_message = frappe.get_doc("Press Settings").telegram_message
		telegram_message.enqueue(
			f"Increasing swap on [{self.server}]({frappe.utils.get_url_to_form(self.server_type, self.server)})",
			"Information",
		)

	@task(queue="long", timeout=1200)
	def add_swap_on_server(self):
		self.server_doc.increase_swap_locked(swap_size=4, throw_on_failure=True)
