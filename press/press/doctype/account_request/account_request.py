# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import json
import random

import frappe
from frappe.model.document import Document
from frappe.utils import get_url, random_string

from press.utils import get_country_info
from press.utils.telemetry import capture


class AccountRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.account_request_press_role.account_request_press_role import (
			AccountRequestPressRole,
		)

		agreed_to_partner_consent: DF.Check
		company: DF.Data | None
		country: DF.Data | None
		designation: DF.Data | None
		email: DF.Data | None
		erpnext: DF.Check
		first_name: DF.Data | None
		geo_location: DF.Code | None
		industry: DF.Data | None
		invited_by: DF.Data | None
		invited_by_parent_team: DF.Check
		ip_address: DF.Data | None
		is_us_eu: DF.Check
		last_name: DF.Data | None
		new_signup_flow: DF.Check
		no_of_employees: DF.Data | None
		no_of_users: DF.Int
		oauth_signup: DF.Check
		otp: DF.Data | None
		phone_number: DF.Data | None
		plan: DF.Link | None
		press_roles: DF.TableMultiSelect[AccountRequestPressRole]
		product_trial: DF.Link | None
		referral_source: DF.Data | None
		referrer_id: DF.Data | None
		request_key: DF.Data | None
		role: DF.Data | None
		saas: DF.Check
		saas_app: DF.Link | None
		saas_signup_values: DF.SmallText | None
		send_email: DF.Check
		state: DF.Data | None
		subdomain: DF.Data | None
		team: DF.Data | None
		url_args: DF.Code | None
	# end: auto-generated types

	def before_insert(self):
		if not self.team:
			self.team = self.email

		if not self.request_key:
			self.request_key = random_string(32)

		if not self.otp:
			self.otp = random.randint(10000, 99999)

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
		if not self.is_saas_signup():
			# Telemetry: Account Request Created
			capture("account_request_created", "fc_signup", self.email)
		if self.send_email:
			self.send_verification_email()
		else:
			if not self.is_saas_signup():
				# Telemetry: Verification Mail Sent
				# If user used oauth, we don't send verification email but to track the event in stat, send this event
				capture("verification_email_sent", "fc_signup", self.email)

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

	def reset_otp(self):
		self.otp = random.randint(10000, 99999)
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def send_verification_email(self):
		url = self.get_verification_url()

		if frappe.conf.developer_mode:
			print(f"\nSetup account URL for {self.email}:")
			print(url)
			print(f"\nOTP for {self.email}:")
			print(self.otp)
			print()
			return

		subject = f"{self.otp} - OTP for Frappe Cloud Account Verification"
		args = {}

		custom_template = self.saas_app and frappe.db.get_value(
			"Marketplace App", self.saas_app, "custom_verify_template"
		)
		if self.product_trial or custom_template:
			template = "saas_verify_account"
		else:
			template = "verify_account"

			if self.invited_by and self.role != "Press Admin":
				subject = f"You are invited by {self.invited_by} to join Frappe Cloud"
				template = "invite_team_member"

		args.update(
			{
				"invited_by": self.invited_by,
				"link": url,
				# "image_path": "/assets/press/images/frappe-logo-black.png",
				"image_path": "https://github.com/frappe/gameplan/assets/9355208/447035d0-0686-41d2-910a-a3d21928ab94",
				"read_pixel_path": get_url(
					f"/api/method/press.utils.telemetry.capture_read_event?email={self.email}"
				),
				"otp": self.otp,
			}
		)
		if not self.is_saas_signup():
			# Telemetry: Verification Mail Sent
			capture("verification_email_sent", "fc_signup", self.email)
		frappe.sendmail(
			recipients=self.email,
			subject=subject,
			template=template,
			args=args,
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
		return " ".join(filter(None, [self.first_name, self.last_name]))

	def get_site_name(self):
		return (
			self.subdomain + "." + frappe.db.get_value("Saas Settings", self.saas_app, "domain")
		)

	def is_saas_signup(self):
		# check whether it's a saas or erpnext signup
		if self.erpnext or self.saas:
			return True
		return False
