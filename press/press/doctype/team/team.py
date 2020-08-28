# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from press.api.billing import get_stripe, get_erpnext_com_connection
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_fullname, flt
from frappe.contacts.address_and_contact import load_address_and_contact
from press.press.doctype.team.team_invoice import TeamInvoice


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
		self.save()

	def allocate_free_credits(self):
		if not self.free_credits_allocated:
			# allocate free credits on signup
			credits_field = "free_credits_inr" if self.currency == "INR" else "free_credits_usd"
			credit_amount = frappe.db.get_single_value("Press Settings", credits_field)
			self.allocate_credit_amount(credit_amount, remark="Free credits on signup")
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

	def create_stripe_customer(self):
		if not self.stripe_customer_id:
			stripe = get_stripe()
			customer = stripe.Customer.create(email=self.user, name=get_fullname(self.user))
			self.stripe_customer_id = customer.id
			self.save()

	def create_or_update_address(self, address):
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
				"address_line1": address.address,
				"city": address.city,
				"state": address.state,
				"pincode": address.postal_code,
				"country": address.country,
				"gstin": address.gstin,
			}
		)
		address_doc.save()

		self.billing_address = address_doc.name
		self.save()
		self.reload()
		self.update_billing_details_on_stripe(address_doc)

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
		payment_methods = frappe.db.get_all(
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
		)
		if payment_methods:
			return payment_methods

		stripe = get_stripe()
		res = stripe.PaymentMethod.list(customer=self.stripe_customer_id, type="card")
		payment_methods = res["data"] or []
		payment_methods = [
			{
				"name": d["id"],
				"last_4": d["card"]["last4"],
				"name_on_card": d["billing_details"]["name"],
				"expiry_month": d["card"]["exp_month"],
				"expiry_year": d["card"]["exp_year"],
			}
			for d in payment_methods
		]
		return payment_methods

	def get_past_invoices(self):
		invoices = frappe.db.get_all(
			"Invoice",
			filters={"team": self.name, "status": ("!=", "Draft")},
			fields=[
				"name",
				"total",
				"amount_due",
				"status",
				"stripe_invoice_url",
				"period_start",
				"period_end",
				"payment_date",
				"currency",
			],
			order_by="period_start desc",
		)

		print_format = frappe.get_meta("Invoice").default_print_format
		for invoice in invoices:
			invoice.formatted_total = frappe.utils.fmt_money(invoice.total, 2, invoice.currency)
			if invoice.currency == "USD":
				invoice.invoice_pdf = frappe.utils.get_url(
					f"/api/method/frappe.utils.print_format.download_pdf?doctype=Invoice&name={invoice.name}&format={print_format}&no_letterhead=0"
				)
		return invoices

	def allocate_credit_amount(self, amount, remark):
		if amount > 0:
			doc = frappe.get_doc(
				{
					"doctype": "Payment Ledger Entry",
					"purpose": "Credits Allocation",
					"amount": amount,
					"team": self.name,
					"remark": remark,
				}
			)
			doc.insert(ignore_permissions=True)
			doc.submit()

	def get_available_credits(self):
		def get_stripe_balance():
			stripe = get_stripe()
			customer_object = stripe.Customer.retrieve(self.stripe_customer_id)
			balance = (customer_object["balance"] * -1) / 100
			return balance

		return frappe.cache().hget(
			"customer_available_credits", self.name, generator=get_stripe_balance
		)

	def is_partner_and_has_enough_credits(self):
		return self.erpnext_partner and self.get_available_credits() > 0

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

		if self.is_partner_and_has_enough_credits():
			return allow
		else:
			why = "Cannot create site due to insufficient credits"

		if self.default_payment_method:
			return allow
		else:
			why = "Cannot create site without subscription"

		return (False, why)

	def get_onboarding(self):
		team_created = True
		card_added = bool(self.default_payment_method)
		site_created = frappe.db.count("Site", {"team": self.name}) > 0
		complete = (
			self.free_account
			or self.erpnext_partner
			or (team_created and card_added and site_created)
		)
		return {
			"Create a Team": {"done": team_created},
			"Add Billing Information": {"done": card_added},
			"Create your first site": {"done": site_created},
			"complete": complete,
		}

	def suspend_sites(self, reason=None):
		sites_to_suspend = self.get_sites_to_suspend()
		for site in sites_to_suspend:
			frappe.get_doc("Site", site).suspend(reason)
		return sites_to_suspend

	def get_sites_to_suspend(self):
		return [
			d.name
			for d in frappe.db.get_all(
				"Site", {"team": self.name, "status": "Active", "free": 0}
			)
		]

	def unsuspend_sites(self, reason=None):
		suspended_sites = [
			d.name for d in frappe.db.get_all("Site", {"team": self.name, "status": "Suspended"})
		]
		for site in suspended_sites:
			frappe.get_doc("Site", site).unsuspend(reason)
		return suspended_sites

	def get_upcoming_invoice(self):
		# get this month's invoice
		today = frappe.utils.datetime.datetime.today()
		return TeamInvoice(self, today.month, today.year).get_draft_invoice()


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


def suspend_sites_for_teams_without_cards():
	"""
	If a team has not added their card and they have exhausted their credits, their sites will be set to Suspended.
	Runs daily.
	"""

	# find out teams which don't have a card and have exhausted their credit limit
	teams_with_total_usage = frappe.db.sql(
		"""
		SELECT
			SUM(ple.amount) as total_usage, ple.team
		FROM `tabPayment Ledger Entry` ple
		LEFT JOIN `tabTeam` t
		ON t.name = ple.team
		WHERE
			ple.docstatus = 1
			AND ple.purpose = 'Site Consumption'
			AND ifnull(t.default_payment_method, '') = ''
			AND t.free_account = 0
			AND t.erpnext_partner = 0
		GROUP BY
			ple.team
	""",
		as_dict=True,
	)

	free_credits_inr, free_credits_usd = frappe.db.get_value(
		"Press Settings", None, ["free_credits_inr", "free_credits_usd"]
	)
	# teams_without_cards_and_exhausted_credit_limit = [r.team for r in res]
	for d in teams_with_total_usage:
		total_usage = d.total_usage * -1
		team = frappe.get_doc("Team", d.team)
		total_usage_limit = flt(
			free_credits_inr if team.currency == "INR" else free_credits_usd
		)

		# if total usage has crossed the allotted free credits, suspend their sites
		if total_usage > total_usage_limit:
			sites = team.suspend_sites(reason="Card not added and free credits exhausted")

			# send email
			if sites:
				email = team.user
				account_update_link = frappe.utils.get_url("/dashboard/#/welcome")
				frappe.sendmail(
					recipients=email,
					subject="Your sites have been suspended on Frappe Cloud",
					template="payment_failed",
					args={
						"subject": "Your sites have been suspended on Frappe Cloud",
						"account_update_link": account_update_link,
						"card_not_added": True,
						"sites": sites,
					},
				)
