# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import os
from hashlib import blake2b
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.rate_limiter import rate_limit
from frappe.utils import get_fullname, get_last_day, get_url_to_form, getdate, random_string

from press.api.client import dashboard_whitelist
from press.exceptions import FrappeioServerNotSet
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.utils import get_valid_teams_for_user, has_role, log_error
from press.utils.billing import (
	get_frappe_io_connection,
	get_stripe,
	is_frappe_auth_disabled,
	process_micro_debit_test_charge,
)
from press.utils.telemetry import capture

if TYPE_CHECKING:
	from press.press.doctype.account_request.account_request import AccountRequest


class Team(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.child_team_member.child_team_member import ChildTeamMember
		from press.press.doctype.communication_info.communication_info import CommunicationInfo
		from press.press.doctype.invoice_discount.invoice_discount import InvoiceDiscount
		from press.press.doctype.team_member.team_member import TeamMember

		account_request: DF.Link | None
		allow_unified_servers: DF.Check
		apply_npo_discount: DF.Check
		benches_enabled: DF.Check
		billing_address: DF.Link | None
		billing_name: DF.Data | None
		billing_team: DF.Link | None
		child_team_members: DF.Table[ChildTeamMember]
		code_servers_enabled: DF.Check
		communication_infos: DF.Table[CommunicationInfo]
		company_logo: DF.Attach | None
		company_name: DF.Data | None
		country: DF.Link | None
		currency: DF.Link | None
		customers: DF.SmallText | None
		database_access_enabled: DF.Check
		default_payment_method: DF.Link | None
		default_razorpay_mandate: DF.Link | None
		discounts: DF.Table[InvoiceDiscount]
		enable_inplace_updates: DF.Check
		enable_performance_tuning: DF.Check
		enabled: DF.Check
		end_date: DF.Date | None
		enforce_2fa: DF.Check
		erpnext_partner: DF.Check
		extend_payment_due_suspension: DF.Check
		frappe_partnership_date: DF.Date | None
		free_account: DF.Check
		free_credits_allocated: DF.Check
		github_access_token: DF.Data | None
		hetzner_internal_user: DF.Check
		hybrid_servers_enabled: DF.Check
		introduction: DF.SmallText | None
		is_code_server_user: DF.Check
		is_developer: DF.Check
		is_saas_user: DF.Check
		is_us_eu: DF.Check
		last_used_team: DF.Link | None
		monthly_alert_threshold: DF.Currency
		mpesa_enabled: DF.Check
		mpesa_phone_number: DF.Data | None
		mpesa_tax_id: DF.Data | None
		parent_team: DF.Link | None
		partner_commission: DF.Percent
		partner_email: DF.Data | None
		partner_manager: DF.Link | None
		partner_referral_code: DF.Data | None
		partner_status: DF.Literal["Active", "Inactive"]
		partner_tier: DF.Link | None
		partnership_date: DF.Date | None
		payment_mode: DF.Literal["", "Card", "Prepaid Credits", "Paid By Partner"]
		phone_number: DF.Phone | None
		razorpay_enabled: DF.Check
		receive_budget_alerts: DF.Check
		referrer_id: DF.Data | None
		security_portal_enabled: DF.Check
		self_hosted_servers_enabled: DF.Check
		send_notifications: DF.Check
		servers_enabled: DF.Check
		skip_backups: DF.Check
		skip_onboarding: DF.Check
		ssh_access_enabled: DF.Check
		start_date: DF.Date | None
		stripe_customer_id: DF.Data | None
		team_members: DF.Table[TeamMember]
		team_title: DF.Data | None
		user: DF.Link | None
		via_erpnext: DF.Check
		website_link: DF.Data | None
	# end: auto-generated types

	dashboard_fields = (
		"enabled",
		"team_title",
		"user",
		"partner_email",
		"erpnext_partner",
		"enforce_2fa",
		"billing_team",
		"team_members",
		"child_team_members",
		"country",
		"currency",
		"payment_mode",
		"default_payment_method",
		"skip_backups",
		"is_saas_user",
		"billing_name",
		"referrer_id",
		"partner_referral_code",
		"parent_team",
		"is_developer",
		"enable_performance_tuning",
		"enable_inplace_updates",
		"servers_enabled",
		"benches_enabled",
		"mpesa_tax_id",
		"mpesa_phone_number",
		"mpesa_enabled",
		"razorpay_enabled",
		"account_request",
		"partner_status",
		"receive_budget_alerts",
		"monthly_alert_threshold",
		"company_name",
		"hybrid_servers_enabled",
	)

	def get_doc(self, doc):
		if (
			not frappe.local.system_user()
			and self.user != frappe.session.user
			and frappe.session.user not in self.get_user_list()
		):
			frappe.throw("You are not allowed to access this document")

		user = frappe.db.get_value(
			"User",
			frappe.session.user,
			["name", "first_name", "last_name", "user_image", "user_type", "email", "api_key"],
			as_dict=True,
		)
		user.is_2fa_enabled = frappe.db.get_value("User 2FA", {"user": user.name}, "enabled")
		doc.user_info = user
		doc.balance = self.get_balance()
		doc.is_desk_user = user.user_type == "System User"
		doc.is_support_agent = has_role("Press Support Agent")
		doc.can_request_access = has_role("Press Support Agent")
		doc.valid_teams = get_valid_teams_for_user(frappe.session.user)
		doc.onboarding = self.get_onboarding()
		doc.billing_info = self.billing_info()
		doc.billing_details = self.billing_details()
		doc.trial_sites = self.get_trial_sites()
		doc.pending_site_request = self.get_pending_saas_site_request()
		doc.payment_method = frappe.db.get_value(
			"Stripe Payment Method",
			{"team": self.name, "name": self.default_payment_method},
			[
				"name",
				"last_4",
				"name_on_card",
				"expiry_month",
				"expiry_year",
				"brand",
				"stripe_mandate_id",
			],
			as_dict=True,
		)
		doc.communication_infos = self.get_communication_infos()
		doc.receive_budget_alerts = self.receive_budget_alerts
		doc.monthly_alert_threshold = self.monthly_alert_threshold
		doc.is_binlog_indexer_enabled = not frappe.db.get_single_value(
			"Press Settings", "disable_binlog_indexer_service", cache=True
		)

	def onload(self):
		load_address_and_contact(self)

	@frappe.whitelist()
	def get_home_data(self):
		return {
			"sites": frappe.db.get_all(
				"Site",
				{"team": self.name, "status": ["!=", "Archived"]},
				["name", "host_name", "status"],
			),
		}

	def validate(self):
		self.validate_duplicate_members()
		self.set_team_currency()
		self.set_default_user()
		self.set_billing_name()
		self.set_partner_email()
		self.unset_saas_team_type_if_required()
		self.validate_disable()
		self.validate_billing_team()

	def before_insert(self):
		self.currency = "INR" if self.country == "India" else "USD"

		if not self.referrer_id:
			self.set_referrer_id()

	def set_referrer_id(self):
		h = blake2b(digest_size=4)
		h.update(self.user.encode())
		self.referrer_id = h.hexdigest()

	def set_partner_email(self):
		if self.erpnext_partner and not self.partner_email:
			self.partner_email = self.user

	def validate_disable(self):
		if self.has_value_changed("enabled") and self.enabled == 0 and has_unsettled_invoices(self.name):
			frappe.throw(
				"Cannot disable team with Draft or Unpaid invoices. Please finalize and settle the pending invoices first"
			)

	def validate_billing_team(self):
		if not (self.billing_team and self.payment_mode == "Paid By Partner"):
			return

		if self.payment_mode == "Paid By Partner" and not self.billing_team:
			frappe.throw("Billing Team is mandatory for Paid By Partner payment mode")

		if self.payment_mode == "Paid By Partner" and has_unsettled_invoices(self.name):
			frappe.throw(
				"Cannot set payment mode to Paid By Partner. Please finalize and settle the pending invoices first"
			)

	def delete(self, force=False, workflow=False):
		if not (force or workflow):
			frappe.throw(
				f"You are only deleting the Team Document for {self.name}. To continue to"
				" do so, pass force=True with this call. Else, pass workflow=True to raise"
				" a Team Deletion Request to trigger complete team deletion process."
			)

		if force:
			return super().delete()

		if workflow:
			return frappe.get_doc({"doctype": "Team Deletion Request", "team": self.name}).insert()

		frappe.throw(
			f"You are only deleting the Team Document for {self.name}. To continue to"
			" do so, pass force=True with this call. Else, pass workflow=True to raise"
			" a Team Deletion Request to trigger complete team deletion process."
		)
		return None

	def disable_account(self):
		self.suspend_sites("Account disabled")
		self.enabled = False
		self.save()
		self.add_comment("Info", "disabled account")

	def enable_account(self):
		self.unsuspend_sites("Account enabled")
		self.enabled = True
		self.save()
		self.add_comment("Info", "enabled account")

	@classmethod
	def create_new(  # noqa: C901
		cls,
		account_request: AccountRequest,
		first_name: str,
		last_name: str,
		password: str | None = None,
		country: str | None = None,
		phone: str | None = None,
		is_us_eu: bool = False,
		via_erpnext: bool = False,
		user_exists: bool = False,
	):
		"""Create new team along with user (user created first)."""
		# Get full phone number with country code
		full_phone = None
		if phone and country:
			dialing_code = get_country_dialing_code(country)
			if dialing_code:
				full_phone = f"+{dialing_code}-{phone}"
			else:
				full_phone = phone

		team: "Team" = frappe.get_doc(
			{
				"doctype": "Team",
				"user": account_request.email,
				"country": country,
				"phone_number": full_phone,
				"enabled": 1,
				"via_erpnext": via_erpnext,
				"is_us_eu": is_us_eu,
				"account_request": account_request.name,
			}
		)

		if not user_exists:
			user = team.create_user(
				first_name, last_name, account_request.email, password, account_request.role
			)
		else:
			user = frappe.get_doc("User", account_request.email)
			user.append_roles(account_request.role)
			user.save(ignore_permissions=True)

		if frappe.db.exists("Team", {"user": user.name}):
			frappe.throw("You have already an account with same email. Please login using the same email.")

		team.team_title = "Parent Team"
		team.insert(ignore_permissions=True, ignore_links=True)
		team.append("team_members", {"user": user.name})
		if account_request.invited_by_parent_team:
			team.parent_team = account_request.invited_by

		if account_request.product_trial:
			team.is_saas_user = 1

		team.save(ignore_permissions=True)

		team.create_stripe_customer()

		if account_request.referrer_id:
			team.create_referral_bonus(account_request.referrer_id)

		if not team.via_erpnext and not account_request.invited_by_parent_team:
			team.create_upcoming_invoice()
		return team

	@staticmethod
	def create_user(first_name=None, last_name=None, email=None, password=None, role=None):
		user = frappe.new_doc("User")
		user.first_name = first_name
		user.last_name = last_name
		user.email = email
		user.owner = email
		user.new_password = password
		user.append_roles(role)
		user.flags.no_welcome_mail = True
		user.save(ignore_permissions=True)
		return user

	def create_user_for_member(
		self,
		first_name=None,
		last_name=None,
		email=None,
		password=None,
		role=None,
		press_roles=None,
		skip_validations=False,
	):
		user = frappe.db.get_value("User", email, ["name"], as_dict=True)
		if not user:
			user = self.create_user(first_name, last_name, email, password, role)

		self.append("team_members", {"user": user.name})
		self.save(ignore_permissions=True)

		for role in press_roles or []:
			frappe.get_doc("Press Role", role.press_role).add_user(
				user.name,
				skip_validations=skip_validations,
			)

	@dashboard_whitelist()
	def remove_team_member(self, member):
		member_to_remove = find(self.team_members, lambda x: x.user == member)
		if member_to_remove:
			self.remove(member_to_remove)

			PressRole = frappe.qb.DocType("Press Role")
			PressRoleUser = frappe.qb.DocType("Press Role User")
			roles = (
				frappe.qb.from_(PressRole)
				.join(PressRoleUser)
				.on((PressRoleUser.parent == PressRole.name) & (PressRoleUser.user == member))
				.where(PressRole.team == self.name)
				.select(PressRole.name)
				.run(as_dict=True, pluck="name")
			)

			for role in roles:
				frappe.get_doc("Press Role", role).remove_user(member)
		else:
			frappe.throw(f"Team member {frappe.bold(member)} does not exists")

		self.save(ignore_permissions=True)

	def set_billing_name(self):
		if not self.billing_name:
			self.billing_name = frappe.utils.get_fullname(self.user)

	def unset_saas_team_type_if_required(self):
		if (self.servers_enabled or self.benches_enabled) and self.is_saas_user:
			self.is_saas_user = 0

	def set_default_user(self):
		if not self.user and self.team_members:
			self.user = self.team_members[0].user

	def set_team_currency(self):
		if not self.currency and self.country:
			self.currency = "INR" if self.country == "India" else "USD"

	def get_user_list(self):
		return [row.user for row in self.team_members]

	def get_users_only_in_this_team(self):
		return [
			user
			for user in self.get_user_list()
			if not frappe.db.exists("Team Member", {"user": user, "parent": ("!=", self.name)})
		]

	def validate_duplicate_members(self):
		team_users = self.get_user_list()
		duplicate_members = [m for m in team_users if team_users.count(m) > 1]
		duplicate_members = list(set(duplicate_members))
		if duplicate_members:
			frappe.throw(
				_("Duplicate Team Members: {0}").format(", ".join(duplicate_members)),
				frappe.DuplicateEntryError,
			)

	def validate_payment_mode(self):  # noqa: C901
		if not self.payment_mode and self.get_balance() > 0:
			self.payment_mode = "Prepaid Credits"

		if self.has_value_changed("payment_mode"):
			if (
				self.payment_mode == "Card"
				and frappe.db.count("Stripe Payment Method", {"team": self.name}) == 0
			):
				frappe.throw("No card added")
			if self.payment_mode == "Prepaid Credits" and self.get_balance() <= 0:
				frappe.throw("Account does not have sufficient balance")

		if not self.is_new() and not self.default_payment_method:
			# if default payment method is unset
			# then set the is_default field for Stripe Payment Method to 0
			payment_methods = frappe.db.get_list(
				"Stripe Payment Method", {"team": self.name, "is_default": 1}
			)
			for pm in payment_methods:
				doc = frappe.get_doc("Stripe Payment Method", pm.name)
				doc.is_default = 0
				doc.save()

		# Telemetry: Payment Mode Changed Event (Only for teams which have came through FC Signup and not via invite)
		if self.has_value_changed("payment_mode") and self.payment_mode and self.account_request:
			old_doc = self.get_doc_before_save()
			# Validate that the team has no payment method set previously
			if (not old_doc) or (not old_doc.payment_mode):
				ar: "AccountRequest" = frappe.get_doc("Account Request", self.account_request)
				# Only capture if it's not a saas signup or invited by parent team
				if not (ar.is_saas_signup() or ar.invited_by_parent_team):
					capture("added_card_or_prepaid_credits", "fc_signup", self.user)

	def on_update(self):
		if not self.enabled:
			return

		self.validate_payment_mode()
		self.update_draft_invoice_payment_mode()
		self.check_budget_alert_threshold()

		if (
			not self.is_new()
			and self.billing_name
			and not frappe.conf.allow_tests
			and self.has_value_changed("billing_name")
		):
			self.update_billing_details_on_frappeio()

	def update_draft_invoice_payment_mode(self):
		if self.has_value_changed("payment_mode"):
			draft_invoices = frappe.get_all(
				"Invoice", filters={"docstatus": 0, "team": self.name}, pluck="name"
			)

			for invoice in draft_invoices:
				frappe.db.set_value("Invoice", invoice, "payment_mode", self.payment_mode)

	def check_budget_alert_threshold(self):
		if self.receive_budget_alerts and self.has_value_changed("monthly_alert_threshold"):
			frappe.db.set_value(
				"Invoice",
				{"team": self.name, "docstatus": 0, "due_date": get_last_day(getdate())},
				"budget_alert_sent",
				0,
			)

	@frappe.whitelist()
	def impersonate(self, member, reason):
		user = frappe.db.get_value("Team Member", member, "user")
		impersonation = frappe.get_doc(
			{
				"doctype": "Team Member Impersonation",
				"user": user,
				"impersonator": frappe.session.user,
				"team": self.name,
				"member": member,
				"reason": reason,
			}
		)
		impersonation.save()
		frappe.local.login_manager.login_as(user)

	@frappe.whitelist()
	def enable_erpnext_partner_privileges(self):
		self.erpnext_partner = 1
		if not self.partner_email:
			self.partner_email = self.user
		self.frappe_partnership_date = self.get_partnership_start_date()
		self.servers_enabled = 1
		self.partner_status = "Active"
		self.save(ignore_permissions=True)
		frappe.get_doc("User", self.user).add_roles("Partner")
		self.create_partner_referral_code()

	@frappe.whitelist()
	def disable_erpnext_partner_privileges(self):
		self.partner_status = "Inactive"
		self.save(ignore_permissions=True)
		frappe.get_doc("User", self.user).remove_roles("Partner")

	def create_partner_referral_code(self):
		if not self.partner_referral_code:
			self.partner_referral_code = random_string(10).upper()
			self.save(ignore_permissions=True)

	def get_partnership_start_date(self):
		if frappe.flags.in_test:
			return frappe.utils.getdate()

		if is_frappe_auth_disabled():
			return frappe.utils.getdate()

		client = get_frappe_io_connection()
		data = client.get_value("Partner", "start_date", {"email": self.partner_email})
		if not data:
			frappe.throw("Partner not found on frappe.io")
		return frappe.utils.getdate(data.get("start_date"))

	def create_referral_bonus(self, referrer_id):
		# Get team name with this this referrer id
		referrer_team = frappe.db.get_value("Team", {"referrer_id": referrer_id})
		frappe.get_doc(
			{"doctype": "Referral Bonus", "for_team": self.name, "referred_by": referrer_team}
		).insert(ignore_permissions=True)

	def has_member(self, user):
		return user in self.get_user_list()

	def is_defaulter(self):
		if self.free_account:
			return False

		try:
			unpaid_invoices = frappe.get_all(
				"Invoice",
				{
					"status": "Unpaid",
					"team": self.name,
					"docstatus": ("<", 2),
					"type": "Subscription",
				},
				pluck="name",
			)
		except frappe.DoesNotExistError:
			return False

		return unpaid_invoices

	def create_stripe_customer(self):
		if not self.stripe_customer_id:
			stripe = get_stripe()
			customer = stripe.Customer.create(email=self.user, name=get_fullname(self.user))
			self.stripe_customer_id = customer.id
			self.save()

	@dashboard_whitelist()
	def get_communication_infos(self):
		return (
			[{"channel": c.channel, "type": c.type, "value": c.value} for c in self.communication_infos]
			if hasattr(self, "communication_infos")
			else []
		)

	@dashboard_whitelist()
	def update_communication_infos(self, values: list[dict]):
		from press.press.doctype.communication_info.communication_info import (
			update_communication_infos as update_infos,
		)

		update_infos("Team", self.name, values)

	@frappe.whitelist()
	def update_billing_details(self, billing_details):
		if self.billing_address:
			address_doc = frappe.get_doc("Address", self.billing_address)
			if (address_doc.country != billing_details.country) and (
				address_doc.country == "India" or billing_details.country == "India"
			):
				frappe.throw("Cannot change country of billing address")
		else:
			if self.account_request:
				ar: "AccountRequest" = frappe.get_doc("Account Request", self.account_request)
				if not (ar.is_saas_signup() or ar.invited_by_parent_team):
					capture("added_billing_address", "fc_signup", self.user)
			address_doc = frappe.new_doc("Address")
			address_doc.address_title = billing_details.billing_name or self.billing_name
			address_doc.append(
				"links",
				{"link_doctype": self.doctype, "link_name": self.name, "link_title": self.name},
			)

		address_doc.update(
			{
				"address_line1": billing_details.address,
				"city": billing_details.city,
				"state": billing_details.state,
				"pincode": billing_details.get("postal_code", "").strip().replace(" ", ""),
				"country": billing_details.country,
				"gstin": billing_details.gstin,
			}
		)
		address_doc.save()
		address_doc.reload()

		self.billing_name = billing_details.billing_name or self.billing_name
		self.billing_address = address_doc.name
		self.save()
		self.reload()

		self.update_billing_details_on_stripe(address_doc)
		self.update_billing_details_on_frappeio()
		self.update_billing_details_on_draft_invoices()

	def update_billing_details_on_draft_invoices(self):
		draft_invoices = frappe.get_all("Invoice", {"team": self.name, "docstatus": 0}, pluck="name")
		for draft_invoice in draft_invoices:
			# Invoice.customer_name set by Invoice.validate()
			frappe.get_doc("Invoice", draft_invoice).save()

	def update_billing_details_on_frappeio(self):
		if frappe.flags.in_install:
			return

		if is_frappe_auth_disabled():
			return

		try:
			frappeio_client = get_frappe_io_connection()
		except FrappeioServerNotSet as e:
			if frappe.conf.developer_mode or os.environ.get("CI"):
				return
			raise e

		previous_version = self.get_doc_before_save()

		if not previous_version:
			self.load_doc_before_save()
			previous_version = self.get_doc_before_save()

		previous_billing_name = previous_version.billing_name

		if previous_billing_name and previous_billing_name != self.billing_name:
			try:
				frappeio_client.rename_doc("Customer", previous_billing_name, self.billing_name)
				frappe.msgprint(f"Renamed customer from {previous_billing_name} to {self.billing_name}")
			except Exception:
				log_error("Failed to rename customer on frappe.io", traceback=frappe.get_traceback())

	def update_billing_details_on_stripe(self, address=None):
		stripe = get_stripe()
		if not address:
			address = frappe.get_doc("Address", self.billing_address)

		country_code = frappe.db.get_value("Country", address.country, "code")
		stripe.Customer.modify(
			self.stripe_customer_id,
			address={
				"line1": address.address_line1,
				"postal_code": address.pincode,
				"city": address.city,
				"state": address.state,
				"country": country_code.upper(),
			},
		)

	def create_payment_method(
		self,
		payment_method_id,
		setup_intent_id,
		mandate_id,
		mandate_reference,
		set_default=False,
		verified_with_micro_charge=False,
	):
		stripe = get_stripe()
		payment_method = stripe.PaymentMethod.retrieve(payment_method_id)

		try:
			doc = frappe.get_doc(
				{
					"doctype": "Stripe Payment Method",
					"stripe_payment_method_id": payment_method["id"],
					"last_4": payment_method["card"]["last4"],
					"name_on_card": payment_method["billing_details"]["name"],
					"expiry_month": payment_method["card"]["exp_month"],
					"expiry_year": payment_method["card"]["exp_year"],
					"brand": payment_method["card"]["brand"] or "",
					"team": self.name,
					"stripe_setup_intent_id": setup_intent_id,
					"stripe_mandate_id": mandate_id if mandate_id else None,
					"stripe_mandate_reference": mandate_reference if mandate_reference else None,
					"is_verified_with_micro_charge": verified_with_micro_charge,
				}
			)
			doc.insert()
		except Exception:
			frappe.log_error("Failed to create new Stripe Payment Method")

		# unsuspend sites on payment method added
		self.unsuspend_sites(reason="Payment method added")
		if set_default:
			doc.set_default()
			self.reload()

		self.remove_subscription_config_in_trial_sites()

		return doc

	def get_payment_methods(self):
		return frappe.db.get_all(
			"Stripe Payment Method",
			{"team": self.name},
			[
				"name",
				"last_4",
				"name_on_card",
				"expiry_month",
				"expiry_year",
				"brand",
				"is_default",
				"creation",
			],
			order_by="creation desc",
		)

	def get_past_invoices(self):
		invoices = frappe.db.get_all(
			"Invoice",
			filters={
				"team": self.name,
				"status": ("not in", ("Draft", "Refunded")),
				"docstatus": ("!=", 2),
			},
			fields=[
				"name",
				"total",
				"amount_due",
				"status",
				"type",
				"stripe_invoice_url",
				"period_start",
				"period_end",
				"due_date",
				"payment_date",
				"currency",
				"invoice_pdf",
				"due_date as date",
			],
			order_by="due_date desc",
		)

		for invoice in invoices:
			invoice.formatted_total = frappe.utils.fmt_money(invoice.total, 2, invoice.currency)
			invoice.stripe_link_expired = False
			if invoice.status == "Unpaid":
				invoice.formatted_amount_due = frappe.utils.fmt_money(invoice.amount_due, 2, invoice.currency)
				days_diff = frappe.utils.date_diff(frappe.utils.now(), invoice.due_date)
				if days_diff > 30:
					invoice.stripe_link_expired = True
		return invoices

	def allocate_credit_amount(self, amount, source, remark=None, type="Adjustment"):
		doc = frappe.get_doc(
			doctype="Balance Transaction",
			team=self.name,
			type=type,
			source=source,
			amount=amount,
			description=remark,
		)
		doc.insert(ignore_permissions=True)
		doc.submit()

		self.reload()
		if not self.payment_mode:
			self.validate_payment_mode()
			self.save(ignore_permissions=True)
		return doc

	def get_available_credits(self):
		def get_stripe_balance():
			return self.get_stripe_balance()

		return frappe.cache().hget("customer_available_credits", self.name, generator=get_stripe_balance)

	def get_stripe_balance(self):
		stripe = get_stripe()
		customer_object = stripe.Customer.retrieve(self.stripe_customer_id)
		return (customer_object["balance"] * -1) / 100

	def is_team_owner(self) -> bool:
		"""
		Checks if the current user is the owner of the team.
		"""
		return bool(frappe.db.get_value("Team", self.name, "user") == frappe.session.user)

	def is_admin_user(self) -> bool:
		"""
		Checks if the current user has admin access in the team via roles.
		"""
		PressRole = frappe.qb.DocType("Press Role")
		PressRoleUser = frappe.qb.DocType("Press Role User")
		return (
			frappe.qb.from_(PressRoleUser)
			.left_join(PressRole)
			.on(PressRole.name == PressRoleUser.parent)
			.select(Count(PressRoleUser.name).as_("count"))
			.where(PressRole.team == self.name)
			.where(PressRoleUser.user == frappe.session.user)
			.where(PressRole.admin_access == 1)
			.run(as_dict=1)
			.pop()
			.get("count", 0)
			> 0
		)

	@dashboard_whitelist()
	def get_team_members(self):
		return get_team_members(self.name)

	@dashboard_whitelist()
	@rate_limit(limit=10, seconds=60 * 60)
	def invite_team_member(self, email, roles=None):
		from frappe.utils.user import is_system_user

		PressRole = frappe.qb.DocType("Press Role")
		PressRoleUser = frappe.qb.DocType("Press Role User")

		has_admin_access = (
			frappe.qb.from_(PressRole)
			.select(PressRole.name)
			.join(PressRoleUser)
			.on((PressRole.name == PressRoleUser.parent) & (PressRoleUser.user == frappe.session.user))
			.where(PressRole.team == self.name)
			.where(PressRole.admin_access == 1)
		)

		if not is_system_user() and frappe.session.user != self.user and not has_admin_access.run():
			frappe.throw(_("Only team owner or admins can invite team members"))

		frappe.utils.validate_email_address(email, True)

		if frappe.db.exists("Team Member", {"user": email, "parent": self.name, "parenttype": "Team"}):
			frappe.throw(_("Team member already exists"))

		if frappe.db.exists(
			"Account Request",
			{
				"email": email,
				"team": self.name,
				"invited_by": ("is", "set"),
				"request_key": ("is", "set"),
			},
		):
			frappe.throw("User has already been invited recently. Please try again later.")

		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"team": self.name,
				"email": email,
				"role": "Press Member",
				"invited_by": self.user,
				"send_email": True,
			}
		)

		for role in roles:
			account_request.append("press_roles", {"press_role": role})

		account_request.insert()

	@frappe.whitelist()
	def get_balance(self):
		res = frappe.get_all(
			"Balance Transaction",
			filters={"team": self.name, "docstatus": 1, "type": ("!=", "Partnership Fee")},
			order_by="creation desc",
			limit=1,
			pluck="ending_balance",
		)
		if not res:
			return 0
		return res[0]

	def can_create_site(self):  # noqa: C901
		why = ""
		allow = (True, "")

		if not self.enabled:
			why = "You cannot create a new site because your account is disabled"
			return (False, why)

		if self.free_account or self.parent_team or self.billing_team:
			return allow

		if self.is_saas_user and not self.payment_mode:
			if not frappe.db.get_all("Site", {"team": self.name}, limit=1):
				return allow
			why = "You have already created trial site in the past"

		# allow user to create their first site without payment method
		if not frappe.db.get_all("Site", {"team": self.name}, limit=1):
			return allow

		if not self.payment_mode:
			why = "You cannot create a new site because your account doesn't have a valid payment method."
			return (False, why)

		if self.payment_mode == "Prepaid Credits":
			# if balance is greater than 0 or have atleast 2 paid invoices, then allow to create site
			if (
				self.get_balance() > 0
				or frappe.db.count(
					"Invoice",
					{
						"team": self.name,
						"status": "Paid",
						"amount_paid": ("!=", 0),
					},
				)
				> 2
			):
				return allow
			why = "Cannot create site due to insufficient balance"

		if self.payment_mode == "Card":
			if self.default_payment_method:
				return allow
			why = "Cannot create site without adding a card"

		return (False, why)

	def can_install_paid_apps(self):
		if self.free_account or self.billing_team or self.payment_mode:
			return True

		return bool(
			frappe.db.exists("Invoice", {"team": self.name, "amount_paid": (">", 0), "status": "Paid"})
		)

	def billing_info(self):
		micro_debit_charge_field = (
			"micro_debit_charge_usd" if self.currency == "USD" else "micro_debit_charge_inr"
		)
		amount = frappe.db.get_single_value("Press Settings", micro_debit_charge_field)

		return {
			"gst_percentage": frappe.db.get_single_value("Press Settings", "gst_percentage"),
			"micro_debit_charge_amount": amount,
			"balance": self.get_balance(),
			"verified_micro_charge": bool(
				frappe.db.exists(
					"Stripe Payment Method", {"team": self.name, "is_verified_with_micro_charge": 1}
				)
			),
			"has_paid_before": bool(
				frappe.db.exists("Invoice", {"team": self.name, "amount_paid": (">", 0), "status": "Paid"})
			),
			"has_unpaid_invoices": bool(
				frappe.db.exists("Invoice", {"team": self.name, "status": "Unpaid", "type": "Subscription"})
			),
		}

	def billing_details(self, timezone=None):
		billing_details = frappe._dict()
		if self.billing_address:
			billing_details = frappe.get_doc("Address", self.billing_address).as_dict()
			billing_details.billing_name = self.billing_name

		if not billing_details.country and timezone:
			from press.utils.country_timezone import get_country_from_timezone

			billing_details.country = get_country_from_timezone(timezone)

		return billing_details

	def get_partner_level(self):
		# fetch partner level from frappe.io
		if frappe.flags.in_install:
			return None

		if is_frappe_auth_disabled():
			return None

		client = get_frappe_io_connection()
		response = client.session.get(
			f"{client.url}/api/method/get_partner_level",
			headers=client.headers,
			params={"email": self.partner_email},
		)

		if response.ok:
			res = response.json()
			partner_level = res.get("message")
			certificate_count = res.get("certificates")
			if partner_level:
				return [partner_level, certificate_count]
			return None

		self.add_comment(text="Failed to fetch partner level" + "<br><br>" + response.text)
		return None

	def is_payment_mode_set(self):
		if self.payment_mode in ("Prepaid Credits", "Paid By Partner") or (
			self.payment_mode == "Card" and self.default_payment_method and self.billing_address
		):
			return True
		return False

	def get_onboarding(self):
		site_created = frappe.db.count("Site", {"team": self.name}) > 0
		saas_site_request = self.get_pending_saas_site_request()
		is_payment_mode_set = self.is_payment_mode_set()
		if not is_payment_mode_set and self.parent_team:
			parent_team = frappe.get_cached_doc("Team", self.parent_team)
			is_payment_mode_set = parent_team.is_payment_mode_set()

		complete = False
		if (
			self.skip_onboarding
			or is_payment_mode_set
			or frappe.db.get_value("User", self.user, "user_type") == "System User"
		):
			complete = True
		elif saas_site_request:
			complete = False

		return frappe._dict(
			{
				"site_created": site_created,
				"is_saas_user": bool(self.via_erpnext or self.is_saas_user),
				"saas_site_request": saas_site_request,
				"complete": complete,
				"is_payment_mode_set": is_payment_mode_set,
			}
		)

	def get_route_on_login(self):
		if self.payment_mode or self.skip_onboarding:
			return "/sites"

		if self.is_saas_user:
			pending_site_request = self.get_pending_saas_site_request()
			if pending_site_request:
				return f"/create-site/{pending_site_request.product_trial}/setup?account_request={pending_site_request.account_request}"

		return "/welcome"

	def get_pending_saas_site_request(self):
		if frappe.db.exists("Product Trial Request", {"team": self.name, "status": "Site Created"}):
			return None

		return frappe.db.get_value(
			"Product Trial Request",
			{
				"team": self.name,
				"status": ("in", ["Pending", "Wait for Site", "Completing Setup Wizard", "Error"]),
			},
			["name", "product_trial", "product_trial.title", "status", "account_request"],
			order_by="creation desc",
			as_dict=True,
		)

	def get_trial_sites(self):
		return frappe.db.get_all(
			"Site",
			{
				"team": self.name,
				"is_standby": False,
				"trial_end_date": ("is", "set"),
				"status": ("!=", "Archived"),
			},
			["name", "trial_end_date", "standby_for_product.title as product_title", "host_name"],
			order_by="`tabSite`.`modified` desc",
		)

	@frappe.whitelist()
	def suspend_sites(self, reason=None):
		from press.press.doctype.site.site import Site

		sites_to_suspend = self.get_sites_to_suspend()
		for site in sites_to_suspend:
			try:
				Site("Site", site).suspend(reason)
			except Exception:
				log_error("Failed to Suspend Sites", traceback=frappe.get_traceback())
		return sites_to_suspend

	def get_sites_to_suspend(self):
		plan = frappe.qb.DocType("Site Plan")
		query = (
			frappe.qb.from_(plan)
			.select(plan.name)
			.where((plan.enabled == 1) & ((plan.is_frappe_plan == 1) | (plan.is_trial_plan == 1)))
		).run(as_dict=True)
		frappe_plans = [d.name for d in query]

		return frappe.db.get_all(
			"Site",
			{
				"team": self.name,
				"status": ("not in", ("Archived", "Suspended")),
				"free": 0,
				"plan": ("not in", frappe_plans),
			},
			pluck="name",
		)

	def reallocate_workers_if_needed(
		self, workloads_before: list[tuple[str, float, str]], workloads_after: list[tuple[str, float, str]]
	):
		for before, after in zip(workloads_before, workloads_after, strict=False):
			if after[1] - before[1] >= 8:  # 100 USD equivalent
				frappe.enqueue_doc(
					"Server",
					before[2],
					method="auto_scale_workers",
					job_id=f"auto_scale_workers:{before[2]}",
					deduplicate=True,
					enqueue_after_commit=True,
				)

	@frappe.whitelist()
	def unsuspend_sites(self, reason=None):
		from press.press.doctype.bench.bench import Bench
		from press.press.doctype.site.site import Site

		suspended_sites = [
			d.name for d in frappe.db.get_all("Site", {"team": self.name, "status": "Suspended"})
		]
		workloads_before = list(Bench.get_workloads(suspended_sites))
		for site in suspended_sites:
			Site("Site", site).unsuspend(reason)
		workloads_after = list(Bench.get_workloads(suspended_sites))
		self.reallocate_workers_if_needed(workloads_before, workloads_after)

		return suspended_sites

	def remove_subscription_config_in_trial_sites(self):
		for site in frappe.db.get_all(
			"Site",
			{"team": self.name, "status": ("!=", "Archived"), "trial_end_date": ("is", "set")},
			pluck="name",
		):
			try:
				frappe.get_doc("Site", site).update_site_config(
					{
						"subscription": {"status": "Subscribed"},
					}
				)
			except Exception:
				log_error("Failed to remove subscription config in trial sites")

	def get_upcoming_invoice(self, for_update=False):
		# get the current period's invoice
		today = frappe.utils.today()
		result = frappe.db.get_all(
			"Invoice",
			filters={
				"status": "Draft",
				"team": self.name,
				"type": "Subscription",
				"period_start": ("<=", today),
				"period_end": (">=", today),
			},
			order_by="creation desc",
			limit=1,
			pluck="name",
		)
		if result:
			return frappe.get_doc("Invoice", result[0], for_update=for_update)
		return None

	def create_upcoming_invoice(self):
		today = frappe.utils.today()
		return frappe.get_doc(
			doctype="Invoice", team=self.name, period_start=today, type="Subscription"
		).insert()

	@frappe.whitelist()
	def send_telegram_alert_for_failed_payment(self, invoice):
		team_url = get_url_to_form("Team", self.name)
		invoice_url = get_url_to_form("Invoice", invoice)
		message = f"Failed Invoice Payment [{invoice}]({invoice_url}) of Partner: [{self.name}]({team_url})"
		TelegramMessage.enqueue(message=message)

	@frappe.whitelist()
	def send_email_for_failed_payment(self, invoice, sites=None):
		invoice = frappe.get_doc("Invoice", invoice)
		email = get_communication_info("Email", "Billing", "Team", self.name)
		payment_method = self.default_payment_method
		last_4 = frappe.db.get_value("Stripe Payment Method", payment_method, "last_4")
		account_update_link = frappe.utils.get_url("/dashboard")
		subject = "Invoice Payment Failed for Frappe Cloud Subscription"

		frappe.sendmail(
			recipients=email,
			subject=subject,
			template="payment_failed_partner" if self.erpnext_partner else "payment_failed",
			args={
				"subject": subject,
				"payment_link": invoice.stripe_invoice_url,
				"amount": invoice.get_formatted("amount_due"),
				"account_update_link": account_update_link,
				"last_4": last_4 or "",
				"card_not_added": not payment_method,
				"sites": sites,
				"team": self,
			},
		)


