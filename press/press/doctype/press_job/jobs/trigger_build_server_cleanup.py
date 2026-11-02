from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class TriggerBuildServerCleanupJob(PressJob):
	@flow
	def execute(self):
		if self.server_type != "Server" or not self.server_doc.use_for_build:
			return

		self.trigger_build_server_cleanup()

	@task
	def trigger_build_server_cleanup(self):
		if not self.server_doc.use_for_build:
			return

		self.server_doc.prune_docker_system()
