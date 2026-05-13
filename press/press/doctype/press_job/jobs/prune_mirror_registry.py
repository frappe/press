from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class PruneMirrorRegistryJob(PressJob):
	@flow
	def execute(self):
		if self.server_type != "Registry Server":
			return

		self.prune_mirror_registry()

	@task(queue="long", timeout=3600)
	def prune_mirror_registry(self):
		self.server_doc._prune_mirror_registry(throw_on_failure=True)
