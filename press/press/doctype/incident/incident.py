# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.background_jobs import enqueue_doc
from frappe.website.website_generator import WebsiteGenerator
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed
from tenacity.retry import retry_if_not_result

from press.utils import log_error

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from press.press.doctype.incident_settings_user.incident_settings_user import (
		IncidentSettingsUser,
	)
	from press.press.doctype.press_settings.press_settings import PressSettings


class Incident(WebsiteGenerator):
	def on_update(self):
		pass

	def validate(self):
		if not hasattr(self, "phone_call"):
			if frappe.get_cached_value("Incident Settings", None, "phone_call_alerts"):
				self.phone_call = True

	def after_insert(self):
		if self.phone_call:
			enqueue_doc(self.doctype, self.name, "_call_humans", queue="long")

	def get_humans(self) -> list["IncidentSettingsUser"]:
		"""
		Returns a list of users who are in the incident team
		"""
		incident_settings = frappe.get_cached_doc("Incident Settings")
		return incident_settings.users

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
			lambda result: result in ["canceled", "completed", "failed", "busy", "no-answer"]
		),
		wait=wait_fixed(1),
		stop=stop_after_attempt(30),
	)
	def wait_for_pickup(self, call):
		return call.fetch().status  # will eventually be no-answer

	def _call_humans(self):
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
				status = "timeout"  # not twilio's status; mostly no-answer
			else:
				if status == "completed":  # call was picked up
					acknowledged = True
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
		assigned_users = self.get_assigned_users()
		phone_numbers = (
			frappe.db.get_value("User", x, "phone")
			for x in assigned_users
			if frappe.db.get_value("User", x, "phone") is not None
		)  # make a generator object of phone numbers
		incident_link = f"https://frappecloud.com/app/incident/{self.name}"
		message_body = f"New Incident {self.name} Reported\n\nSubject: {self.alertname}\nType: {self.type}\nHosted on: {self.server}\n\nIncident URL: {incident_link}"
		for number in phone_numbers:  # Looping the Numbers one by one
			if number:
				self.twilio_client.messages.create(
					to=number, from_=self.twilio_phone_number, body=message_body
				)
		self.sms_sent = 1

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
