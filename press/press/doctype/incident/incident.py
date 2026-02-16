# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import urllib.parse
from base64 import b64encode
from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
import requests
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
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.bench.bench import Bench
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.database_server.database_server import DatabaseServer
from press.press.doctype.server.server import MARIADB_DATA_MNT_POINT
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.utils import log_error

if TYPE_CHECKING:
	from frappe.types import DF
	from twilio.rest.api.v2010.account.call import CallInstance

	from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import AlertmanagerWebhookLog
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

MIN_FIRING_INSTANCES = 15  # minimum instances that should have fired for an incident to be valid
MIN_FIRING_INSTANCES_FRACTION = (
	0.4  # 40%; minimum percentage of instances that should have fired for an incident to be valid
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
		called_customer: DF.Check
		cluster: DF.Link | None
		corrective_suggestions: DF.Table[IncidentSuggestion]
		description: DF.TextEditor | None
		investigation: DF.Link | None
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
		"""
		Start investigating the incident since we have already waited 5m before creating it
		send sms and email notifications
		"""
		try:
			incident_investigator = frappe.get_doc(
				{"doctype": "Incident Investigator", "incident": self.name, "server": self.server}
			)
			incident_investigator.insert(ignore_permissions=True)
			self.investigation = incident_investigator.name
			self.save()
		except frappe.ValidationError:
			# Investigator in cool off period
			pass
		self.send_sms_via_twilio()
		self.send_email_notification()
		self.identify_affected_resource()

	def on_update(self):
		if self.has_value_changed("status"):
			self.send_email_notification()
			if self.status == "Confirmed" and not self.called_customer:
				self.call_customers()

	def vcpu(self, server_type, server_name):
		vm_name = str(frappe.db.get_value(server_type, server_name, "virtual_machine"))
		return int(
			frappe.db.get_value("Virtual Machine", vm_name, "vcpu") or 16  # type: ignore
		)  # 16 as DO and Scaleway servers have high CPU; Add a CPU field everywhere later

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
		if load > 3 * self.vcpu(resource_type, resource):
			return resource_type, resource
		return False, False

	def get_sites_down_list(self):
		return "\n".join(self.sites_down)

	def identify_affected_resource(self):
		"""
		Identify the affected resource and set the resource field
		"""
		self.add_description(f"{len(self.sites_down)} / {self.total_instances} sites down:")
		self.add_description(self.get_sites_down_list())

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
		timespan = get_confirmation_threshold_duration()
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

	def categorize_db_cpu_issues(self, cpu_state):
		self.type = "Database Down"
		if cpu_state == "user":
			self.update_user_db_issue()
		elif cpu_state == "iowait":
			self.update_high_io_db_issue()

	def update_user_server_issue(self):
		pass

	def update_high_io_server_issue(self):
		pass

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
				self.send_disk_full_mail()
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
		incident_settings: IncidentSettings = frappe.get_cached_doc("Incident Settings")  # type: ignore
		users = incident_settings.users
		if frappe.db.exists("Self Hosted Server", {"server": self.server}) or frappe.db.get_value(
			"Server", self.server, "is_self_hosted"
		):
			users = incident_settings.self_hosted_users
		ret: DF.Table = users
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
			if not frappe.flags.in_test:
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
		TelegramMessage.enqueue(
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
			ignore_till := frappe.db.get_value("Server", self.server, "ignore_incidents_till")
		) and ignore_till > frappe.utils.now_datetime():
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
		if (
			ignore_since := frappe.db.get_value("Server", self.server, "ignore_incidents_till")
		) and ignore_since < frappe.utils.now_datetime():
			return
		domain = frappe.db.get_value("Press Settings", None, "domain")
		incident_link = f"https://{domain}{self.get_url()}"
		message = f"Incident on server: {self.server}\n\nURL: {incident_link}\n\nID: {self.name}"
		for human in self.get_humans():
			self.twilio_client.messages.create(to=human.phone, from_=self.twilio_phone_number, body=message)
		self.reload()  # In case the phone call status is modified by the investigator before the sms is sent
		self.sms_sent = 1
		self.save()

	def send_disk_full_mail(self):
		title = str(frappe.db.get_value("Server", self.server, "title"))
		if self.resource_type:
			title = str(frappe.db.get_value(self.resource_type, self.resource, "title"))
		subject = f"Disk Full Incident on {title}"
		message = f"""
		<p>Dear User,</p>
		<p>You are receiving this mail as the storage has been filled up on your server: <strong>{self.resource}</strong> and you have <a href="https://docs.frappe.io/cloud/storage-addons#steps-to-disable-auto-increase-storage">automatic addition</a> of storage disabled.</p>
		<p>Please enable automatic addition of storage or <a href="https://docs.frappe.io/cloud/storage-addons#steps-to-add-storage-manually">add more storage manually</a> to resolve the issue.</p>
		<p>Best regards,<br/>Frappe Cloud Team</p>
		"""
		self.send_mail(subject, message)

	def send_mail(self, subject: str, message: str):
		try:
			frappe.sendmail(
				recipients=get_communication_info("Email", "Server Activity", "Server", self.server),
				subject=subject,
				reference_doctype=self.doctype,
				reference_name=self.name,
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

	def send_email_notification(self):
		if not self.global_email_alerts_enabled:
			return

		if self.status == "Investigating":
			return

		# Notifications are only meaningful for incidents that are linked to a server and a team
		team = frappe.db.get_value("Server", self.server, "team")
		if (not self.server) or (not team):
			return
		subject = self.get_email_subject()
		message = self.get_email_message()
		self.send_mail(subject, message)

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
			"Auto-Resolved": "Your sites are now up! This incident has resolved on its own. We will keep monitoring your sites for any further issues.",
			"Confirmed": "We are still noticing issues with your sites. We are escalating this incident to our engineers.",
			"Acknowledged": f"{acknowledged_by} from our team has acknowledged the incident and is actively investigating. Please allow them some time to diagnose and address the issue.",
			"Resolved": f"Your sites are now up! {acknowledged_by} has resolved this incident. We will keep monitoring your sites for any further issues",
		}[self.status]

	def call_customers(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_call_customers",
			queue="default",
			enqueue_after_commit=True,
			at_front=True,
			job_id=f"incident||call_customers||{self.name}",
			deduplicate=True,
		)

	def _call_customers(self):
		if not self.phone_call:
			return

		phone_nos = get_communication_info("Phone Call", "Incident", "Server", self.server)
		if not phone_nos:
			return

		for phone_no in phone_nos:
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"_call_customer",
				queue="default",
				timeout=1800,
				enqueue_after_commit=True,
				phone_no=phone_no,
			)

		self.add_comment("Comment", f"Called customers at {', '.join(phone_nos)}")

		self.called_customer = 1
		self.save()

	def _call_customer(self, phone_no: str):
		twilio_client = self.twilio_client
		if not twilio_client:
			return
		from_phone = self.twilio_phone_number
		server_title = frappe.db.get_value("Server", self.server, "title") or self.server
		if not from_phone or not server_title:
			return

		server_title_encoded = urllib.parse.quote(server_title)

		press_public_base_url = frappe.utils.get_url()
		twilio_client.calls.create(
			url=f"{press_public_base_url}/api/method/press.api.message.confirmed_incident?server_title={server_title_encoded}",
			to=phone_no,
			from_=from_phone,
		)

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
				"update_time": frappe.utils.now(),
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
	def time_to_call_for_help(self) -> bool:
		return self.status == "Confirmed" and frappe.utils.now_datetime() - self.creation > timedelta(
			seconds=get_confirmation_threshold_duration() + get_call_threshold_duration()
		)

	@property
	def time_to_call_for_help_again(self) -> bool:
		return self.status == "Acknowledged" and frappe.utils.now_datetime() - self.modified > timedelta(
			seconds=get_call_repeat_interval()
		)

	@cached_property
	def sites_down(self) -> list[str]:
		return self.monitor_server.get_sites_down_for_server(str(self.server))

	@frappe.whitelist()
	def get_down_site(self):
		return self.sites_down[0] if self.sites_down else None


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
			incident.create_log_for_server()
			incident.call_humans()


def notify_ignored_servers():
	servers = frappe.qb.DocType("Server")
	if not (
		ignored_servers := frappe.qb.from_(servers)
		.select(servers.name, servers.ignore_incidents_till)
		.where(servers.status == "Active")
		.where(servers.ignore_incidents_till.isnotnull())
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
