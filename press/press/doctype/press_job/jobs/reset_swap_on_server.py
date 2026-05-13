from contextlib import suppress

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class ResetSwapOnServerJob(PressJob):
	@flow
	def execute(self):
		with suppress(Exception):
			self.send_telegram_notification()

		self.reset_swap()

	@task
	def send_telegram_notification(self):
		telegram_message = frappe.get_doc("Press Settings").telegram_message
		telegram_message.enqueue(
			f"Resetting swap on [{self.server}]({frappe.utils.get_url_to_form(self.server_type, self.server)})",
			"Information",
		)

	@task(queue="long", timeout=1200)
	def reset_swap(self):
		self.server_doc.reset_swap(now=True)
