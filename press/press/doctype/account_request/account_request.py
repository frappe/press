# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
from frappe.model.document import Document
from frappe.utils import get_url, random_string

from press.utils import get_country_info, is_valid_email_address
from press.utils.otp import generate_otp
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
		no_of_employees: DF.Data | None
		no_of_users: DF.Int
		oauth_signup: DF.Check
		otp: DF.Data | None
		otp_generated_at: DF.Datetime | None
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
		send_email: DF.Check
		state: DF.Data | None
		subdomain: DF.Data | None
		team: DF.Data | None
		unsubscribed_from_drip_emails: DF.Check
		url_args: DF.Code | None
	# end: auto-generated types

	def before_insert(self):
		# This pre-verification is only beneficial for SaaS signup
		# because, in general flow we already have e-mail link/otp based verification
		if (
			not frappe.conf.developer_mode
			and frappe.db.get_single_value("Press Settings", "enable_email_pre_verification")
			and self.saas
			and not self.oauth_signup
			and not is_valid_email_address(self.email)
		):
			frappe.throw(f"{self.email} is not a valid email address")

		if not self.team:
			self.team = self.email

		if not self.request_key:
			self.request_key = random_string(32)

		if not self.otp:
			self.otp = generate_otp()
			self.otp_generated_at = frappe.utils.now_datetime()
			if frappe.conf.developer_mode and frappe.local.dev_server:
				self.otp = 111111

		self.ip_address = frappe.local.request_ip
		geo_location = self.get_country_info() or {}
		self.geo_location = json.dumps(geo_location, indent=1, sort_keys=True)
		self.state = geo_location.get("regionName")

		# check for US and EU
		if (
			geo_location.get("country") == "United States"
			or geo_location.get("continent") == "Europe"
			or self.country == "United States"
		):
			self.is_us_eu = True
		else:
			self.is_us_eu = False

	def validate(self):
		self.email = self.email.strip()

	def after_insert(self):
		# Telemetry: Only capture if it's not a saas signup or invited by parent team. Also don't capture if user already have a team
		if not (
			frappe.db.exists("Team", {"user": self.email})
			or self.is_saas_signup()
			or self.invited_by_parent_team
		):
			# Telemetry: Account Request Created
			capture("account_request_created", "fc_signup", self.email)

		if self.is_saas_signup() and self.is_using_new_saas_flow():
			# Telemetry: Account Request Created
			capture("account_request_created", "fc_saas", self.email)

		if self.is_saas_signup() and not self.is_using_new_saas_flow():
			# If user used oauth, we don't need to verification email but to track the event in stat, send this dummy event
			capture("verification_email_sent", "fc_signup", self.email)
			capture("clicked_verify_link", "fc_signup", self.email)

		if self.send_email:
			self.send_verification_email()
		if self.oauth_signup:
			# Telemetry: simulate verification email sent
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
		self.otp = generate_otp()
		if frappe.conf.developer_mode and frappe.local.dev_server:
			self.otp = 111111
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def send_verification_email(self):  # noqa: C901
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
		sender = ""

		custom_template = self.saas_app and frappe.db.get_value(
			"Marketplace App", self.saas_app, "custom_verify_template"
		)
		if self.is_saas_signup() or custom_template:
			subject = "Verify your email for Frappe"
			template = "saas_verify_account"
			# If product trial(new saas flow), get the product trial details
			if self.product_trial:
				template = "product_trial_verify_account"
				product_trial = frappe.get_doc("Product Trial", self.product_trial)
				if product_trial.email_subject:
					subject = product_trial.email_subject.format(otp=self.otp)
				if product_trial.email_account:
					sender = frappe.get_value("Email Account", product_trial.email_account, "email_id")
				if product_trial.email_full_logo:
					args.update({"image_path": get_url(product_trial.email_full_logo, True)})
				args.update({"header_content": product_trial.email_header_content or ""})
			# If saas_app is set, check for email account in saas settings of that app
			elif self.saas_app:
				email_account = frappe.get_value("Saas Settings", self.saas_app, "email_account")
				if email_account:
					sender = frappe.get_value("Email Account", email_account, "email_id")
		else:
			template = "verify_account"

			if self.invited_by and self.role != "Press Admin":
				subject = f"You are invited by {self.invited_by} to join Frappe Cloud"
				template = "invite_team_member"

		args.update(
			{
				"invited_by": self.invited_by,
				"link": url,
				"read_pixel_path": get_url(
					f"/api/method/press.utils.telemetry.capture_read_event?email={self.email}"
				),
				"otp": self.otp,
			}
		)
		if not args.get("image_path"):
			args.update(
				{
					"image_path": "https://github.com/frappe/gameplan/assets/9355208/447035d0-0686-41d2-910a-a3d21928ab94"
				}
			)
		# Telemetry: Verification Email Sent
		# Only capture if it's not a saas signup or invited by parent team
		if not (self.is_saas_signup() or self.invited_by_parent_team):
			# Telemetry: Verification Mail Sent
			capture("verification_email_sent", "fc_signup", self.email)
		frappe.sendmail(
			sender=sender,
			recipients=self.email,
			subject=subject,
			template=template,
			args=args,
			now=True,
		)

	def send_login_mail(self):
		if frappe.conf.developer_mode and frappe.local.dev_server:
			print(rf"\Login OTP for {self.email}:")
			print(self.otp)
			print()
			return

		subject = f"{self.otp} - OTP for Frappe Cloud Login"
		args = {
			"otp": self.otp,
		}
		template = "login_otp"

		frappe.sendmail(
			recipients=self.email,
			subject=subject,
			template=template,
			args=args,
			now=True,
		)

	def get_verification_url(self):
		if self.saas:
			return get_url(f"/api/method/press.api.saas.validate_account_request?key={self.request_key}")
		return get_url(f"/dashboard/setup-account/{self.request_key}")

	@property
	def full_name(self):
		return " ".join(filter(None, [self.first_name, self.last_name]))

	def get_site_name(self):
		return self.subdomain + "." + frappe.db.get_value("Saas Settings", self.saas_app, "domain")

	def is_using_new_saas_flow(self):
		return bool(self.product_trial)

	def is_saas_signup(self):
		return bool(self.saas_app or self.saas or self.erpnext or self.product_trial)
