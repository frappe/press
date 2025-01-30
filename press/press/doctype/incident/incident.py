# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from base64 import b64encode
from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
from frappe.types.DF import Phone
from frappe.utils import cint
from frappe.utils.background_jobs import enqueue_doc
from frappe.utils.synchronization import filelock
from frappe.website.website_generator import WebsiteGenerator
from playwright.sync_api import Page, sync_playwright
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed
from tenacity.retry import retry_if_not_result
from twilio.base.exceptions import TwilioRestException

from press.api.server import prometheus_query
from press.telegram_utils import Telegram
from press.utils import log_error

if TYPE_CHECKING:
	from twilio.rest.api.v2010.account.call import CallInstance

	from press.press.doctype.incident_settings.incident_settings import IncidentSettings
	from press.press.doctype.incident_settings_self_hosted_user.incident_settings_self_hosted_user import (
		IncidentSettingsSelfHostedUser,
	)
	from press.press.doctype.incident_settings_user.incident_settings_user import (
		IncidentSettingsUser,
	)
	from press.press.doctype.monitor_server.monitor_server import MonitorServer
	from press.press.doctype.press_settings.press_settings import PressSettings

INCIDENT_ALERT = "Sites Down"  # TODO: make it a field or child table somewhere #
INCIDENT_SCOPE = (
	"server"  # can be bench, cluster, server, etc. Not site, minor code changes required for that
)

DAY_HOURS = range(9, 18)
CONFIRMATION_THRESHOLD_SECONDS_DAY = 5 * 60  # 5 minutes;time after which humans are called
CONFIRMATION_THRESHOLD_SECONDS_NIGHT = (
	10 * 60  # 10 minutes; time after which humans are called
)
CALL_THRESHOLD_SECONDS_DAY = 0  # 0 minutes;time after which humans are called
CALL_THRESHOLD_SECONDS_NIGHT = (
	15 * 60  # 15 minutes; time after confirmation after which humans are called
)
CALL_REPEAT_INTERVAL_DAY = 15 * 60
CALL_REPEAT_INTERVAL_NIGHT = 20 * 60
PAST_ALERT_COVER_MINUTES = 15  # to cover alerts that fired before/triggered the incident


