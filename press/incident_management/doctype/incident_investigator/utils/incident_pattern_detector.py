import typing

import frappe

from press.runner import Status as StepStatus

if typing.TYPE_CHECKING:
	from press.press.incident_management.doctype.action_step.action_step import ActionStep

	from press.incident_management.doctype.incident_investigator.incident_investigator import (
		IncidentInvestigator,
	)
	from press.incident_management.doctype.incident_pattern.incident_pattern import (
		IncidentPattern,
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

	DB_REPEAT_THRESHOLD: typing.ClassVar = 3
	APP_REPEAT_THRESHOLD: typing.ClassVar = 3
	REPEAT_WINDOW_DAYS: typing.ClassVar = 7

	INVESTIGATION_STEPS: typing.ClassVar = [
		"has_high_disk_usage",
		"has_high_cpu_load",
		"has_high_memory_usage",
		"has_high_system_load",
	]

	def __init__(self, investigator: "IncidentInvestigator"):
		self.investigator = investigator

		# Pattern detection parameters
		self.detection_window = frappe.utils.add_to_date(days=-self.REPEAT_WINDOW_DAYS)

	def _create_pattern_record(
		self, server_type: str, server: str, cause_subset: list[str], investigations: list[str]
	):
		"""Will create a pattern record if one hasn't already been created for the same server and the causes this week"""

		server = (
			server if server_type == "Server" else frappe.db.get_value("Server", server, "database_server")
		)
		cause_key = ",".join(cause_subset)
		incident_pattern: IncidentPattern = frappe.new_doc("Incident Pattern")
		incident_pattern.server = server
		incident_pattern.server_type = server_type
		incident_pattern.causes = cause_key

		for investigation in investigations:
			incident_pattern.append("investigations", {"investigation": investigation})

		record_created_this_week = frappe.db.get_value(
			"Incident Pattern",
			{
				"server": server,
				"server_type": server_type,
				"causes": cause_key,
				"creation": (">=", self.detection_window),
			},
		)

		if not record_created_this_week:
			incident_pattern.save()

	def _detect_patterns(self, server: str, cause_subset: list[str]):
		IncidentInvestigator = frappe.qb.DocType("Incident Investigator")
		InvestigationStep = frappe.qb.DocType("Investigation Step")

		threshold = self.DB_REPEAT_THRESHOLD if server == "Database Server" else self.APP_REPEAT_THRESHOLD
		parentfield = (
			"database_investigation_steps" if server == "Database Server" else "server_investigation_steps"
		)
		cause_key = ",".join(cause_subset)
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
				& (IncidentInvestigator.creation >= self.detection_window)
			)
			.groupby(IncidentInvestigator.name)
			.having(likely_causes == cause_key)
		).run(pluck=True)

		if len(matching_incidents_count) >= threshold:
			self._create_pattern_record(
				server_type=server,
				server=self.investigator.server,
				cause_subset=cause_subset,
				investigations=matching_incidents_count,
			)

	def detect_patterns(self, step: "ActionStep"):
		"""Detects if the current incident matches any known patterns of resource contention."""
		step.status = StepStatus.Running
		step.save()

		try:
			database_server_causes = self.investigator.likely_causes.get("database", [])
			app_server_causes = self.investigator.likely_causes.get("server", [])
			is_unified_server = frappe.db.get_value("Server", self.investigator.server, "is_unified_server")

			# Detect patterns for application server causes
			if app_server_causes:
				self._detect_patterns("Server", app_server_causes)

			# Detect patterns for database server causes, we don't need to run this in case of unified servers, telemetry would be the same
			if database_server_causes and not is_unified_server:
				self._detect_patterns("Database Server", database_server_causes)

			step.status = StepStatus.Success

		except Exception as e:
			step.status = StepStatus.Failure
			step.output = frappe.safe_decode(str(e))

		finally:
			step.save()
