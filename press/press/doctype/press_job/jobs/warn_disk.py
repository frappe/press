from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class WarnDiskJob(PressJob):
	@flow
	def execute(self):
		self.send_warning()

	@task
	def send_warning(self):
		mountpoint = self.arguments_dict.labels.get("mountpoint")
		self.server_doc.recommend_disk_increase(mountpoint=mountpoint)
