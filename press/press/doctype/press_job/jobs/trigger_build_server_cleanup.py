from datetime import timedelta

import frappe

from press.press.doctype.deploy_candidate.utils import get_active_build_count_by_build_server
from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

# The disk is at 90% when this job starts. Do not wait longer than this for builds to finish.
MAX_WAIT_FOR_BUILDS = timedelta(minutes=30)


class TriggerBuildServerCleanupJob(PressJob):
	@flow
	def execute(self):
		if self.server_type != "Server" or not self.server_doc.use_for_build:
			return

		self.wait_for_running_builds()
		self.trigger_build_server_cleanup()

	@task
	def wait_for_running_builds(self):
		# New builds go to other servers while this job is open. See get_build_server_with_least_active_builds.
		if not get_active_build_count_by_build_server().get(self.server):
			return

		if frappe.utils.now_datetime() - frappe.utils.get_datetime(self.creation) < MAX_WAIT_FOR_BUILDS:
			self.defer_current_task()

	@task(queue="long", timeout=8000)
	def trigger_build_server_cleanup(self):
		if not self.server_doc.use_for_build:
			return

		# Prune in this task, so that the job stays open (and new builds stay away) until the prune ends
		self.server_doc._prune_docker_system()
