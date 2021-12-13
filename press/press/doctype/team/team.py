# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe import _
from typing import List
from hashlib import blake2b
from press.utils import log_error
from frappe.utils import get_fullname
from frappe.utils import get_url_to_form
from press.telegram_utils import Telegram
from frappe.model.document import Document
from press.exceptions import FrappeioServerNotSet
from frappe.contacts.address_and_contact import load_address_and_contact
from press.press.doctype.account_request.account_request import AccountRequest
from press.utils.billing import (
	get_erpnext_com_connection,
	get_frappe_io_connection,
	get_stripe,
)


class Team(Document):
	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		self.validate_duplicate_members()
		self.set_team_currency()
		self.set_default_user()
		self.set_billing_name()

	def before_insert(self):
		if not self.notify_email:
			self.notify_email = self.name

		if not self.referrer_id:
			self.set_referrer_id()

	def set_referrer_id(self):
		h = blake2b(digest_size=4)
		h.update(self.name.encode())
		self.referrer_id = h.hexdigest()

	def delete(self, force=False, workflow=False):
		if force:
			return super().delete()

		if workflow:
			return frappe.get_doc(
				{"doctype": "Team Deletion Request", "team": self.name}
			).insert()

		frappe.throw(
			f"You are only deleting the Team Document for {self.name}. To continue to"
			" do so, pass force=True with this call. Else, pass workflow=True to raise"
			" a Team Deletion Request to trigger complete team deletion process."
		)

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
	def create_new(
		cls,
		account_request: AccountRequest,
		first_name: str,
		last_name: str,
		password: str = None,
		country: str = None,
		via_erpnext: bool = False,
	):
		"""Create new team along with user (user created first)."""
		team = frappe.get_doc(
			{
				"doctype": "Team",
				"name": account_request.team,
				"user": account_request.email,
				"country": country,
				"enabled": 1,
				"via_erpnext": via_erpnext,
			}
		)
		user = team.create_user(
			first_name, last_name, account_request.email, password, account_request.role
		)
		team.insert(ignore_permissions=True, ignore_links=True)
		team.append("team_members", {"user": user.name})
		team.save(ignore_permissions=True)

		team.create_stripe_customer()

		if account_request.referrer_id:
			team.create_referral_bonus(account_request.referrer_id)

		if not team.via_erpnext:
			team.create_upcoming_invoice()
			if team.has_partner_account_on_erpnext_com():
				team.enable_erpnext_partner_privileges()

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
		self, first_name=None, last_name=None, email=None, password=None, role=None
	):
		user = frappe.db.get_value("User", email, ["name"], as_dict=True)
		if not user:
			user = self.create_user(first_name, last_name, email, password, role)

		self.append("team_members", {"user": user.name})
		self.save(ignore_permissions=True)

	def set_billing_name(self):
		if not self.billing_name:
			self.billing_name = frappe.utils.get_fullname(self.name)

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

	def validate_payment_mode(self):
		if self.has_value_changed("payment_mode"):
			if self.payment_mode == "Card":
				if frappe.db.count("Stripe Payment Method", {"team": self.name}) == 0:
					frappe.throw("No card added")
			if self.payment_mode == "Prepaid Credits":
				if self.get_balance() <= 0:
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

	def on_update(self):
		self.validate_payment_mode()

		if not self.is_new() and self.billing_name:
			self.load_doc_before_save()
			if self.has_value_changed("billing_name"):
				self.update_billing_details_on_frappeio()

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
		self.save(ignore_permissions=True)

	def allocate_free_credits(self):
		if self.via_erpnext:
			# dont allocate free credits for signups via erpnext
			# since they get a 14 day free trial site
			return

		if not self.free_credits_allocated:
			# allocate free credits on signup
			credits_field = "free_credits_inr" if self.currency == "INR" else "free_credits_usd"
			credit_amount = frappe.db.get_single_value("Press Settings", credits_field)
			if not credit_amount:
				return
			self.allocate_credit_amount(credit_amount, source="Free Credits")
			self.free_credits_allocated = 1
			self.save()
			self.reload()

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
			last_invoice = frappe.get_last_doc(
				"Invoice", filters={"docstatus": 0, "team": self.name}
			)
		except frappe.DoesNotExistError:
			return False

		return last_invoice.status == "Unpaid"

	def create_stripe_customer(self):
		if not self.stripe_customer_id:
			stripe = get_stripe()
			customer = stripe.Customer.create(email=self.user, name=get_fullname(self.user))
			self.stripe_customer_id = customer.id
			self.save()

	def update_billing_details(self, billing_details):
		if self.billing_address:
			address_doc = frappe.get_doc("Address", self.billing_address)
		else:
			address_doc = frappe.new_doc("Address")
			address_doc.address_title = self.name
			address_doc.append(
				"links",
				{"link_doctype": self.doctype, "link_name": self.name, "link_title": self.name},
			)

		address_doc.update(
			{
				"address_line1": billing_details.address,
				"city": billing_details.city,
				"state": billing_details.state,
				"pincode": billing_details.postal_code,
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
		draft_invoices = frappe.get_all(
			"Invoice", {"team": self.name, "docstatus": 0}, pluck="name"
		)
		for draft_invoice in draft_invoices:
			# Invoice.customer_name set by Invoice.validate()
			frappe.get_doc("Invoice", draft_invoice).save()

	def update_billing_details_on_frappeio(self):
		try:
			frappeio_client = get_frappe_io_connection()
		except FrappeioServerNotSet as e:
			if frappe.conf.developer_mode:
				return
			else:
				raise e

		previous_version = self.get_doc_before_save()

		if not previous_version:
			self.load_doc_before_save()
			previous_version = self.get_doc_before_save()

		previous_billing_name = previous_version.billing_name

		if previous_billing_name:
			if frappeio_client.rename_doc("Customer", previous_billing_name, self.billing_name):
				frappe.msgprint(
					f"Renamed customer from {previous_billing_name} to {self.billing_name}"
				)

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

	def create_payment_method(self, payment_method_id, set_default=False):
		stripe = get_stripe()
		payment_method = stripe.PaymentMethod.retrieve(payment_method_id)

		doc = frappe.get_doc(
			{
				"doctype": "Stripe Payment Method",
				"stripe_payment_method_id": payment_method["id"],
				"last_4": payment_method["card"]["last4"],
				"name_on_card": payment_method["billing_details"]["name"],
				"expiry_month": payment_method["card"]["exp_month"],
				"expiry_year": payment_method["card"]["exp_year"],
				"team": self.name,
			}
		)
		doc.insert()

		# unsuspend sites on payment method added
		self.unsuspend_sites(reason="Payment method added")
		if set_default:
			doc.set_default()
			self.reload()

		# allocate credits if not already allocated
		self.allocate_free_credits()

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
		return invoices

	def allocate_credit_amount(self, amount, source, remark=None):
		doc = frappe.get_doc(
			doctype="Balance Transaction",
			team=self.name,
			type="Adjustment",
			source=source,
			amount=amount,
			description=remark,
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
		return doc

	def get_available_credits(self):
		def get_stripe_balance():
			return self.get_stripe_balance()

		return frappe.cache().hget(
			"customer_available_credits", self.name, generator=get_stripe_balance
		)

	def get_stripe_balance(self):
		stripe = get_stripe()
		customer_object = stripe.Customer.retrieve(self.stripe_customer_id)
		balance = (customer_object["balance"] * -1) / 100
		return balance

	@frappe.whitelist()
	def get_balance(self):
		res = frappe.db.get_all(
			"Balance Transaction",
			filters={"team": self.name, "docstatus": 1},
			order_by="creation desc",
			limit=1,
			pluck="ending_balance",
		)
		if not res:
			return 0
		return res[0]

	@frappe.whitelist()
	def get_available_partner_credits(self):
		if not self.erpnext_partner:
			frappe.throw(f"{self.name} is not a partner account.")

		client = get_frappe_io_connection()
		response = client.session.post(
			f"{client.url}/api/method/partner_relationship_management.api.get_partner_credit_balance",
			data={"email": self.name},
		)

		if response.ok:
			res = response.json()
			message = res.get("message")

			if message.get("credit_balance"):
				return message.get("credit_balance")
			else:
				error_message = message.get("error_message")
				log_error("Partner Credit Fetch Error", team=self.name, error_message=error_message)
				frappe.throw(error_message)

		else:
			log_error(
				"Problem fetching partner credit balance from frappe.io",
				team=self.name,
				response=response.text,
			)
			frappe.throw("Problem fetching partner credit balance.")

	def is_partner_and_has_enough_credits(self):
		return self.erpnext_partner and self.get_balance() > 0

	def has_partner_account_on_erpnext_com(self):
		if frappe.conf.developer_mode:
			return False
		erpnext_com = get_erpnext_com_connection()
		res = erpnext_com.get_value(
			"ERPNext Partner", "name", filters={"email": self.name, "status": "Approved"}
		)
		return res["name"] if res else None

	def can_create_site(self):
		why = ""
		allow = (True, "")

		if self.free_account:
			return allow

		if self.payment_mode == "Prepaid Credits":
			if self.get_balance() > 0:
				return allow
			else:
				why = "Cannot create site due to insufficient balance"

		if self.payment_mode == "Card":
			if self.default_payment_method:
				return allow
			else:
				why = "Cannot create site without adding a card"

		return (False, why)

	def get_onboarding(self):
		billing_setup = bool(
			self.payment_mode in ["Card", "Prepaid Credits"]
			and (self.default_payment_method or self.get_balance() > 0)
			and self.billing_address
		)
		site_created = frappe.db.count("Site", {"team": self.name}) > 0

		if self.via_erpnext:
			erpnext_domain = frappe.db.get_single_value("Press Settings", "erpnext_domain")
			erpnext_site = frappe.db.get_value(
				"Site",
				{"domain": erpnext_domain, "team": self.name, "status": ("!=", "Archived")},
				["name", "plan"],
				as_dict=1,
			)
			erpnext_site_plan_set = erpnext_site and erpnext_site.plan != "ERPNext Trial"
		else:
			erpnext_site = None
			erpnext_site_plan_set = True

		return {
			"account_created": True,
			"billing_setup": billing_setup,
			"erpnext_site": erpnext_site,
			"erpnext_site_plan_set": erpnext_site_plan_set,
			"site_created": site_created,
			"complete": billing_setup and site_created and erpnext_site_plan_set,
		}

	@frappe.whitelist()
	def suspend_sites(self, reason=None):
		sites_to_suspend = self.get_sites_to_suspend()
		for site in sites_to_suspend:
			frappe.get_doc("Site", site).suspend(reason)
		return sites_to_suspend

	def get_sites_to_suspend(self):
		return frappe.db.get_all(
			"Site",
			{"team": self.name, "status": ("in", ("Active", "Inactive")), "free": 0},
			pluck="name",
		)

	@frappe.whitelist()
	def unsuspend_sites(self, reason=None):
		suspended_sites = [
			d.name for d in frappe.db.get_all("Site", {"team": self.name, "status": "Suspended"})
		]
		for site in suspended_sites:
			frappe.get_doc("Site", site).unsuspend(reason)
		return suspended_sites

	def get_upcoming_invoice(self):
		# get the current period's invoice
		today = frappe.utils.datetime.datetime.today()
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
			return frappe.get_doc("Invoice", result[0])

	def create_upcoming_invoice(self):
		today = frappe.utils.today()
		return frappe.get_doc(doctype="Invoice", team=self.name, period_start=today).insert()

	def notify_with_email(self, recipients: List[str], **kwargs):
		if not self.send_notifications:
			return
		if not recipients:
			recipients = [self.notify_email]

		frappe.sendmail(
			recipients=recipients, **kwargs,
		)

	@frappe.whitelist()
	def send_telegram_alert_for_failed_payment(self, invoice):
		telegram = Telegram()
		team_url = get_url_to_form("Team", self.name)
		invoice_url = get_url_to_form("Invoice", invoice)
		telegram.send(
			f"Failed Invoice Payment [{invoice}]({invoice_url}) of"
			f" Partner: [{self.name}]({team_url})"
		)

	@frappe.whitelist()
	def send_email_for_failed_payment(self, invoice, sites=None):
		invoice = frappe.get_doc("Invoice", invoice)
		email = self.user
		payment_method = self.default_payment_method
		last_4 = frappe.db.get_value("Stripe Payment Method", payment_method, "last_4")
		account_update_link = frappe.utils.get_url("/dashboard/welcome")
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
				select u.name, u.first_name, u.last_name, GROUP_CONCAT(r.`role`) as roles
				from `tabUser` u
				left join `tabHas Role` r
				on (r.parent = u.name)
				where ifnull(u.name, '') in %s
				group by u.name
			""",
			[member_emails],
			as_dict=True,
		)
		for user in users:
			user.roles = (user.roles or "").split(",")

	return users


def get_default_team(user):
	if frappe.db.exists("Team", user):
		return user


def process_stripe_webhook(doc, method):
	"""This method runs after a Stripe Webhook Log is created"""
	from datetime import datetime

	if doc.event_type not in ["payment_intent.succeeded"]:
		return

	event = frappe.parse_json(doc.payload)
	payment_intent = event["data"]["object"]
	if payment_intent.get("invoice"):
		# ignore payment for invoice
		return

	team = frappe.get_doc("Team", {"stripe_customer_id": payment_intent["customer"]})
	amount = payment_intent["amount"] / 100
	balance_transaction = team.allocate_credit_amount(
		amount, source="Prepaid Credits", remark=payment_intent["id"]
	)
	invoice = frappe.get_doc(
		doctype="Invoice",
		team=team.name,
		type="Prepaid Credits",
		status="Paid",
		due_date=datetime.fromtimestamp(payment_intent["created"]),
		amount_paid=amount,
		amount_due=amount,
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
	# there should only be one charge object
	charge = payment_intent["charges"]["data"][0]["id"]
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

	team = get_current_team()
	if doc.name == team:
		return True

	return False


def validate_site_creation(doc, method):
	if frappe.session.user == "Administrator":
		return
	if not doc.team:
		return

	# validate site creation for team
	team = frappe.get_doc("Team", doc.team)
	[allow_creation, why] = team.can_create_site()
	if not allow_creation:
		frappe.throw(why)
