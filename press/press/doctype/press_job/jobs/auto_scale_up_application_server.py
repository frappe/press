from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class AutoScaleUpApplicationServerJob(PressJob):
	@flow
	def execute(self):
		if self.server_type != "Server":
			return
		self.scale_up()

	@task
	def scale_up(self):
		"""Scale Up Application Server"""
		if self.server_doc.scaled_up:
			return

		self.server_doc.scale_up(is_automatically_triggered=True)
