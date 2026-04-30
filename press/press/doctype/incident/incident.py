# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from contextlib import suppress
from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils.data import cint

from press.press.doctype.bench.bench import Bench
from press.press.doctype.telegram_message.telegram_message import TelegramMessage

if TYPE_CHECKING:
	from frappe.types import DF

	from press.incident_management.doctype.incident_investigator.incident_investigator import (
		IncidentInvestigator,
	)
	from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import AlertmanagerWebhookLog
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.incident.incident_action import IncidentAction
	from press.press.doctype.incident.incident_analysis import IncidentAnalysis
	from press.press.doctype.incident.incident_communication import IncidentCommunication
	from press.press.doctype.incident_settings.incident_settings import IncidentSettings
	from press.press.doctype.incident_settings_self_hosted_user.incident_settings_self_hosted_user import (
		IncidentSettingsSelfHostedUser,
	)
	from press.press.doctype.incident_settings_user.incident_settings_user import (
		IncidentSettingsUser,
	)
	from press.press.doctype.server.server import Server


INCIDENT_ALERT = "Sites Down"  # TODO: make it a field or child table somewhere #
# Scope at which an incident is grouped. Can be bench/cluster/server. Not site.
INCIDENT_SCOPE = "server"


class Incident(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.incident_alerts.incident_alerts import IncidentAlerts
		from press.press.doctype.incident_finding.incident_finding import IncidentFinding
		from press.press.doctype.incident_updates.incident_updates import IncidentUpdates

		acknowledged_at: DF.Datetime | None
		acknowledged_by: DF.Link | None
		alert: DF.Link | None
		alerts: DF.Table[IncidentAlerts]
		called_customer: DF.Check
		cluster: DF.Link | None
		confirmed_at: DF.Datetime | None
		description: DF.TextEditor | None
		findings: DF.Table[IncidentFinding]
		investigation: DF.Link | None
		likely_cause: DF.Text | None
		phone_call: DF.Check
		resolved_at: DF.Datetime | None
		resource: DF.DynamicLink | None
		resource_type: DF.Link | None
		server: DF.Link | None
		sms_sent: DF.Check
		status: DF.Literal[
			"Validating",
			"Confirmed",
			"Acknowledged",
			"Investigating",
			"Resolved",
			"Auto-Resolved",
			"Press-Resolved",
		]
		subtype: DF.Literal["High CPU: user", "High CPU: iowait", "Disk full"]
		type: DF.Literal["Database Down", "Server Down", "Proxy Down"]
		updates: DF.Table[IncidentUpdates]
	# end: auto-generated types

	@cached_property
	def settings(self) -> IncidentSettings:
		return frappe.get_cached_doc("Incident Settings")

	@cached_property
	def communication(self) -> IncidentCommunication:
		from press.press.doctype.incident.incident_communication import IncidentCommunication

		return IncidentCommunication(self)

	@cached_property
	def analysis(self) -> IncidentAnalysis:
		from press.press.doctype.incident.incident_analysis import IncidentAnalysis

		return IncidentAnalysis(self)

	@cached_property
	def action(self) -> IncidentAction:
		from press.press.doctype.incident.incident_action import IncidentAction

		return IncidentAction(self)

	@property
	def monitor_server(self):
		# Proxied through the analysis helper, which owns the Grafana / Prometheus client.
		return self.analysis.monitor_server

	@cached_property
	def database_server(self) -> str:
		return str(frappe.db.get_value("Server", self.server, "database_server"))

	@cached_property
	def proxy_server(self) -> str:
		return str(frappe.db.get_value("Server", self.server, "proxy_server"))

	@property
	def incident_scope(self):
		return getattr(self, INCIDENT_SCOPE)

	@property
	def total_instances(self) -> int:
		return frappe.db.count(
			"Site",
			{"status": "Active", INCIDENT_SCOPE: self.incident_scope},
		)

	@cached_property
	def sites_down(self) -> list[str]:
		return self.monitor_server.get_sites_down_for_server(str(self.server))

	@cached_property
	def down_bench(self):
		down_benches = self.monitor_server.get_benches_down_for_server(str(self.server))
		return down_benches[0] if down_benches else None

	@cached_property
	def is_ignore_incident_for_server(self) -> bool:
		ignore_till = frappe.db.get_value("Server", self.server, "ignore_incidents_till")
		return bool(ignore_till and ignore_till > frappe.utils.now_datetime())

	def validate(self):
		if not self.phone_call and self.settings.phone_call_alerts:
			self.phone_call = True

	def after_insert(self):
		self._create_investigation_if_possible()
		self.communication.send_sms_to_on_call_engineers()
		self.communication.send_email_notification()

	def on_update(self):
		if not self.has_value_changed("status"):
			return

		current_datetime = frappe.utils.now_datetime()
		self.communication.send_email_notification()

		if self.status in ("Resolved", "Auto-Resolved"):
			self.db_set("resolved_at", current_datetime)
		elif self.status == "Confirmed" and not self.confirmed_at:
			self.db_set("confirmed_at", current_datetime)
			self.call_customers()

	def confirm(self, save: bool = True):
		self.status = "Confirmed"
		self.analysis.identify_affected_resource()  # assume 1 resource; Occam's razor
		self.analysis.categorize_problem()
		self.analysis.capture_grafana_dashboards()
		if save:
			self.save()

	def acknowledge(self, user: str, save: bool = True):
		self.acknowledged_by = user
		self.acknowledged_at = frappe.utils.now_datetime()
		self.status = "Acknowledged"
		if save:
			self.save()

	def resolve(self, save: bool = True):
		self.status = "Auto-Resolved" if self.status == "Validating" else "Resolved"
		self.create_log_for_server(is_resolved=True)
		if save:
			self.save()

	def check_resolved(self):
		try:
			last_resolved: AlertmanagerWebhookLog = frappe.get_last_doc(
				"Alertmanager Webhook Log",
				{
					"status": "Resolved",
					"group_key": ("like", f"%{self.incident_scope}%"),
					"alert": self.alert,
				},
			)
		except frappe.DoesNotExistError:
			return

		if not last_resolved.is_enough_firing:
			self.resolve()

	def escalate_to_on_call_engineers_if_needed(self):
		"""Escalate the incident by paging on-call engineers if escalation thresholds are met."""
		now = frappe.utils.now_datetime()

		call_threshold = timedelta(seconds=self.settings.call_threshold_seconds)
		recall_threshold = timedelta(seconds=self.settings.call_repeat_interval_seconds)

		time_to_call = self.status == "Confirmed" and now - self.confirmed_at > call_threshold
		time_to_call_again = self.status == "Acknowledged" and now - self.acknowledged_at > recall_threshold

		if not (time_to_call or time_to_call_again):
			return

		if self.investigation and frappe.get_single_value("Press Settings", "execute_incident_action"):
			# It's worthy to wait for investigator if incident action execution is enabled
			# Else, let it run in background and do the necessary actions without blocking escalation

			investigator: IncidentInvestigator = frappe.get_doc("Incident Investigator", self.investigation)
			if investigator.status != "Completed" and investigator.modified > now - timedelta(
				seconds=self.settings.deadline_for_investigator_actions_seconds
			):
				# If investigation is still ongoing, then don't escalate yet
				# But, there will be a deadline, within that if investigation is not completed
				# then we will escalate anyway because we don't want incidents to be stuck
				return

			# Investigation is complete; wait a bit longer if any actions were just taken.
			wait_window = timedelta(seconds=cint(self.settings.wait_time_post_investigator_actions))
			if investigator.action_steps and investigator.modified > now - wait_window:
				return

		self.create_log_for_server()
		self.call_on_call_engineers()

	def create_log_for_server(self, is_resolved: bool = False):
		"""Create an incident log on the server activity for confirmed incidents and their resolution."""
		try:
			incidence_server: Server | DatabaseServer = frappe.get_cached_doc(
				self.resource_type, self.resource
			)
		except Exception:
			if not self.server:
				return
			incidence_server = frappe.get_cached_doc("Server", self.server)

		incidence_server.create_log(
			"Incident",
			f"{self.alert} resolved" if is_resolved else f"{self.alert} reported",
		)

	# ==================================================================
	# Actions
	# ==================================================================

	@frappe.whitelist()
	def regather_info_and_screenshots(self):
		self.analysis.identify_affected_resource()
		self.analysis.categorize_problem()
		self.analysis.capture_grafana_dashboards()

	@frappe.whitelist()
	def get_down_site(self):
		return self.sites_down[0] if self.sites_down else None

	@frappe.whitelist()
	def reboot_database_server(self):
		self.action.reboot_database_server()

	@frappe.whitelist()
	def cancel_stuck_jobs(self):
		self.action.cancel_stuck_jobs()

	@frappe.whitelist()
	def restart_down_benches(self):
		self.action.restart_down_benches()

	def call_on_call_engineers(self, run_in_background: bool = True):
		if run_in_background:
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"call_on_call_engineers",
				queue=self.settings.custom_queue or "default",
				timeout=600,
				enqueue_after_commit=True,
				at_front=True,
				job_id=f"incident||{self.name}||call_on_call_engineers",
				deduplicate=True,
				run_in_background=False,
			)
			return

		self.communication.call_on_call_engineers()

	def call_customers(self, run_in_background: bool = True):
		if run_in_background:
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"call_customers",
				queue=self.settings.custom_queue or "default",
				enqueue_after_commit=True,
				at_front=True,
				job_id=f"incident||{self.name}||call_customers",
				deduplicate=True,
				run_in_background=False,
			)
			return

		self.communication.call_customers()

	def add_acknowledgment_update(
		self,
		human: IncidentSettingsUser | IncidentSettingsSelfHostedUser,
		call_status: str | None = None,
		acknowledged=False,
	):
		"""Adds a new update to the Incident Document."""
		if acknowledged:
			update_note = f"Acknowledged by {human.user}"
			self.acknowledge(human.user, save=False)
		else:
			update_note = f"Acknowledgement failed for {human.user}"

		if call_status:
			update_note += f" with call status {call_status}"

		self.append(
			"updates",
			{
				"update_note": update_note,
				"update_time": frappe.utils.now(),
			},
		)
		self.save()

	# ==================================================================
	# Helpers
	# ==================================================================

	def _add_description(self, description: str):
		if not self.description:
			self.description = ""
		self.description += "<p>" + description + "</p>"

	def _add_finding(self, label: str, value):
		"""Record a key-value finding on the incident's `findings` child table."""
		self.append("findings", {"label": label, "value": str(value)})

	def _add_likely_cause(self, cause: str):
		self.likely_cause = (self.likely_cause or "") + cause + "\n"

	def _create_investigation_if_possible(self):
		"""Investigations have a cool off period of 5m, so consecutive incidents on the
		same server might not trigger investigations."""
		with suppress(frappe.ValidationError):
			incident_investigator = frappe.get_doc(
				{"doctype": "Incident Investigator", "incident": self.name, "server": self.server}
			)
			incident_investigator.insert(ignore_permissions=True)
			self.investigation = incident_investigator.name
			self.save()

	def _comment_bench_web_err_log(self, bench_name: str):
		"""Add the last 100 lines of `web.error.log` from the bench as a comment."""
		try:
			log = Bench("Bench", bench_name).get_server_log("web.error.log")["web.error.log"]
		except Exception as e:
			log = f"Error fetching web.error.log: {e!s}"

		last_lines = "\n".join(log.splitlines()[-100:])
		self.add_comment(
			"Comment",
			f"""Last 100 lines of web.error.log for bench {bench_name}:<br/><br/>
<pre class="ql-code-block-container">
{last_lines}
</pre>
""",
		)


