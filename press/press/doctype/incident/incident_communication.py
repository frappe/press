from __future__ import annotations

import urllib.parse
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
from frappe.types.DF import Phone
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed
from tenacity.retry import retry_if_not_result
from twilio.base.exceptions import TwilioRestException

from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.telegram_message.telegram_message import TelegramMessage

if TYPE_CHECKING:
	from twilio.rest.api.v2010.account.call import CallInstance

	from press.press.doctype.incident.incident import Incident
	from press.press.doctype.incident_settings_self_hosted_user.incident_settings_self_hosted_user import (
		IncidentSettingsSelfHostedUser,
	)
	from press.press.doctype.incident_settings_user.incident_settings_user import IncidentSettingsUser
	from press.press.doctype.press_settings.press_settings import PressSettings


# Twilio call statuses that indicate the call has reached a terminal state
CALL_TERMINAL_STATUSES = frozenset(
	["canceled", "completed", "failed", "busy", "no-answer", "in-progress", "timeout"]
)

# Twilio call statuses that mean the call was actually answered
CALL_PICKUP_STATUSES = frozenset(["in-progress", "completed"])


class IncidentCommunication:
	def __init__(self, incident: Incident):
		self.incident = incident

	# ------------------------------------------------------------------
	# Twilio configuration
	# ------------------------------------------------------------------

	@cached_property
	def twilio_phone_number(self) -> Phone:
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		return Phone(press_settings.twilio_phone_number)

	@property
	def twilio_client(self):
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		try:
			return press_settings.twilio_client
		except Exception:
			frappe.log_error("Twilio Client not configured in Press Settings")
			if not frappe.flags.in_test:
				frappe.db.commit()
			raise

	# ------------------------------------------------------------------
	# On-call engineers
	# ------------------------------------------------------------------

	def get_on_call_engineers(self) -> list[IncidentSettingsUser | IncidentSettingsSelfHostedUser]:
		"""Return the on-call team for this incident, with the acknowledging user moved to the front."""
		is_self_hosted = frappe.db.exists(
			"Self Hosted Server", {"server": self.incident.server}
		) or frappe.db.get_value("Server", self.incident.server, "is_self_hosted")

		users = self.incident.settings.self_hosted_users if is_self_hosted else self.incident.settings.users
		users_copy = users[:]

		if self.incident.status == "Acknowledged":
			for user in users:
				if user.user == self.incident.acknowledged_by:
					users_copy.remove(user)
					users_copy.insert(0, user)
					break

		return users_copy

	# ------------------------------------------------------------------
	# Phone calls : on-call engineers
	# ------------------------------------------------------------------

	def call_on_call_engineers(self):
		if (
			self.incident.is_ignore_incident_for_server
			or not self.incident.phone_call
			or not self.incident.settings.phone_call_alerts
		):
			return

		for human in self.get_on_call_engineers():
			status, _ = self._call_human(human.phone, wait_for_pickup=True)
			if not status:
				return  # Twillio unavailable

			acknowledged = status in CALL_PICKUP_STATUSES
			self._add_acknowledgment_update(human, acknowledged=acknowledged, call_status=status)

			if acknowledged:
				break

	# ------------------------------------------------------------------ #
	# Phone calls : customer alerts                                        #
	# ------------------------------------------------------------------ #

	def call_customers(self):
		if not self.incident.settings.phone_call_alerts or self.incident.called_customer:
			return

		phone_nos = get_communication_info("Phone Call", "Incident", "Server", self.incident.server)
		if not phone_nos:
			return

		for phone_no in phone_nos:
			self._call_human(phone_no, wait_for_pickup=False)

		self.incident.add_comment("Comment", f"Called customers at {', '.join(phone_nos)}")
		self.incident.called_customer = 1
		self.incident.save()

	# ------------------------------------------------------------------ #
	# Email                                                                #
	# ------------------------------------------------------------------ #

	def send_email_notification(self):
		if not self.incident.settings.email_alerts:
			return

		if self.incident.status == "Investigating":
			return

		team = frappe.db.get_value("Server", self.incident.server, "team")
		if not self.incident.server or not team:
			return

		server_name = (
			str(frappe.db.get_value("Server", self.incident.server, "title")).removesuffix(" - Application")
			or self.incident.server
		)
		acknowledged_by = (
			frappe.db.get_value("User", self.incident.acknowledged_by, "first_name")
			if self.incident.acknowledged_by
			else "An engineer"
		)

		status_messages = {
			"Validating": (
				"We are noticing some issues with sites on your server. "
				"We are giving it a few minutes to confirm before escalating this incident to our engineers."
			),
			"Auto-Resolved": (
				"Your sites are now up! This incident has resolved on its own. "
				"We will keep monitoring your sites for any further issues."
			),
			"Confirmed": (
				"We are still noticing issues with your sites. "
				"We are escalating this incident to our engineers."
			),
			"Acknowledged": (
				f"{acknowledged_by} from our team has acknowledged the incident and is actively investigating. "
				"Please allow them some time to diagnose and address the issue."
			),
			"Resolved": (
				f"Your sites are now up! {acknowledged_by} has resolved this incident. "
				"We will keep monitoring your sites for any further issues."
			),
		}

		self._send_mail(
			f"Incident on {server_name} - {self.incident.alert}", status_messages[self.incident.status]
		)

	def send_disk_full_mail(self):
		title = str(frappe.db.get_value("Server", self.incident.server, "title"))
		if self.incident.resource_type:
			title = str(frappe.db.get_value(self.incident.resource_type, self.incident.resource, "title"))

		subject = f"Disk Full Incident on {title}"
		message = f"""
		<p>Dear User,</p>
		<p>You are receiving this mail as the storage has been filled up on your server: <strong>{self.incident.resource}</strong> and you have <a href="https://docs.frappe.io/cloud/storage-addons#steps-to-disable-auto-increase-storage">automatic addition</a> of storage disabled.</p>
		<p>Please enable automatic addition of storage or <a href="https://docs.frappe.io/cloud/storage-addons#steps-to-add-storage-manually">add more storage manually</a> to resolve the issue.</p>
		<p>Best regards,<br/>Frappe Cloud Team</p>
		"""
		self._send_mail(subject, message)

	# ------------------------------------------------------------------ #
	# SMS                                                                  #
	# ------------------------------------------------------------------ #

	def send_sms_to_on_call_engineers(self):
		"""Send an SMS alert to each on-call team member.

		Twilio requires one API call per recipient.
		Ref: https://support.twilio.com/hc/en-us/articles/223181548
		"""
		if self.incident.is_ignore_incident_for_server:
			return

		domain = frappe.db.get_value("Press Settings", None, "domain")
		incident_link = f"https://{domain}{self.incident.get_url()}"
		message = (
			f"Incident on server: {self.incident.server}\n\nURL: {incident_link}\n\nID: {self.incident.name}"
		)

		for human in self.get_on_call_engineers():
			self.twilio_client.messages.create(to=human.phone, from_=self.twilio_phone_number, body=message)

		self.incident.reload()  # refresh in case acknowledgement changed before SMS was sent
		self.incident.sms_sent = 1
		self.incident.save()

	# ------------------------------------------------------------------
	# Helpers
	# ------------------------------------------------------------------

	def _send_mail(self, subject: str, message: str):
		try:
			frappe.sendmail(
				recipients=get_communication_info("Email", "Server Activity", "Server", self.incident.server),
				subject=subject,
				reference_doctype=self.incident.doctype,
				reference_name=self.incident.name,
				template="incident",
				args={
					"message": message,
					"link": f"dashboard/servers/{self.incident.server}/analytics/",
				},
				now=True,
			)
		except Exception:
			frappe.log_error("Incident Notification Email Failed")

	def _call_human(
		self, phone_no: str, wait_for_pickup: bool = True
	) -> tuple[str | None, CallInstance | None]:
		if not self.twilio_phone_number or self.incident.is_ignore_incident_for_server:
			return None, None

		server_title = str(
			frappe.db.get_value("Server", self.incident.server, "title") or self.incident.server
		).removesuffix(" - Application")

		if not server_title:
			return None, None

		server_title_encoded = urllib.parse.quote(server_title)
		press_public_base_url = frappe.utils.get_url(frappe.conf.get("press_url"))

		call: CallInstance | None = None
		try:
			call = self.twilio_client.calls.create(
				url=f"{press_public_base_url}/api/method/press.api.message.confirmed_incident?server_title={server_title_encoded}",
				to=phone_no,
				from_=self.twilio_phone_number,
			)
			status = str(call.status)

			if wait_for_pickup:
				status = self._wait_for_call_pickup(call)

			return status, call
		except RetryError:
			return "timeout", call  # not a Twilio status; call was never answered
		except TwilioRestException:
			TelegramMessage.enqueue(
				f"Unable to reach Twilio for Incident in {self.incident.server}\n\n"
				"Likely due to insufficient balance or incorrect credentials",
				reraise=True,
			)
			return None, None

	@retry(
		retry=retry_if_not_result(lambda result: result in CALL_TERMINAL_STATUSES),
		wait=wait_fixed(1),
		stop=stop_after_attempt(30),
	)
	def _wait_for_call_pickup(self, call: CallInstance):
		return call.fetch().status

	def _add_acknowledgment_update(
		self,
		human: IncidentSettingsUser | IncidentSettingsSelfHostedUser,
		call_status: str | None = None,
		acknowledged=False,
		save: bool = True,
	):
		"""Adds a new update to the Incident Document."""
		if acknowledged:
			update_note = f"Acknowledged by {human.user}"
			self.incident.acknowledge(human.user, save=False)
		else:
			update_note = f"Acknowledgement failed for {human.user}"

		if call_status:
			update_note += f" with call status {call_status}"

		self.incident.append(
			"updates",
			{
				"update_note": update_note,
				"update_time": frappe.utils.now(),
			},
		)

		if save:
			self.incident.save()