def get_team_members(team):
	if not frappe.db.exists("Team", team):
		return []

	r = frappe.db.get_all("Team Member", filters={"parent": team}, fields=["user"])
	member_emails = [d.user for d in r]

	users = []
	if member_emails:
		users = frappe.db.sql(
			"""
				select
					u.name,
					u.first_name,
					u.last_name,
					u.full_name,
					u.user_image,
					u.name as email,
					GROUP_CONCAT(r.`role`) as roles
				from `tabUser` u
				left join `tabHas Role` r
				on (r.parent = u.name)
				where u.name in %s
				group by u.name
			""",
			[member_emails],
			as_dict=True,
		)
		for user in users:
			user.roles = (user.roles or "").split(",")

	return users


def get_child_team_members(team):
	if not frappe.db.exists("Team", team):
		return []

	# a child team cannot be parent to another child team
	if frappe.get_value("Team", team, "parent_team"):
		return []

	child_team_members = [d.name for d in frappe.db.get_all("Team", {"parent_team": team}, ["name"])]

	child_teams = []
	if child_team_members:
		child_teams = frappe.db.sql(
			"""
				select t.name, t.team_title, t.parent_team, t.user
				from `tabTeam` t
				where t.name in %s
				and t.enabled = 1
			""",
			[child_team_members],
			as_dict=True,
		)

	return child_teams


