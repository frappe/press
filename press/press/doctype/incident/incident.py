# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from twilio.rest import Client
from frappe.website.website_generator import WebsiteGenerator


class Incident(WebsiteGenerator):
	def on_update(self):
		pass

	def validate(self):
		if self.status == "Confirmed" and self.sms_sent == 0:
			self.send_sms_via_twilio()
		if self.status == "Acknowledged" and len(self.updates) < 1:
			self.add_acknowledgment_update()

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
		press_settings = frappe.get_doc("Press Settings")
		try:
			account_sid = press_settings.twilio_account_sid
			auth_token = press_settings.get_password("twilio_auth_token")
		except:
			frappe.msgprint(
				"Twilio credentials are not entered in Press Settings.",
				title="Notification cannot be sent",
				indicator="Red",
			)
			return
		incident_link = f"https://frappecloud.com/app/incident/{self.name}"
		message_body = f"New Incident {self.name} Reported\n\nSubject: {self.alertname}\nType: {self.type}\nHosted on: {self.server}\n\nIncident URL: {incident_link}"
		client = Client(account_sid, auth_token) # Initialize Twilio Client
		for number in phone_numbers: # Looping the Numbers one by one
			if number:client.messages.create(
					to=number,
					from_=press_settings.twilio_phone_number,
					body=message_body
				)
		self.sms_sent = 1

	def add_acknowledgment_update(self):
		"""
		Adds a new update to the Incident Document
		"""
		self.append(
			"updates",
			{
				"update_note": f"Incident Acknowledged by {self.acknowledged_by} and have started working on the Incident",
				"update_time": frappe.utils.frappe.utils.now(),
			},
		)

	def set_acknowledgement(self, acknowledged_by):
		"""
		Sets the Incident status to Acknowledged
		"""
		self.status = "Acknowledged"
		self.acknowledged_by = acknowledged_by
		self.save()