class Incident(WebsiteGenerator):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.incident_alerts.incident_alerts import IncidentAlerts
		from press.press.doctype.incident_suggestion.incident_suggestion import IncidentSuggestion
		from press.press.doctype.incident_updates.incident_updates import IncidentUpdates

		acknowledged_by: DF.Link | None
		alert: DF.Link | None
		alerts: DF.Table[IncidentAlerts]
		cluster: DF.Link | None
		description: DF.TextEditor | None
		likely_cause: DF.Text | None
		phone_call: DF.Check
		preventive_suggestions: DF.Table[IncidentSuggestion]
		resolved_by: DF.Link | None
		resource: DF.DynamicLink | None
		resource_type: DF.Link | None
		route: DF.Data | None
		server: DF.Link | None
		show_in_website: DF.Check
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
		subject: DF.Data | None
		subtype: DF.Literal["High CPU: user", "High CPU: iowait", "Disk full"]
		suggestions: DF.Table[IncidentSuggestion]
		type: DF.Literal["Database Down", "Server Down", "Proxy Down"]
		updates: DF.Table[IncidentUpdates]
	# end: auto-generated types

	def validate(self):
		if not hasattr(self, "phone_call") and self.global_phone_call_enabled:
			self.phone_call = True

	@property
	def global_phone_call_enabled(self) -> bool:
		return bool(frappe.db.get_single_value("Incident Settings", "phone_call_alerts", cache=True))

	@property
	def global_email_alerts_enabled(self) -> bool:
		return bool(frappe.db.get_single_value("Incident Settings", "email_alerts", cache=True))

	def after_insert(self):
		self.send_sms_via_twilio()
		self.send_email_notification()

	def on_update(self):
		if self.has_value_changed("status"):
			self.send_email_notification()

	def vcpu(self, server_type, server_name):
		vm_name = frappe.db.get_value(server_type, server_name, "virtual_machine")
		return int(
			frappe.db.get_value("Virtual Machine", vm_name, "vcpu") or 16
		)  # 16 as DO and scaleway servers have high CPU; Add a CPU field everywhere later

	@cached_property
	def database_server(self):
		return str(frappe.db.get_value("Server", self.server, "database_server"))

	@cached_property
	def proxy_server(self):
		return str(frappe.db.get_value("Server", self.server, "proxy_server"))

	def get_load(self, name) -> float:
		timespan = get_confirmation_threshold_duration()
		load = prometheus_query(
			f"""avg_over_time(node_load5{{instance="{name}", job="node"}}[{timespan}s])""",
			lambda x: x,
			"Asia/Kolkata",
			timespan,
			timespan + 1,
		)["datasets"]
		if load == []:
			ret = -1  # no response
		else:
			ret = load[0]["values"][-1]
		self.add_description(f"{name} load avg(5m): {ret if ret != -1 else 'No data'}")
		return ret

	def check_high_load(self, resource_type: str, resource: str):
		load = self.get_load(resource)
		if load < 0:  # no response, likely down
			return resource_type, resource
		if load > 3 * self.vcpu(resource_type, resource):
			return resource_type, resource
		return False, False

	def identify_affected_resource(self):
		"""
		Identify the affected resource and set the resource field
		"""

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
		self.save()

	def get_cpu_state(self, resource: str):
		timespan = get_confirmation_threshold_duration()
		cpu_info = prometheus_query(
			f"""avg by (mode)(rate(node_cpu_seconds_total{{instance="{resource}", job="node"}}[{timespan}s])) * 100""",
			lambda x: x["mode"],
			"Asia/Kolkata",
			timespan,
			timespan + 1,
		)["datasets"]
		mode_cpus = {x["name"]: x["values"][-1] for x in cpu_info} or {
			"user": -1,
			"idle": -1,
			"softirq": -1,
			"iowait": -1,
		}  # no info;
		max_mode = max(mode_cpus, key=mode_cpus.get)
		max_cpu = mode_cpus[max_mode]
		self.add_description(f"CPU Usage: {max_mode} {max_cpu if max_cpu > 0 else 'No data'}")
		return max_mode, mode_cpus[max_mode]

	def add_description(self, description):
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

	def update_user_db_issue(self):
		self.subtype = "High CPU: user"
		self.likely_causes = "Likely slow queries or many queries."
		self.add_corrective_suggestion("Kill long running queries")
		self.add_preventive_suggestion("Contact user to reduce queries")

	def update_high_io_db_issue(self):
		self.subtype = "High CPU: iowait"
		self.likely_causes = "Not enough memory"
		self.add_corrective_suggestion("Reboot Server")
		self.add_preventive_suggestion("Upgrade database server for more memory")

	def categorize_db_issues(self, cpu_state):
		self.type = "Database Down"
		if cpu_state == "user":
			self.update_user_db_issue()
		elif cpu_state == "iowait":
			self.update_high_io_db_issue()

	def update_user_server_issue(self):
		pass

	def update_high_io_server_issue(self):
		pass

	def categorize_server_issues(self, cpu_state):
		self.type = "Server Down"
		if cpu_state == "user":
			self.update_user_server_issue()
		elif cpu_state == "iowait":
			self.update_high_io_server_issue()

	def identify_problem(self):
		if not self.resource:
			return
			# TODO: Try random shit if resource isn't identified
			# Eg: Check mysql up/ docker up/ container up
			# Ping site for error code to guess more accurately
			# 500 would mean mysql down or bug in app/config
			# 502 would mean server/bench down
			# 504 overloaded workers

		state, percent = self.get_cpu_state(self.resource)
		if state == "idle" or percent < 70:
			return

		if self.resource_type == "Database Server":
			self.categorize_db_issues(state)
		elif self.resource_type == "Server":
			self.categorize_server_issues(state)

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
			page = browser.new_page()
			page.set_extra_http_headers({"Authorization": self.get_grafana_auth_header()})

			self.add_node_exporter_screenshot(page, self.resource or self.server)
			self.add_node_exporter_screenshot(page, self.other_resource)

		self.save()

	@frappe.whitelist()
	def ignore_for_server(self):
		"""
		Ignore incidents on server (Don't call)
		"""
		frappe.db.set_value("Server", self.server, "ignore_incidents_since", frappe.utils.now_datetime())

	def call_humans(self):
		enqueue_doc(
			self.doctype,
			self.name,
			"_call_humans",
			queue="default",
			timeout=1800,
			enqueue_after_commit=True,
			at_front=True,
			job_id=f"call_humans:{self.name}",
			deduplicate=True,
		)

	def get_humans(
		self,
	):
		"""
		Returns a list of users who are in the incident team
		"""
		incident_settings: IncidentSettings = frappe.get_cached_doc("Incident Settings")
		users = incident_settings.users
		if frappe.db.exists("Self Hosted Server", {"server": self.server}) or frappe.db.get_value(
			"Server", self.server, "is_self_hosted"
		):
			users = incident_settings.self_hosted_users
		ret: list[IncidentSettingsUser | IncidentSettingsSelfHostedUser] = users
		if self.status == "Acknowledged":  # repeat the acknowledged user to be the first
			for user in users:
				if user.user == self.acknowledged_by:
					ret.remove(user)
					ret.insert(0, user)
		return ret

	@property
	def twilio_phone_number(self):
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		return Phone(press_settings.twilio_phone_number)

	@property
	def twilio_client(self):
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		try:
			return press_settings.twilio_client
		except Exception:
			log_error("Twilio Client not configured in Press Settings")
			frappe.db.commit()
			raise

	@retry(
		retry=retry_if_not_result(
			lambda result: result in ["canceled", "completed", "failed", "busy", "no-answer", "in-progress"]
		),
		wait=wait_fixed(1),
		stop=stop_after_attempt(30),
	)
	def wait_for_pickup(self, call: CallInstance):
		return call.fetch().status  # will eventually be no-answer

	def notify_unable_to_reach_twilio(self):
		telegram = Telegram()
		telegram.send(
			f"""Unable to reach Twilio for Incident in {self.server}

Likely due to insufficient balance or incorrect credentials""",
			reraise=True,
		)

	def call_human(self, human: IncidentSettingsUser | IncidentSettingsSelfHostedUser):
		try:
			return self.twilio_client.calls.create(
				url="http://demo.twilio.com/docs/voice.xml",
				to=human.phone,
				from_=self.twilio_phone_number,
			)
		except TwilioRestException:
			self.notify_unable_to_reach_twilio()
			raise

	def _call_humans(self):
		if not self.phone_call or not self.global_phone_call_enabled:
			return
		if (
			ignore_since := frappe.db.get_value("Server", self.server, "ignore_incidents_since")
		) and ignore_since < frappe.utils.now_datetime():
			return
		for human in self.get_humans():
			if not (call := self.call_human(human)):
				return  # can't twilio
			acknowledged = False
			status = str(call.status)
			try:
				status = str(self.wait_for_pickup(call))
			except RetryError:
				status = "timeout"  # not Twilio's status; mostly translates to no-answer
			else:
				if status in ["in-progress", "completed"]:  # call was picked up
					acknowledged = True
					self.status = "Acknowledged"
					self.acknowledged_by = human.user
					break
			finally:
				self.add_acknowledgment_update(human, acknowledged=acknowledged, call_status=status)

	def send_sms_via_twilio(self):
		"""
		Sends an SMS to the members in the Incident team
		Uses Twilio for sending the SMS.
		Fetches all the Numbers and makes it a generator object for memory efficiency and
		Runs them through a loop since Twilio Requires a single API call for
		Sending one SMS to one number
		Ref: https://support.twilio.com/hc/en-us/articles/223181548-Can-I-set-up-one-API-call-to-send-messages-to-a-list-of-people-
		"""
		domain = frappe.db.get_value("Press Settings", None, "domain")
		incident_link = f"{domain}{self.get_url()}"

		message_body = f"""New Incident {self.name} Reported

Hosted on: {self.server}

Incident URL: {incident_link}"""
		for human in self.get_humans():
			self.twilio_client.messages.create(
				to=human.phone, from_=self.twilio_phone_number, body=message_body
			)
		self.sms_sent = 1
		self.save()

	def send_email_notification(self):
		if not self.global_email_alerts_enabled:
			return

		if self.status == "Investigating":
			return

		# Notifications are only meaningful for incidents that are linked to a server and a team
		team = frappe.db.get_value("Server", self.server, "team")
		if (not self.server) or (not team):
			return
		try:
			subject = self.get_email_subject()
			message = self.get_email_message()
			frappe.sendmail(
				recipients=[frappe.db.get_value("Team", team, "notify_email")],
				subject=subject,
				template="incident",
				args={
					"message": message,
					"link": f"dashboard/servers/{self.server}/analytics/",
				},
				now=True,
			)
		except Exception:
			# Swallow the exception to avoid breaking the Incident creation
			log_error("Incident Notification Email Failed")

	def get_email_subject(self):
		title = str(frappe.db.get_value("Server", self.server, "title"))
		name = title.removesuffix(" - Application") or self.server
		return f"Incident on {name} - {self.alert}"

	def get_email_message(self):
		acknowledged_by = "An engineer"
		if self.acknowledged_by:
			acknowledged_by = frappe.db.get_value("User", self.acknowledged_by, "first_name")
		return {
			"Validating": "We are noticing some issues with sites on your server. We are giving it a few minutes to confirm before escalating this incident to our engineers.",
			"Auto-Resolved": "Your sites are now up! This incident has been auto-resolved. We will keep monitoring your sites for any further issues.",
			"Confirmed": "We are still noticing issues with your sites. We are escalating this incident to our engineers.",
			"Acknowledged": f"{acknowledged_by} from our team has acknowledged the incident and is actively investigating. Please allow them some time to diagnose and address the issue.",
			"Resolved": f"Your sites are now up! {acknowledged_by} has resolved this incident. We will keep monitoring your sites for any further issues",
		}[self.status]

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
		else:
			update_note = f"Acknowledgement failed for {human.user}"
		if call_status:
			update_note += f" with call status {call_status}"
		self.append(
			"updates",
			{
				"update_note": update_note,
				"update_time": frappe.utils.frappe.utils.now(),
			},
		)
		self.save()

	def set_acknowledgement(self, acknowledged_by):
		"""
		Sets the Incident status to Acknowledged
		"""
		self.status = "Acknowledged"
		self.acknowledged_by = acknowledged_by
		self.save()

	@property
	def incident_scope(self):
		return getattr(self, INCIDENT_SCOPE)

	def get_last_alert_status_for_each_group(self):
		return frappe.db.sql_list(
			f"""
select
	last_alert_per_group.status
from
	(
		select
			name,
			status,
			group_key,
			modified,
			ROW_NUMBER() OVER (
				PARTITION BY
					`group_key`
				ORDER BY
					`modified` DESC
			) AS rank
		from
			`tabAlertmanager Webhook Log`
		where
			modified >= "{self.creation - timedelta(minutes=PAST_ALERT_COVER_MINUTES)}"
			and group_key like "%%{self.incident_scope}%%"
	) last_alert_per_group
where
	last_alert_per_group.rank = 1
			"""
		)  # status of the sites down in each bench

	def check_resolved(self):
		if "Firing" in self.get_last_alert_status_for_each_group():
			# all should be "resolved" for auto-resolve
			return
		if self.status == "Validating":
			self.status = "Auto-Resolved"
		else:
			self.status = "Resolved"
		self.save()

	@property
	def time_to_call_for_help(self) -> bool:
		return self.status == "Confirmed" and frappe.utils.now_datetime() - self.creation > timedelta(
			seconds=get_confirmation_threshold_duration() + get_call_threshold_duration()
		)

	@property
	def time_to_call_for_help_again(self) -> bool:
		return self.status == "Acknowledged" and frappe.utils.now_datetime() - self.modified > timedelta(
			seconds=get_call_repeat_interval()
		)