def get_default_team(user):
	if frappe.db.exists("Team", user):
		return user
	return None


def process_stripe_webhook(doc, method):
	"""This method runs after a Stripe Webhook Log is created"""

	if doc.event_type not in ["payment_intent.succeeded"]:
		return

	event = frappe.parse_json(doc.payload)
	payment_intent = event["data"]["object"]
	if payment_intent.get("invoice"):
		# ignore payment for invoice
		return

	metadata = payment_intent.get("metadata")
	payment_for = metadata.get("payment_for")

	if payment_for and payment_for == "micro_debit_test_charge":
		process_micro_debit_test_charge(event)
		return

	if payment_for and payment_for == "partnership_fee":
		process_partnership_fee(payment_intent)
		return

	handle_payment_intent_succeeded(payment_intent)


def handle_payment_intent_succeeded(payment_intent):  # noqa: C901
	from datetime import datetime

	if isinstance(payment_intent, str):
		stripe = get_stripe()
		payment_intent = stripe.PaymentIntent.retrieve(payment_intent)

	metadata = payment_intent.get("metadata")
	if frappe.db.exists("Invoice", {"stripe_payment_intent_id": payment_intent["id"], "status": "Paid"}):
		# ignore creating if already allocated
		return

	if not frappe.db.exists("Team", {"stripe_customer_id": payment_intent["customer"]}):
		# might be checkout session payment
		# log the stripe webhook log
		# TODO: handle checkout session payment
		return
	team: Team = frappe.get_doc("Team", {"stripe_customer_id": payment_intent["customer"]})
	amount_with_tax = payment_intent["amount"] / 100
	gst = float(metadata.get("gst", 0))
	amount = amount_with_tax - gst
	balance_transaction = team.allocate_credit_amount(
		amount, source="Prepaid Credits", remark=payment_intent["id"]
	)

	team.remove_subscription_config_in_trial_sites()
	invoice = frappe.get_doc(
		doctype="Invoice",
		team=team.name,
		type="Prepaid Credits",
		status="Paid",
		due_date=datetime.fromtimestamp(payment_intent["created"]),
		total=amount,
		amount_due=amount,
		gst=gst or 0,
		amount_due_with_tax=amount_with_tax,
		amount_paid=amount_with_tax,
		stripe_payment_intent_id=payment_intent["id"],
	)
	invoice.append(
		"items",
		{
			"description": "Prepaid Credits",
			"document_type": "Balance Transaction",
			"document_name": balance_transaction.name,
			"quantity": 1,
			"rate": amount,
		},
	)
	invoice.insert()
	invoice.reload()

	if not team.payment_mode:
		frappe.db.set_value("Team", team.name, "payment_mode", "Prepaid Credits")
		if team.account_request:
			ar: "AccountRequest" = frappe.get_doc("Account Request", team.account_request)
			if not (ar.is_saas_signup() or ar.invited_by_parent_team):
				capture("added_card_or_prepaid_credits", "fc_signup", team.user)

	# latest stripe API sets charge id in latest_charge
	charge = payment_intent.get("latest_charge")
	if not charge:
		# older stripe API sets charge id in charges.data
		charges = payment_intent.get("charges", {}).get("data", [])
		charge = charges[0]["id"] if charges else None
	if charge:
		# update transaction amount, fee and exchange rate
		invoice.update_transaction_details(charge)
		invoice.submit()

	_enqueue_finalize_unpaid_invoices_for_team(team.name)


