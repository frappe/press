# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from datetime import timedelta
import frappe
from frappe.utils.background_jobs import enqueue_doc
from frappe.utils import cint
from frappe.website.website_generator import WebsiteGenerator
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed
from tenacity.retry import retry_if_not_result

from press.utils import log_error

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from press.press.doctype.incident_settings_user.incident_settings_user import (
		IncidentSettingsUser,
	)
	from press.press.doctype.incident_settings_self_hosted_user.incident_settings_self_hosted_user import (
		IncidentSettingsSelfHostedUser,
	)
	from press.press.doctype.press_settings.press_settings import PressSettings

INCIDENT_ALERT = "Sites Down"  # TODO: make it a field or child table somewhere #
INCIDENT_SCOPE = "server"  # can be bench, cluster, server, etc. Not site, minor code changes required for that

DAY_HOURS = range(9, 18)
CONFIRMATION_THRESHOLD_SECONDS_DAY = (
	5 * 60
)  # 5 minutes;time after which humans are called
CONFIRMATION_THRESHOLD_SECONDS_NIGHT = (
	10 * 60  # 10 minutes; time after which humans are called
)
CALL_THRESHOLD_SECONDS_DAY = 0  # 0 minutes;time after which humans are called
CALL_THRESHOLD_SECONDS_NIGHT = (
	15 * 60  # 15 minutes; time after confirmation after which humans are called
)
CALL_REPEAT_INTERVAL_DAY = 15 * 60
CALL_REPEAT_INTERVAL_NIGHT = 20 * 60
PAST_ALERT_COVER_MINUTES = (
	15  # to cover alerts that fired before/triggered the incident
)


class Incident(WebsiteGenerator):
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
		bench: DF.Link | None
		cluster: DF.Link | None
		description: DF.TextEditor | None
		phone_call: DF.Check
		resolved_by: DF.Link | None
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
		type: DF.Literal["Site Down", "Bench Down", "Server Down"]
		updates: DF.Table[IncidentUpdates]
	# end: auto-generated types

	def validate(self):
		if not hasattr(self, "phone_call") and self.global_phone_call_enabled:
			self.phone_call = True

	@property
	def global_phone_call_enabled(self) -> bool:
		return bool(frappe.get_cached_value("Incident Settings", None, "phone_call_alerts"))

	@property
	def global_email_alerts_enabled(self) -> bool:
		return bool(frappe.get_cached_value("Incident Settings", None, "email_alerts"))

	def after_insert(self):
		self.send_sms_via_twilio()
		self.send_email_notification()

	def on_update(self):
		if self.has_value_changed("status"):
			self.send_email_notification()

	@frappe.whitelist()
	def ignore_for_server(self):
		"""
		Ignore incidents on server (Don't call)
		"""
		frappe.db.set_value("Server", self.server, "ignore_incidents", 1)

	def call_humans(self):
		enqueue_doc(
			self.doctype,
			self.name,
			"_call_humans",
			queue="long",
			enqueue_after_commit=True,
			at_front=True,
		)

	def get_humans(
		self,
	) -> list["IncidentSettingsUser"] | list["IncidentSettingsSelfHostedUser"]:
		"""
		Returns a list of users who are in the incident team
		"""
		incident_settings = frappe.get_cached_doc("Incident Settings")
		if frappe.db.exists(
			"Self Hosted Server", {"server": self.server}
		) or frappe.db.get_value("Server", self.server, "is_self_hosted"):
			users = incident_settings.self_hosted_users
		users = incident_settings.users
		ret = users
		if self.status == "Acknowledged":  # repeat the acknowledged user to be the first
			for user in users:
				if user.user == self.acknowledged_by:
					ret.remove(user)
					ret.insert(0, user)
		return ret

	@property
	def twilio_phone_number(self):
		press_settings = frappe.get_cached_doc("Press Settings")
		return press_settings.twilio_phone_number

	@property
	def twilio_client(self):
		press_settings: "PressSettings" = frappe.get_cached_doc("Press Settings")
		try:
			return press_settings.twilio_client
		except Exception:
			log_error("Twilio Client not configured in Press Settings")
			frappe.db.commit()
			raise

	@retry(
		retry=retry_if_not_result(
			lambda result: result
			in ["canceled", "completed", "failed", "busy", "no-answer", "in-progress"]
		),
		wait=wait_fixed(1),
		stop=stop_after_attempt(30),
	)
	def wait_for_pickup(self, call):
		return call.fetch().status  # will eventually be no-answer

	def _call_humans(self):
		if not self.phone_call or not self.global_phone_call_enabled:
			return
		if frappe.db.get_value("Server", self.server, "ignore_incidents"):
			return
		for human in self.get_humans():
			call = self.twilio_client.calls.create(
				url="http://demo.twilio.com/docs/voice.xml",
				to=human.phone,
				from_=self.twilio_phone_number,
			)
			acknowledged = False
			status = call.status
			try:
				status = self.wait_for_pickup(call)
			except RetryError:
				status = "timeout"  # not twilio's status; mostly translates to no-answer
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
		title = frappe.db.get_value("Server", self.server, "title")
		name = title.removesuffix(" - Application") or self.server
		return f"Incident on {name} - {self.alert}"

	def get_email_message(self):
		acknowledged_by = "An engineer"
		if self.acknowledged_by:
			acknowledged_by = frappe.db.get_value("User", self.acknowledged_by, "first_name")
		message = {
			"Validating": "We are noticing some issues with sites on your server. We are giving it a few minutes to confirm before escalating this incident to our engineers.",
			"Auto-Resolved": "Your sites are now up! This incident has been auto-resolved. We will keep monitoring your sites for any further issues.",
			"Confirmed": "We are still noticing issues with your sites. We are escalating this incident to our engineers.",
			"Acknowledged": f"{acknowledged_by} from our team has acknowledged the incident and is actively investigating. Please allow them some time to diagnose and address the issue.",
			"Resolved": f"Your sites are now up! {acknowledged_by} has resolved this incident. We will keep monitoring your sites for any further issues",
		}[self.status]

		return message

	def add_acknowledgment_update(
		self, human: "IncidentSettingsUser", call_status: str = None, acknowledged=False
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
		return (
			self.status == "Confirmed"
			and frappe.utils.now_datetime() - self.creation
			> timedelta(
				seconds=get_confirmation_threshold_duration() + get_call_threshold_duration()
			)
		)

	@property
	def time_to_call_for_help_again(self) -> bool:
		return (
			self.status == "Acknowledged"
			and frappe.utils.now_datetime() - self.modified
			> timedelta(seconds=get_call_repeat_interval())
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
			incident: Incident = frappe.get_doc("Incident", incident_dict.name)
			incident.status = "Confirmed"
			incident.save()


def resolve_incidents():
	ongoing_incidents = frappe.get_all(
		"Incident",
		filters={
			"status": ("in", ["Validating", "Confirmed", "Acknowledged"]),
		},
		pluck="name",
	)
	for incident_name in ongoing_incidents:
		incident: Incident = frappe.get_doc("Incident", incident_name)
		incident.check_resolved()
		if incident.time_to_call_for_help or incident.time_to_call_for_help_again:
			incident.call_humans()


def on_doctype_update():
	frappe.db.add_index("Incident", ["server", "status"])