def get_confirmation_threshold_duration():
	if frappe.utils.now_datetime().hour in DAY_HOURS:
		return (
			cint(frappe.db.get_value("Incident Settings", None, "confirmation_threshold_day"))
			or CONFIRMATION_THRESHOLD_SECONDS_DAY
		)
	return (
		cint(frappe.db.get_value("Incident Settings", None, "confirmation_threshold_night"))
		or CONFIRMATION_THRESHOLD_SECONDS_NIGHT
	)


def get_call_threshold_duration():
	if frappe.utils.now_datetime().hour in DAY_HOURS:
		return (
			cint(frappe.db.get_value("Incident Settings", None, "call_threshold_day"))
			or CALL_THRESHOLD_SECONDS_DAY
		)
	return (
		cint(frappe.db.get_value("Incident Settings", None, "call_threshold_night"))
		or CALL_THRESHOLD_SECONDS_NIGHT
	)


def get_call_repeat_interval():
	if frappe.utils.now_datetime().hour in DAY_HOURS:
		return (
			cint(frappe.db.get_value("Incident Settings", None, "call_repeat_interval_day"))
			or CALL_REPEAT_INTERVAL_DAY
		)
	return (
		cint(frappe.db.get_value("Incident Settings", None, "call_repeat_interval_night"))
		or CALL_REPEAT_INTERVAL_NIGHT
	)


def validate_incidents():
	validating_incidents = frappe.get_all(
		"Incident",
		filters={
			"status": "Validating",
		},
		fields=["name", "creation"],
	)
	for incident_dict in validating_incidents:
		if frappe.utils.now_datetime() - incident_dict.creation > timedelta(
			seconds=get_confirmation_threshold_duration()
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
		if incident.time_to_call_for_help or incident.time_to_call_for_help_again:
			incident.call_humans()


def notify_ignored_servers():
	servers = frappe.qb.DocType("Server")
	if not (
		ignored_servers := frappe.qb.from_(servers)
		.select(servers.name, servers.ignore_incidents_since)
		.where(servers.status == "Active")
		.where(servers.ignore_incidents_since.isnotnull())
		.run(as_dict=True)
	):
		return

	message = "The following servers are being ignored for incidents:\n\n"
	for server in ignored_servers:
		message += f"{server.name} since {frappe.utils.pretty_date(server.ignore_incidents_since)}\n"
	message += "\n@adityahase @balamurali27 @saurabh6790\n"
	telegram = Telegram()
	telegram.send(message)


def on_doctype_update():
	frappe.db.add_index("Incident", ["alert", "server", "status"])