def _enqueue_finalize_unpaid_invoices_for_team(team: str):
	# Enqueue a background job to call finalize_draft_invoice for unpaid invoices
	frappe.enqueue(
		"press.press.doctype.team.team.enqueue_finalize_unpaid_for_team",
		team=team,
		enqueue_after_commit=True,
	)


def enqueue_finalize_unpaid_for_team(team: str):
	# get a list of unpaid invoices for the team
	invoices = frappe.get_all(
		"Invoice",
		filters={"team": team, "status": "Unpaid", "type": "Subscription"},
		pluck="name",
	)

	# Enqueue a background job to call finalize_invoice
	for invoice in invoices:
		doc = frappe.get_doc("Invoice", invoice)
		doc.finalize_invoice()


def process_partnership_fee(payment_intent):
	from datetime import datetime

	if isinstance(payment_intent, str):
		stripe = get_stripe()
		payment_intent = stripe.PaymentIntent.retrieve(payment_intent)

	metadata = payment_intent.get("metadata")
	if frappe.db.exists("Invoice", {"stripe_payment_intent_id": payment_intent["id"], "status": "Paid"}):
		# ignore creating duplicate partnership fee invoice
		return

	team = frappe.get_doc("Team", {"stripe_customer_id": payment_intent["customer"]})
	amount_with_tax = payment_intent["amount"] / 100
	gst = float(metadata.get("gst", 0))
	amount = amount_with_tax - gst
	balance_transaction = team.allocate_credit_amount(
		amount, source="Prepaid Credits", remark=payment_intent["id"], type="Partnership Fee"
	)

	invoice = frappe.get_doc(
		doctype="Invoice",
		team=team.name,
		type="Partnership Fees",
		status="Paid",
		due_date=datetime.fromtimestamp(payment_intent["created"]),
		total=amount,
		amount_due=amount,
		gst=gst or 0,
		amount_due_with_tax=amount_with_tax,
		amount_paid=amount_with_tax,
		stripe_payment_intent_id=payment_intent["id"],
	)
	invoice.append(
		"items",
		{
			"description": "Partnership Fee",
			"document_type": "Balance Transaction",
			"document_name": balance_transaction.name,
			"quantity": 1,
			"rate": amount,
		},
	)
	invoice.insert()
	invoice.reload()

	# latest stripe API sets charge id in latest_charge
	charge = payment_intent.get("latest_charge")
	if not charge:
		# older stripe API sets charge id in charges.data
		charges = payment_intent.get("charges", {}).get("data", [])
		charge = charges[0]["id"] if charges else None
	if charge:
		# update transaction amount, fee and exchange rate
		invoice.update_transaction_details(charge)
		invoice.submit()


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "user_type", cache=True)
	if user_type == "System User":
		return ""

	team = get_current_team()

	return f"(`tabTeam`.`name` = {frappe.db.escape(team)})"


