# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe
import json
from frappe.model.document import Document
from frappe.utils import formataddr, random_string, get_url
from press.utils import get_country_info


class AccountRequest(Document):
	def before_insert(self):
		if not self.team:
			self.team = self.email

		if not self.request_key:
			self.request_key = random_string(32)

		self.ip_address = frappe.local.request_ip
		geo_location = self.get_country_info() or {}
		self.geo_location = json.dumps(geo_location, indent=1, sort_keys=True)
		self.state = geo_location.get("regionName")

		# check for US and EU
		if (
			geo_location.get("country") == "United States"
			or geo_location.get("continent") == "Europe"
		):
			self.is_us_eu = True
		elif self.country == "United States":
			self.is_us_eu = True
		else:
			self.is_us_eu = False

	def after_insert(self):
		if self.send_email:
			self.send_verification_email()

	def get_country_info(self):
		return get_country_info()

	def too_many_requests_with_field(self, field_name, limits):
		key = getattr(self, field_name)
		for allowed_count, kwargs in limits:
			count = frappe.db.count(
				self.doctype,
				{field_name: key, "creation": (">", frappe.utils.add_to_date(None, **kwargs))},
			)
			if count > allowed_count:
				return True
		return False

	@frappe.whitelist()
	def send_verification_email(self):
		url = self.get_verification_url()
		signature, message, image_path = "", "", ""
		app_title = "ERPNext" if self.saas_app == "erpnext" else "Frappe Cloud"
		sender = ""

		if frappe.conf.developer_mode:
			print(f"\nSetup account URL for {self.email}:")
			print(url)
			print()
			return

		if self.saas_app and frappe.db.get_value(
			"Marketplace App", self.saas_app, "custom_verify_template"
		):
			app_title, subject, message, signature = frappe.db.get_value(
				"Marketplace App", self.saas_app, ["title", "subject", "message", "signature"]
			)
			message = frappe.render_template(message, {})
			signature = frappe.render_template(signature, {})
			image_path = frappe.db.get_value(
				"Saas Signup Generator", self.saas_app, "image_path"
			)
			template = "saas_verify_account"

			outgoing_email, outgoing_sender_name = frappe.db.get_value(
				"Marketplace App", self.saas_app, ["outgoing_email", "outgoing_sender_name"]
			)
			if outgoing_email:
				sender = formataddr((outgoing_sender_name, outgoing_email))
		else:
			subject = "Verify your account"
			template = "verify_account"

			if self.invited_by and self.role != "Press Admin":
				subject = f"You are invited by {self.invited_by} to join Frappe Cloud"
				template = "invite_team_member"

		frappe.sendmail(
			sender=sender,
			recipients=self.email,
			subject=subject,
			template=template,
			args={
				"link": url,
				"title": app_title,
				"message": message,
				"signature_text": signature,
				"image_path": image_path,
			},
			now=True,
		)

	def get_verification_url(self):
		if self.saas:
			return get_url(
				f"/api/method/press.api.saas.validate_account_request?key={self.request_key}"
			)

		return get_url(f"/dashboard/setup-account/{self.request_key}")

	@property
	def full_name(self):
		return self.first_name + " " + self.last_name