# ---------------------------------------------------------------------------
# Scheduled Jobs
# ---------------------------------------------------------------------------


def validate_incidents():
	settings: IncidentSettings = frappe.get_cached_doc("Incident Settings")
	validating_incidents = frappe.get_all(
		"Incident",
		filters={
			"status": "Validating",
			"creation": (
				"<",
				frappe.utils.now_datetime() - timedelta(seconds=settings.confirmation_threshold_seconds),
			),
		},
		fields=["name", "creation"],
	)
	for i in validating_incidents:
		try:
			incident = Incident("Incident", i.name)
			incident.confirm()
		except Exception as e:
			frappe.log_error(f"Error confirming incident {i.name}: {e!s}")


def resolve_incidents():
	ongoing_incidents = frappe.get_all(
		"Incident",
		filters={"status": ("in", ["Validating", "Confirmed", "Acknowledged"])},
		pluck="name",
	)
	for incident_name in ongoing_incidents:
		try:
			incident = Incident("Incident", incident_name)
			incident.check_resolved()
			incident.escalate_to_on_call_engineers_if_needed()
		except Exception as e:
			frappe.log_error(f"Error resolving/escalating incident {incident_name}: {e!s}")


def notify_ignored_servers():
	servers = frappe.qb.DocType("Server")
	ignored_servers = (
		frappe.qb.from_(servers)
		.select(servers.name, servers.ignore_incidents_till)
		.where(servers.status == "Active")
		.where(servers.ignore_incidents_till.isnotnull())
		.where(servers.ignore_incidents_till >= frappe.utils.now_datetime())
		.run(as_dict=True)
	)
	if not ignored_servers:
		return

	message = "The following servers are being ignored for incidents:\n\n"
	for server in ignored_servers:
		message += f"{server.name} till {frappe.utils.pretty_date(server.ignore_incidents_till)}\n"
	message += "\n@adityahase @balamurali27 @saurabh6790 @tanmoysrt\n"
	TelegramMessage.enqueue(message)


def on_doctype_update():
	frappe.db.add_index("Incident", ["alert", "server", "status"])
