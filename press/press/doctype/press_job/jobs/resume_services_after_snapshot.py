import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task


class ResumeServicesAfterSnapshotJob(PressJob):
	@flow
	def execute(self):
		self.start_docker_daemon()
		self.start_mariadb_service()

	@task(queue="long", timeout=1200)
	def start_docker_daemon(self):
		server_snapshot = self.arguments_dict.get("server_snapshot")

		if self.server_type == "Server" and self.arguments_dict.get("is_consistent_snapshot", False):
			server = frappe.get_doc("Server", self.server)
			output = server.ansible_run("systemctl start docker")
			if not (output and output.get("status") == "Success"):
				raise Exception("Failed to start docker daemon")

		frappe.db.set_value(
			"Server Snapshot",
			server_snapshot,
			"app_server_services_started",
			True,
			update_modified=False,
		)

	@task(queue="long", timeout=3600)
	def start_mariadb_service(self):
		server_snapshot = self.arguments_dict.get("server_snapshot")

		if self.server_type == "Database Server" and self.arguments_dict.get("is_consistent_snapshot", False):
			server = frappe.get_doc("Database Server", self.server)
			output = server.ansible_run("systemctl start mariadb")
			if not (output and output.get("status") == "Success"):
				raise Exception("Failed to start mariadb service")

		frappe.db.set_value(
			"Server Snapshot",
			server_snapshot,
			"database_server_services_started",
			True,
			update_modified=False,
		)
