# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from base64 import b64encode
from contextlib import suppress
from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
import requests
from frappe.model.document import Document
from frappe.utils.data import cint
from frappe.utils.synchronization import filelock
from playwright.sync_api import Page, sync_playwright

from press.api.server import prometheus_query
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.bench.bench import Bench
from press.press.doctype.database_server.database_server import DatabaseServer
from press.press.doctype.server.server import MARIADB_DATA_MNT_POINT
from press.press.doctype.telegram_message.telegram_message import TelegramMessage

if TYPE_CHECKING:
	from frappe.types import DF

	from press.incident_management.doctype.incident_investigator.incident_investigator import (
		IncidentInvestigator,
	)
	from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import AlertmanagerWebhookLog
	from press.press.doctype.incident.incident_communication import IncidentCommunication
	from press.press.doctype.incident_settings.incident_settings import IncidentSettings
	from press.press.doctype.incident_settings_self_hosted_user.incident_settings_self_hosted_user import (
		IncidentSettingsSelfHostedUser,
	)
	from press.press.doctype.incident_settings_user.incident_settings_user import (
		IncidentSettingsUser,
	)
	from press.press.doctype.monitor_server.monitor_server import MonitorServer
	from press.press.doctype.press_settings.press_settings import PressSettings
	from press.press.doctype.server.server import Server


INCIDENT_ALERT = "Sites Down"  # TODO: make it a field or child table somewhere #
INCIDENT_SCOPE = (
	"server"  # can be bench, cluster, server, etc. Not site, minor code changes required for that
)