def has_permission(doc, ptype, user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "user_type", cache=True)
	if user_type == "System User":
		return True

	team = get_current_team(True)
	child_team_members = [d.name for d in frappe.db.get_all("Team", {"parent_team": team.name}, ["name"])]
	if doc.name == team.name or doc.name in child_team_members:
		return True

	return False


def validate_site_creation(doc, method):
	if frappe.session.user == "Administrator":
		return
	if not doc.team:
		return
	# allow product signups
	if doc.standby_for_product:
		return

	# validate site creation for team
	team = frappe.get_doc("Team", doc.team)
	[allow_creation, why] = team.can_create_site()
	if not allow_creation:
		frappe.throw(why)


def has_unsettled_invoices(team):
	if not frappe.db.exists(
		"Invoice", {"team": team, "status": ("in", ("Unpaid", "Draft")), "type": "Subscription"}
	):
		return False

	currency = frappe.db.get_value("Team", team, "currency")
	minimum_amount = 5
	if currency == "INR":
		minimum_amount = 450

	data = frappe.get_all(
		"Invoice",
		{"team": team, "status": ("in", ("Unpaid", "Draft")), "type": "Subscription"},
		["sum(amount_due) as amount_due"],
	)[0]
	if data.amount_due <= minimum_amount:
		return False
	return True


