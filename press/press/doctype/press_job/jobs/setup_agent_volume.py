from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import frappe
import requests

from press.agent import Agent, AgentRequestSkippedException
from press.press.doctype.agent_job.agent_job import handle_polled_jobs, poll_random_jobs
from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

if TYPE_CHECKING:
	from press.workflow_engine.doctype.press_workflow.press_workflow import PressWorkflow

# A job that is still Running after this is most likely a stale record, not a real job
MAX_WAIT_FOR_AGENT_JOBS = timedelta(hours=12)


class SetupAgentVolumeJob(PressJob):
	@flow
	def execute(self):
		self.halt_agent_jobs()
		self.wait_for_agent_jobs()
		self.setup_agent_volume()
		self.start_agent_jobs()

	@task
	def halt_agent_jobs(self):
		# New agent jobs wait as Undelivered, so the play does not stop a worker in the middle of a job
		frappe.db.set_value(self.server_type, self.server, "halt_agent_jobs", True)

	@task
	def wait_for_agent_jobs(self):
		running_jobs = frappe.get_all(
			"Agent Job",
			fields=["name", "job_id", "status", "callback_failure_count"],
			filters={"status": ("in", ["Pending", "Running"]), "job_id": ("!=", 0), "server": self.server},
		)
		if not running_jobs:
			return

		if frappe.utils.now_datetime() - frappe.utils.get_datetime(self.creation) > MAX_WAIT_FOR_AGENT_JOBS:
			frappe.throw(
				f"Agent jobs are still running after {MAX_WAIT_FOR_AGENT_JOBS}: "
				+ ", ".join(job.name for job in running_jobs)
			)

		# poll_pending_jobs skips servers with halted agent jobs, so this task polls them
		try:
			polled_jobs = poll_random_jobs(
				Agent(self.server, server_type=self.server_type), [job.job_id for job in running_jobs]
			)
			handle_polled_jobs(polled_jobs or [], running_jobs)
		except (AgentRequestSkippedException, requests.RequestException):
			pass  # The agent is unreachable for now. Try again on the next run.

		self.defer_current_task()

	# Agent workers get up to 1500 seconds (stopwaitsecs) to stop
	@task(queue="long", timeout=3600)
	def setup_agent_volume(self):
		self.server_doc._setup_agent_volume()

	@task
	def start_agent_jobs(self):
		frappe.db.set_value(self.server_type, self.server, "halt_agent_jobs", False)

	def on_press_job_failure(self, workflow: PressWorkflow):
		self.start_agent_jobs()
