import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class UpgradeMariaDBJob(PressJob):
	@flow
	def execute(self):
		self.stop_mariadb()
		self.create_server_snapshot()
		self.upgrade_mariadb()

	@task(queue="long", timeout=1800)
	def stop_mariadb(self):
		self.server_doc._stop_mariadb(throw_on_failure=True)

	@task
	def create_server_snapshot(self):
		self.virtual_machine_doc.create_snapshots()

		snapshot = frappe.get_last_doc("Virtual Disk Snapshot", {"virtual_machine": self.virtual_machine})
		snapshot.add_comment(text="Before MariaDB Upgrade")

	@task(queue="long", timeout=1800)
	def upgrade_mariadb(self):
		self.server_doc._upgrade_mariadb(throw_on_failure=True)