def is_us_eu():
	"""Is the customer from U.S. or European Union"""
	from press.utils import get_current_team

	countrygroup = [
		"United States",
		"United Kingdom",
		"Austria",
		"Belgium",
		"Bulgaria",
		"Croatia",
		"Republic of Cyprus",
		"Czech Republic",
		"Denmark",
		"Estonia",
		"Finland",
		"France",
		"Germany",
		"Greece",
		"Hungary",
		"Ireland",
		"Italy",
		"Latvia",
		"Lithuania",
		"Luxembourg",
		"Malta",
		"Netherlands",
		"Poland",
		"Portugal",
		"Romania",
		"Slovakia",
		"Slovenia",
		"Spain",
		"Sweden",
		"Switzerland",
		"Australia",
		"New Zealand",
		"Canada",
		"Mexico",
	]
	return frappe.db.get_value("Team", get_current_team(), "country") in countrygroup


def check_budget_alerts():
	"""
	Daily background job to check if teams have exceeded their monthly budget alert limits.
	Sends email notifications for invoices that have crossed the set limit.
	"""
	teams_with_budget_alert_enabled = frappe.get_all(
		"Team",
		filters={"receive_budget_alerts": 1, "monthly_alert_threshold": (">", 0), "enabled": 1},
		fields=["name", "monthly_alert_threshold", "currency", "user"],
	)

	if not teams_with_budget_alert_enabled:
		return

	team_names = [team["name"] for team in teams_with_budget_alert_enabled]
	team_dict = {team["name"]: team for team in teams_with_budget_alert_enabled}

	current_month_end = get_last_day(getdate())

	# Fetch current month invoices for all teams, filter out invoices that have already sent alerts
	current_invoices = frappe.get_all(
		"Invoice",
		filters={
			"team": ("in", team_names),
			"due_date": current_month_end,
			"status": "Draft",
			"budget_alert_sent": 0,
		},
		fields=[
			"name",
			"team",
			"total",
			"period_start",
			"period_end",
		],
		order_by="creation desc",
	)

	invoices_to_update = []  # To keep track of invoices that need budget_alert_sent field update
	for invoice in current_invoices:
		team_name = invoice["team"]
		monthly_limit = team_dict[team_name]["monthly_alert_threshold"]
		if invoice["total"] > monthly_limit:
			email_sent = send_budget_alert_email(team_dict[team_name], invoice)
			if email_sent:
				invoices_to_update.append(invoice["name"])

	if invoices_to_update:
		Invoice = frappe.qb.DocType("Invoice")
		(
			frappe.qb.update(Invoice)
			.set(Invoice.budget_alert_sent, 1)
			.where(Invoice.name.isin(invoices_to_update))
		).run()


