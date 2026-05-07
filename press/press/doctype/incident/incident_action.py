# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.bench.bench import Bench
from press.press.doctype.database_server.database_server import DatabaseServer

if TYPE_CHECKING:
	from press.press.doctype.incident.incident import Incident


# Job types that are known to get stuck during db reboot/upgrade and are safe
# to cancel.
STUCK_JOB_TYPES = ("Fetch Database Table Schema", "Backup Site", "Restore Site")
MAX_STUCK_JOBS_TO_CANCEL = 2  # only 2 workers


class IncidentAction:
	"""Remediation actions an operator can trigger on an incident."""

	def __init__(self, incident: Incident):
		self.incident = incident

	def reboot_database_server(self):
		db_server_name = frappe.db.get_value("Server", self.incident.server, "database_server")
		if not db_server_name:
			frappe.throw("No database server found for this server")

		db_server = DatabaseServer("Database Server", db_server_name)
		try:
			db_server.reboot_with_serial_console()
		except NotImplementedError:
			db_server.reboot()

		self.incident._add_likely_cause("Rebooted database server.")
		self.incident.save()

	def cancel_stuck_jobs(self):
		"""Cancel up to `MAX_STUCK_JOBS_TO_CANCEL` of the most likely-stuck jobs."""

		stuck_jobs = frappe.get_all(
			"Agent Job",
			{
				"status": "Running",
				"server": self.incident.server,
				"job_type": ("in", STUCK_JOB_TYPES),
			},
			["name", "job_type"],
			limit=MAX_STUCK_JOBS_TO_CANCEL,
		)
		for stuck_job in stuck_jobs:
			AgentJob("Agent Job", stuck_job.name).cancel_job()
			self.incident._add_likely_cause(f"Cancelled stuck {stuck_job.job_type} job {stuck_job.name}")
		self.incident.save()

	def restart_down_benches(self):
		"""Restart all benches on the server that are down."""
		for bench in self.incident.down_benches:
			if bench.current_sites_down == 0:
				continue  # skip if bench is not down
			Bench("Bench", bench.bench_name).restart()
			self.incident._add_likely_cause(f"Restarted bench {bench.bench}")

		self.incident.save()