class Incident(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.incident_alerts.incident_alerts import IncidentAlerts
		from press.press.doctype.incident_updates.incident_updates import IncidentUpdates

		acknowledged_by: DF.Link | None
		alert: DF.Link | None
		alerts: DF.Table[IncidentAlerts]
		called_customer: DF.Check
		cluster: DF.Link | None
		confirmed_at: DF.Datetime | None
		description: DF.TextEditor | None
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
	def database_server(self):
		return str(frappe.db.get_value("Server", self.server, "database_server"))

	@cached_property
	def proxy_server(self):
		return str(frappe.db.get_value("Server", self.server, "proxy_server"))

	@cached_property
	def is_ignore_incident_for_server(self) -> bool:
		ignore_till = frappe.db.get_value("Server", self.server, "ignore_incidents_till")
		return ignore_till and ignore_till > frappe.utils.now_datetime()

	@cached_property
	def settings(self) -> IncidentSettings:
		return frappe.get_cached_doc("Incident Settings")

	@cached_property
	def communication(self) -> IncidentCommunication:
		from press.press.doctype.incident.incident_communication import IncidentCommunication

		return IncidentCommunication(self)

	def validate(self):
		if not self.phone_call and self.settings.phone_call_alerts:
			self.phone_call = True

	def after_insert(self):
		"""
		Start investigating the incident since we have already waited 5m before creating it
		send sms and email notifications, also add a dashboard banner in case of insert taking users to the status page
		"""
		self.create_investigation_if_possible()
		self.communication.send_sms_to_on_call_engineers()
		self.communication.send_email_notification()
		self.identify_affected_resource()

	def create_investigation_if_possible(self):
		"""Investigations have a cool off period of 5m therefore consecutive incidents on the same server might not trigger investigations"""
		with suppress(frappe.ValidationError):
			incident_investigator = frappe.get_doc(
				{"doctype": "Incident Investigator", "incident": self.name, "server": self.server}
			)
			incident_investigator.insert(ignore_permissions=True)
			self.investigation = incident_investigator.name
			self.save()

	def on_update(self):
		if self.has_value_changed("status"):
			current_datetime = frappe.utils.now_datetime()
			self.communication.send_email_notification()
			if self.status == "Resolved" or self.status == "Auto-Resolved":
				self.db_set("resolved_at", current_datetime)
			elif self.status == "Confirmed" and not self.confirmed_at:
				self.db_set("confirmed_at", current_datetime)
				self.communication.call_customers()

	def get_load(self, name) -> float:
		timespan = self.settings.confirmation_threshold_seconds
		load = prometheus_query(
			f"""avg_over_time(node_load5{{instance="{name}", job="node"}}[{timespan}s])""",
			lambda x: x,
			"Asia/Kolkata",
			timespan,
			timespan + 1,
		)["datasets"]
		if load:
			ret = load[0]["values"][-1]
		else:
			ret = -1  # no response
		self.add_description(f"{name} load avg(5m): {ret if ret != -1 else 'No data'}")
		return ret

	def check_high_load(self, resource_type: str, resource: str):
		load = self.get_load(resource)
		if load < 0:  # no response, likely down
			return resource_type, resource

		vm_name = str(frappe.db.get_value(resource_type, resource, "virtual_machine"))
		vcpu = int(frappe.db.get_value("Virtual Machine", vm_name, "vcpu") or 16)

		if load > 3 * vcpu:
			return resource_type, resource
		return False, False

	def identify_affected_resource(self):
		"""
		Identify the affected resource and set the resource field
		"""
		self.add_description(f"{len(self.sites_down)} / {self.total_instances} sites down:")
		self.add_description("\n".join(self.sites_down))

		for resource_type, resource in [
			("Database Server", self.database_server),
			("Server", self.server),
			("Proxy Server", self.proxy_server),
		]:
			if self.check_high_load(resource_type, resource) != (False, False):
				self.resource_type = resource_type
				self.resource = resource
				return

	def confirm(self):
		self.status = "Confirmed"
		self.identify_affected_resource()  # assume 1 resource; Occam's razor
		self.identify_problem()
		self.take_grafana_screenshots()
		if self.down_bench:
			self.comment_bench_web_err_log(self.down_bench)
		self.save()

	def get_last_n_lines_of_log(self, log: str, n: int = 100) -> str:
		# get last n lines of log
		lines = log.splitlines()
		return "\n".join(lines[-n:]) if len(lines) > n else log

	def comment_bench_web_err_log(self, bench_name: str):
		# get last 100 lines of web.error.log from the bench
		bench: Bench = Bench("Bench", bench_name)
		try:
			log = bench.get_server_log("web.error.log")["web.error.log"]
		except Exception as e:
			log = f"Error fetching web.error.log: {e!s}"

		self.add_comment(
			"Comment",
			f"""Last 100 lines of web.error.log for bench {bench_name}:<br/><br/>
<pre class="ql-code-block-container">
{self.get_last_n_lines_of_log(log)}
</pre>
""",
		)

	@frappe.whitelist()
	def regather_info_and_screenshots(self):
		self.identify_affected_resource()
		self.identify_problem()
		self.take_grafana_screenshots()

	def get_cpu_state(self, resource: str) -> tuple[str, float]:
		"""
		Returns the prominent CPU state and its percentage
		"""
		timespan = self.settings.confirmation_threshold_seconds
		cpu_info = prometheus_query(
			f"""avg by (mode)(rate(node_cpu_seconds_total{{instance="{resource}", job="node"}}[{timespan}s])) * 100""",
			lambda x: x["mode"],
			"Asia/Kolkata",
			timespan,
			timespan + 1,
		)["datasets"]
		mode_cpus: dict[str, int] = {x["name"]: x["values"][-1] for x in cpu_info} or {
			"user": -1,
			"idle": -1,
			"softirq": -1,
			"iowait": -1,
		}  # no info;
		max_mode: str = max(mode_cpus, key=lambda k: mode_cpus[k])
		max_cpu = mode_cpus[max_mode]
		self.add_description(f"CPU Usage: {max_mode} {max_cpu if max_cpu > 0 else 'No data'}")
		return max_mode, mode_cpus[max_mode]

	def add_description(self, description: str):
		if not self.description:
			self.description = ""
		self.description += "<p>" + description + "</p>"

	def add_corrective_suggestion(self, suggestion):
		self.append(
			"corrective_suggestions",
			{
				"suggestion": suggestion,
			},
		)

	def add_preventive_suggestion(self, suggestion):
		self.append(
			"preventive_suggestions",
			{
				"suggestion": suggestion,
			},
		)

	def categorize_db_cpu_issues(self, cpu_state):
		self.type = "Database Down"

		if cpu_state == "user":
			self.subtype = "High CPU: user"
		elif cpu_state == "iowait":
			self.subtype = "High CPU: iowait"

	def categorize_server_cpu_issues(self, cpu_state):
		self.type = "Server Down"
		if cpu_state == "user":
			self.update_user_server_issue()
		elif cpu_state == "iowait":
			self.update_high_io_server_issue()

	def ping_sample_site(self):
		if not (site := self.get_down_site()):
			return None
		try:
			ret = requests.get(f"https://{site}/api/method/ping", timeout=10)
		except requests.RequestException as e:
			self.add_description(f"Error pinging sample site {site}: {e!s}")
			return None
		else:
			self.add_description(f"Ping response for sample site {site}: {ret.status_code} {ret.reason}")
			return ret.status_code

	def categorize_disk_full_issue(self):
		self.likely_cause = "Disk is full"
		self.add_corrective_suggestion("Add more storage")
		self.add_preventive_suggestion("Enable automatic addition of storage")

	def identify_problem(self):
		pong = self.ping_sample_site()
		if not self.resource and pong and pong == 500:
			db: DatabaseServer = frappe.get_doc("Database Server", self.database_server)
			if db.is_disk_full(MARIADB_DATA_MNT_POINT):
				self.resource_type = "Database Server"
				self.resource = self.database_server
				self.type = "Database Down"
				self.subtype = "Disk full"
				self.categorize_disk_full_issue()
				self.communication.send_disk_full_mail()
				return
			# TODO: Try more random shit if resource isn't identified
			# Eg: Check mysql up/ docker up/ container up
			# Ping site for error code to guess more accurately
			# 500 would mean mysql down or bug in app/config
			# 502 would mean server/bench down
			# 504 overloaded workers

		state, percent = self.get_cpu_state(self.resource)
		if state == "idle" or percent < 70:
			return

		if self.resource_type == "Database Server":
			self.categorize_db_cpu_issues(state)
		elif self.resource_type == "Server":
			self.categorize_server_cpu_issues(state)

		# TODO: categorize proxy issues #

	@property
	def other_resource(self):
		if self.resource_type == "Database Server":
			return str(self.server)
		if self.resource_type == "Server":
			return str(frappe.db.get_value("Server", self.resource, "database_server"))
		return None

	def add_node_exporter_screenshot(self, page: Page, instance: str | None):
		if not instance:
			return

		page.goto(
			f"https://{self.monitor_server.name}{self.monitor_server.node_exporter_dashboard_path}&refresh=5m&var-DS_PROMETHEUS=Prometheus&var-job=node&var-node={instance}&from=now-1h&to=now"
		)
		page.wait_for_load_state("networkidle")

		image = b64encode(page.screenshot()).decode("ascii")
		self.add_description(f'<img src="data:image/png;base64,{image}" alt="grafana-image">')

	@cached_property
	def monitor_server(self) -> MonitorServer:
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		if not (monitor_url := press_settings.monitor_server):
			frappe.throw("Monitor Server not set in Press Settings")
		return frappe.get_cached_doc("Monitor Server", monitor_url)

	def get_grafana_auth_header(self):
		username = str(self.monitor_server.grafana_username)
		password = str(self.monitor_server.get_password("grafana_password"))
		token = b64encode(f"{username}:{password}".encode()).decode("ascii")
		return f"Basic {token}"

	@filelock("grafana_screenshots")  # prevent 100 chromes from opening
	def take_grafana_screenshots(self):
		if not frappe.db.get_single_value("Incident Settings", "grafana_screenshots"):
			return
		with sync_playwright() as p:
			browser = p.chromium.launch(headless=True, channel="chromium")
			page = browser.new_page(locale="en-IN", timezone_id="Asia/Kolkata")
			page.set_extra_http_headers({"Authorization": self.get_grafana_auth_header()})

			self.add_node_exporter_screenshot(page, self.resource or self.server)
			self.add_node_exporter_screenshot(page, self.other_resource)

		self.save()

	@frappe.whitelist()
	def reboot_database_server(self):
		db_server_name = frappe.db.get_value("Server", self.server, "database_server")
		if not db_server_name:
			frappe.throw("No database server found for this server")
		db_server = DatabaseServer("Database Server", db_server_name)
		try:
			db_server.reboot_with_serial_console()
		except NotImplementedError:
			db_server.reboot()
		self.add_likely_cause("Rebooted database server.")
		self.save()

	@frappe.whitelist()
	def cancel_stuck_jobs(self):
		"""
		During db reboot/upgrade some jobs tend to get stuck. This is a hack to cancel those jobs
		"""
		stuck_jobs = frappe.get_all(
			"Agent Job",
			{
				"status": "Running",
				INCIDENT_SCOPE: self.incident_scope,
				"job_type": (
					"in",
					["Fetch Database Table Schema", "Backup Site", "Restore Site"],
				),  # to be safe
			},
			["name", "job_type"],
			limit=2,
		)  # only 2 workers
		for stuck_job in stuck_jobs:
			job = AgentJob("Agent Job", stuck_job.name)
			job.cancel_job()
			self.add_likely_cause(f"Cancelled stuck {stuck_job.job_type} job {stuck_job.name}")
		self.save()

	def add_likely_cause(self, cause: str):
		self.likely_cause = self.likely_cause + cause + "\n" if self.likely_cause else cause + "\n"

	@cached_property
	def down_bench(self):
		down_benches = self.monitor_server.get_benches_down_for_server(str(self.server))
		return down_benches[0] if down_benches else None

	@frappe.whitelist()
	def restart_down_benches(self):
		"""
		Restart all benches on the server that are down
		"""
		down_benches = self.monitor_server.get_benches_down_for_server(str(self.server))
		if not down_benches:
			frappe.throw("No down benches found for this server")
			return
		for bench_name in down_benches:
			bench: Bench = Bench("Bench", bench_name)
			bench.restart()
			self.add_likely_cause(f"Restarted bench {bench_name}")
		self.save()

	def call_on_call_engineers(self, run_in_background: bool = True):
		if run_in_background:
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"call_on_call_engineers",
				queue="long",
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
				queue="default",
				enqueue_after_commit=True,
				at_front=True,
				job_id=f"incident||{self.name}||call_customers",
				deduplicate=True,
				run_in_background=False,
			)
			return

		self.communication.call_customers(enqueue_in_background=False)

	def add_acknowledgment_update(
		self,
		human: IncidentSettingsUser | IncidentSettingsSelfHostedUser,
		call_status: str | None = None,
		acknowledged=False,
	):
		"""
		Adds a new update to the Incident Document
		"""
		if acknowledged:
			update_note = f"Acknowledged by {human.user}"
			# Set acknowledged user and status
			self.status = "Acknowledged"
			self.acknowledged_by = human.user
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

	@property
	def incident_scope(self):
		return getattr(self, INCIDENT_SCOPE)

	@property
	def total_instances(self) -> int:
		return frappe.db.count(
			"Site",
			{"status": "Active", INCIDENT_SCOPE: self.incident_scope},
		)

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
		else:
			if not last_resolved.is_enough_firing:
				self.create_log_for_server(is_resolved=True)
				self.resolve()

	def resolve(self):
		if self.status == "Validating":
			self.status = "Auto-Resolved"
		else:
			self.status = "Resolved"
		self.save()

	def create_log_for_server(self, is_resolved: bool = False):
		"""We will create a incident log on the server activity for confirmed incidents and their resolution"""
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

	@property
	def waited_enough_for_investigator_reactions(self) -> bool:
		"""Check if the investigator has taken any action"""
		investigator: IncidentInvestigator = frappe.get_doc("Incident Investigator", {"incident": self.name})
		if investigator.status != "Completed":
			return False

		# Investigation is completed and actions are taken wait before calling
		if (
			investigator.status == "Completed"
			and investigator.action_steps
			and (
				investigator.modified
				> frappe.utils.now_datetime()
				- timedelta(seconds=cint(self.settings.wait_time_post_investigator_actions))
			)
		):
			return False

		return True

	@property
	def time_to_call_for_help(self) -> bool:
		return self.status == "Confirmed" and frappe.utils.now_datetime() - self.creation > timedelta(
			seconds=self.settings.confirmation_threshold_seconds + self.settings.call_threshold_seconds
		)

	@property
	def time_to_call_for_help_again(self) -> bool:
		return self.status == "Acknowledged" and frappe.utils.now_datetime() - self.modified > timedelta(
			seconds=self.settings.call_repeat_interval_seconds
		)

	@cached_property
	def sites_down(self) -> list[str]:
		return self.monitor_server.get_sites_down_for_server(str(self.server))

	@frappe.whitelist()
	def get_down_site(self):
		return self.sites_down[0] if self.sites_down else None


