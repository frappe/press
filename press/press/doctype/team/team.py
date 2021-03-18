# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.model.document import Document
from frappe.utils import get_fullname
from press.utils.billing import (
	get_erpnext_com_connection,
	get_frappe_io_connection,
	get_stripe,
)
from press.exceptions import FrappeioServerNotSet


class Team(Document):
	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		# validate duplicate team members
		team_members = [row.user for row in self.team_members]
		duplicate_members = [m for m in team_members if team_members.count(m) > 1]
		duplicate_members = list(set(duplicate_members))
		if duplicate_members:
			frappe.throw(
				_("Duplicate Team Members: {0}").format(", ".join(duplicate_members)),
				frappe.DuplicateEntryError,
			)

		if not self.currency and self.country:
			self.currency = "INR" if self.country == "India" else "USD"

		# set default user
		if not self.user and self.team_members:
			self.user = self.team_members[0].user

		# set billing name
		if not self.billing_name:
			self.billing_name = frappe.utils.get_fullname(self.name)

		self.validate_onboarding()

	def validate_onboarding(self):
		if self.is_new():
			self.initialize_onboarding_steps()
			return

		for step in self.onboarding:
			if self.free_account:
				step.status = "Skipped"

	def initialize_onboarding_steps(self):
		self.set(
			"onboarding",
			[
				{"step_name": "Create Team", "status": "Completed"},
				{"step_name": "Add Billing Information", "status": "Pending"},
				{"step_name": "Transfer Credits", "status": "Not Applicable"},
				{"step_name": "Create Site", "status": "Pending"},
			],
		)

	def update_onboarding(self, step_name, status):
		def get_step(step_name):
			for step in self.onboarding:
				if step.step_name == step_name:
					return step

		step = get_step(step_name)
		step.status = status
		if (
			step_name == "Add Billing Information"
			and status == "Completed"
			and self.erpnext_partner
		):
			get_step("Transfer Credits").status = "Skipped"

		if (
			step_name == "Add Billing Information"
			and status == "Skipped"
			and not self.erpnext_partner
		):
			frappe.throw("Cannot skip this step")

		self.save()

	def on_update(self):
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

		if not self.is_new() and self.billing_name:
			self.load_doc_before_save()
			if self.has_value_changed("billing_name"):
				self.update_billing_details_on_frappeio()

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

	def enable_erpnext_partner_privileges(self):
		self.erpnext_partner = 1
		self.update_onboarding("Transfer Credits", "Pending")

	def allocate_free_credits(self):
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

	def create_user_for_member(
		self, first_name=None, last_name=None, email=None, password=None, role=None
	):
		user = frappe.db.get_value("User", email, ["name"], as_dict=True)
		if not user:
			user = frappe.new_doc("User")
			user.first_name = first_name
			user.last_name = last_name
			user.email = email
			user.owner = email
			user.new_password = password
			user.append_roles(role)
			user.flags.no_welcome_mail = True
			user.save(ignore_permissions=True)

		self.append("team_members", {"user": user.name})

		self.save(ignore_permissions=True)

	def has_member(self, user):
		users = [row.user for row in self.team_members]
		return user in users

	def is_defaulter(self):
		if self.free_account:
			return

		last_invoice = frappe.get_last_doc(
			"Invoice", filters={"docstatus": 1, "team": self.name}
		)
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
			filters={"team": self.name, "status": ("!=", "Draft"), "docstatus": 1},
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

		return allow

		# if self.free_account:
		# 	return allow

		# if self.is_partner_and_has_enough_credits():
		# 	return allow
		# else:
		# 	why = "Cannot create site due to insufficient credits"

		# if self.default_payment_method:
		# 	return allow
		# else:
		# 	why = "Cannot create site without adding a card"

		# return (False, why)

	def get_onboarding(self):
		valid_steps = [step for step in self.onboarding if step.status != "Not Applicable"]
		return {
			"steps": self.onboarding,
			"complete": all(step.status in ["Completed", "Skipped"] for step in valid_steps),
		}

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


def update_site_onboarding(site, method):
	if site.team:
		team = frappe.get_doc("Team", site.team)
		if not team.get_onboarding()["complete"]:
			team.update_onboarding("Create Site", "Completed")


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
