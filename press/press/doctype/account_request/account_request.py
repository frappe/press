# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
from frappe.model.document import Document
from frappe.utils import get_url, random_string

from press.guards import settings
from press.utils import disposable_emails, get_country_info, is_valid_email_address, log_error
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
		agreed_to_terms: DF.Check
		company: DF.Data | None
		continent: DF.Data | None
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
		is_mobile: DF.Check
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
		request_key_expiration_time: DF.Datetime | None
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
			self.request_key_expiration_time = frappe.utils.add_to_date(minutes=10)

		if not self.otp:
			self.otp = generate_otp()
			self.otp_generated_at = frappe.utils.now_datetime()
			if frappe.conf.developer_mode and frappe.local.dev_server:
				self.otp = 111111

		self.ip_address = frappe.local.request_ip
		geo_location = self.get_country_info() or {}
		self.geo_location = json.dumps(geo_location, indent=1, sort_keys=True)
		self.state = geo_location.get("regionName")
		self.country = geo_location.get("country")
		self.is_mobile = geo_location.get("mobile", False)
		self.continent = geo_location.get("continent")

		# check for US and EU
		if (
			geo_location.get("country") == "United States"
			or geo_location.get("continent") == "Europe"
			or self.country == "United States"
		):
			self.is_us_eu = True
		else:
			self.is_us_eu = False

	def before_validate(self):
		self.email = self.email.strip()

	def validate(self):
		self.disallow_disposable_emails()

	@settings.enabled("disallow_disposable_emails")
	def disallow_disposable_emails(self):
		"""
		Disallow temporary email providers for account requests. Throws
		validation error if a temporary email provider is detected.
		"""
		if frappe.conf.developer_mode and frappe.local.dev_server:
			return
		if not self.email:
			return
		if disposable_emails.is_disposable(self.email):
			frappe.throw(
				"Temporary email providers are not allowed.",
				frappe.ValidationError,
			)

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
			capture("account_request_created", "fc_product_trial", self.email)

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
		if not self.request_key:
			self.request_key = random_string(32)
			self.request_key_expiration_time = frappe.utils.add_to_date(minutes=10)
		self.otp = generate_otp()
		if frappe.conf.developer_mode and frappe.local.dev_server:
			self.otp = 111111
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def send_verification_email(self):  # noqa: C901
		url = self.get_verification_url()

		if frappe.conf.developer_mode and frappe.local.dev_server:
			print(f"\nSetup account URL for {self.email}:")
			print(url)
			print(f"\nOTP for {self.email}:")
			print(self.otp)
			print()
			return

		subject = f"{self.otp} - OTP for Frappe Cloud Account Verification"
		args = {}
		sender = ""
		inline_images = []
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
					try:
						logo_name = product_trial.email_full_logo[1:]
						args.update({"logo_name": logo_name})
						with open(frappe.utils.get_site_path("public", logo_name), "rb") as logo_file:
							inline_images.append(
								{
									"filename": logo_name,
									"filecontent": logo_file.read(),
								}
							)
					except Exception as ex:
						log_error(
							"Error reading logo for inline images in email",
							data=ex,
							reference_doctype=self.doctype,
							reference_name=self.name,
						)
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
		if not (self.is_saas_signup() or self.invited_by_parent_team):
			# Telemetry: Verification Mail Sent
			capture("verification_email_sent", "fc_signup", self.email)
		if self.is_using_new_saas_flow():
			# Telemetry: Verification Email Sent for new saas flow when coming from product page
			capture("verification_email_sent", "fc_product_trial", self.name)

		try:
			frappe.sendmail(
				sender=sender,
				recipients=self.email,
				subject=subject,
				template=template,
				args=args,
				now=True,
				reference_doctype=self.doctype,
				reference_name=self.name,
				inline_images=inline_images,
			)
		except frappe.ValidationError:
			pass
		except Exception as e:
			log_error(
				"Error sending verification email",
				data=e,
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

	def send_otp_mail(self, for_login: bool = True):
		if frappe.conf.developer_mode and frappe.local.dev_server:
			print(
				f"Login OTP for {self.email}:"
				if for_login
				else f"OTP to view 2FA recovery codes for {self.email}:"
			)
			print(self.otp)
			print()
			return

		if hasattr(frappe.flags, "in_test") and frappe.flags.in_test:
			return

		if for_login:
			template = "login_otp"
			subject = f"{self.otp} - OTP for Frappe Cloud Login"
		else:
			template = "2fa_recovery_codes_otp"
			subject = f"{self.otp} - OTP to view 2FA recovery codes for Frappe Cloud"

		args = {
			"otp": self.otp,
		}

		frappe.sendmail(
			recipients=self.email,
			subject=subject,
			template=template,
			args=args,
			now=True,
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def get_verification_url(self):
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


def expire_request_key():
	"""
	Expire the request key requested 10 minutes ago.
	"""
	frappe.db.set_value(
		"Account Request",
		{
			"request_key_expiration_time": ("<", frappe.utils.now_datetime()),
			"request_key": ["is", "set"],
		},
		{
			"request_key": "",
			"request_key_expiration_time": None,
		},
		update_modified=False,
	)
