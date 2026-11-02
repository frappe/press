from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class AttachVolumeJob(PressJob):
	@flow
	def execute(self):
		self.attach_volume()

	@task
	def attach_volume(self):
		machine = self.virtual_machine_doc

		if machine.cloud_provider in ["AWS EC2", "OCI"]:
			machine.attach_new_volume(machine.size, machine.iops, machine.throughput)
		else:
			machine.attach_volume(size=100)
