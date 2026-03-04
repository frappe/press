import typing

import frappe

if typing.TYPE_CHECKING:
	from press.incident_management.doctype.incident_investigator.incident_investigator import (
		IncidentInvestigator,
	)

from frappe.query_builder.functions import GroupConcat


class IncidentPatternDetector:
	"""
	Detects recurring resource contention patterns across Incident Investigator docs
	to surface upgrade or investigation recommendations to customers.

	Writing elaborate docs since this is quite confusing

	HOW IT WORKS
	------------
	Pattern matching is based on `likely_causes` fingerprints only for now — two incidents are
	considered similar if they produce identical likely_causes (same server, database,
	sets).

	A pattern is triggered when the same fingerprint appears >= threshold times
	within the detection window on the same server.

	GROUND RULES
	------------
	Database Server:
		- Trigger : >= 2 incidents with database likely_causes in 7 days
		- Action  : Notify customer to run a slow query analysis
		- Message : "We noticed your database server has been under stress multiple times
					this week. We recommend running a slow query analysis to identify
					and resolve long-running queries, if there aren't any concider a plan upgrade."

	App Server:
		- Trigger : >= 2 incidents with server likely_causes (OOM, high CPU, high memory)
					in 7 days
		- Action  : Notify customer to consider autoscaling or a plan upgrade
		- Message : "We noticed your app server has been under stress multiple times
					this week. We recommend enabling autoscaling or upgrading your
					plan to handle the load."
	"""

	DB_REPEAT_THRESHOLD: typing.ClassVar = 2
	APP_REPEAT_THRESHOLD: typing.ClassVar = 2
	REPEAT_WINDOW_DAYS: typing.ClassVar = 7

	INVESTIGATION_STEPS: typing.ClassVar = [
		"has_high_disk_usage",
		"has_high_cpu_load",
		"has_high_memory_usage",
		"has_high_system_load",
	]

	def __init__(self, investigator: "IncidentInvestigator"):
		self.investigator = investigator
		self.server = investigator.server
		self.now = frappe.utils.now_datetime()

		# Pattern detection parameters
		self.detection_window = frappe.utils.add_to_date(days=-7)

	def _detect_patterns(self, server: str, cause_subset: list[str]):
		IncidentInvestigator = frappe.qb.DocType("Incident Investigator")
		InvestigationStep = frappe.qb.DocType("Investigation Step")

		threshold = self.DB_REPEAT_THRESHOLD if server == "database" else self.APP_REPEAT_THRESHOLD
		parentfield = "database_investigation_steps" if server == "database" else "server_investigation_steps"
		cause_key = ",".join(sorted(cause_subset))
		likely_causes = GroupConcat(InvestigationStep.method).distinct()
		matching_incidents_count = (
			frappe.qb.from_(IncidentInvestigator)
			.join(InvestigationStep)
			.on(IncidentInvestigator.name == InvestigationStep.parent)
			.select(IncidentInvestigator.name)
			.where(
				(InvestigationStep.is_likely_cause == 1)
				& (InvestigationStep.parentfield == parentfield)
				& (IncidentInvestigator.server == self.investigator.server)
				& (IncidentInvestigator.creation >= self.now - self.detection_window)
			)
			.groupby(IncidentInvestigator.name)
			.having(likely_causes == cause_key)
		).run(pluck=True)

		if len(matching_incidents_count) >= threshold:
			frappe.throw(
				"We noticed your database server has been under stress multiple times this week. "
				"We recommend running a slow query analysis to identify and resolve "
				"long-running queries, if there aren't any consider a plan upgrade."
			)

	def detect_patterns(self):
		"""Detects if the current incident matches any known patterns of resource contention"""
		database_server_causes = self.investigator.likely_causes["database"]
		app_server_causes = self.investigator.likely_causes["server"]

		if database_server_causes:
			self._detect_patterns("database", database_server_causes)

		if app_server_causes:
			self._detect_patterns("server", app_server_causes)