def send_budget_alert_email(team_info, invoice):
	"""
	Args:
		team_info (dict)
		invoice (dict): Invoice that exceeded the budget alert threshold
	"""
	try:
		team_user = team_info["user"]
		currency = "₹" if team_info["currency"] == "INR" else "$"

		invoice_amount = f"{currency}{invoice['total']}"
		alert_threshold = f"{currency}{team_info['monthly_alert_threshold']}"
		excess_amount = f"{currency}{round(invoice['total'] - team_info['monthly_alert_threshold'], 2)}"

		subject = f"Frappe Cloud Budget Alert for {team_user}"

		frappe.sendmail(
			recipients=team_user,
			subject=subject,
			template="budget_alert",
			args={
				"team_user": team_user,
				"invoice_amount": invoice_amount,
				"alert_threshold": alert_threshold,
				"excess_amount": excess_amount,
				"period_start": invoice["period_start"],
				"period_end": invoice["period_end"],
			},
			reference_doctype="Invoice",
			reference_name=invoice["name"],
		)
		return True
	except Exception as e:
		frappe.log_error(f"Failed to send budget alert email: {team_info['user']}", {e})
		return False


def get_country_dialing_code(country_name: str) -> str | None:
	"""Get the dialing code for a given country name using phonenumbers library."""
	from phonenumbers import country_code_for_region

	# Get the ISO 3166 ALPHA-2 code from Country doctype
	country_code = frappe.db.get_value("Country", country_name, "code")
	if not country_code:
		return None

	# phonenumbers expects uppercase country code
	dialing_code = country_code_for_region(country_code.upper())
	return str(dialing_code) if dialing_code else None
