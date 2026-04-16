from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class AutoScaleApplicationServerJob(PressJob):
	@flow
	def execute(self):
		if self.server_type != "Server":
			return

		self.scale_app_server()

	@task
	def scale_app_server(self):
		"""Scale Application Server"""
		self.server_doc.scale_up()
