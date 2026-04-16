from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class AutoScaleDownApplicationServerJob(PressJob):
	@flow
	def execute(self):
		if self.server_type != "Server":
			return

		self.scale_down()

	@task
	def scale_down(self):
		"""Scale Down Application Server"""
		if not self.server_doc.scaled_up:
			return

		self.server_doc.scale_down(is_automatically_triggered=True)