def validate_incidents():
	settings: IncidentSettings = frappe.get_cached_doc("Incident Settings")
	validating_incidents = frappe.get_all(
		"Incident",
		filters={
			"status": "Validating",
		},
		fields=["name", "creation"],
	)
	for incident_dict in validating_incidents:
		if frappe.utils.now_datetime() - incident_dict.creation > timedelta(
			seconds=settings.confirmation_threshold_seconds
		):
			incident = Incident("Incident", incident_dict.name)
			incident.confirm()


def resolve_incidents():
	ongoing_incidents = frappe.get_all(
		"Incident",
		filters={
			"status": ("in", ["Validating", "Confirmed", "Acknowledged"]),
		},
		pluck="name",
	)
	for incident_name in ongoing_incidents:
		incident = Incident("Incident", incident_name)
		incident.check_resolved()
		if (
			incident.time_to_call_for_help or incident.time_to_call_for_help_again
		) and incident.waited_enough_for_investigator_reactions:
			incident.create_log_for_server()
			incident.call_on_call_engineers()


def notify_ignored_servers():
	servers = frappe.qb.DocType("Server")
	if not (
		ignored_servers := frappe.qb.from_(servers)
		.select(servers.name, servers.ignore_incidents_till)
		.where(servers.status == "Active")
		.where(servers.ignore_incidents_till.isnotnull())
		.where(servers.ignore_incidents_till >= frappe.utils.now_datetime())
		.run(as_dict=True)
	):
		return

	message = "The following servers are being ignored for incidents:\n\n"
	for server in ignored_servers:
		message += f"{server.name} till {frappe.utils.pretty_date(server.ignore_incidents_till)}\n"
	message += "\n@adityahase @balamurali27 @saurabh6790\n"
	TelegramMessage.enqueue(message)


def on_doctype_update():
	frappe.db.add_index("Incident", ["alert", "server", "status"])
