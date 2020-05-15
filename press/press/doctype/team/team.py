# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from press.api.billing import get_stripe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_fullname


class Team(Document):
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

	def create_stripe_customer_and_subscription(self):
		self.create_stripe_customer()
		self.create_subscription()

		# allocate free credits on signup
		credits_field = "free_credits_inr" if self.currency == "INR" else "free_credits_usd"
		credit_amount = frappe.db.get_single_value("Press Settings", credits_field)
		self.allocate_credit_amount(credit_amount, remark="Free credits on signup")

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

	def create_stripe_customer(self):
		if not self.stripe_customer_id:
			stripe = get_stripe()
			customer = stripe.Customer.create(email=self.user, name=get_fullname(self.user))
			self.db_set("stripe_customer_id", customer.id)

	def create_payment_method(self, payment_method, set_default=False):
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

	def get_payment_methods(self):
		payment_methods = frappe.db.get_all(
			"Stripe Payment Method",
			{"team": self.name},
			["name", "last_4", "name_on_card", "expiry_month", "expiry_year", "is_default"],
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

	def get_upcoming_invoice(self):
		stripe = get_stripe()
		return stripe.Invoice.upcoming(customer=self.stripe_customer_id)

	def create_subscription(self):
		if not self.has_subscription():
			frappe.get_doc(
				{"doctype": "Subscription", "team": self.name, "status": "Active"}
			).insert()

	def has_subscription(self):
		return bool(frappe.db.exists("Subscription", {"team": self.name}))

	def get_past_payments(self):
		payments = frappe.db.get_all(
			"Payment",
			filters={"team": self.name, "docstatus": 1, "amount": (">", 0)},
			fields=[
				"amount",
				"payment_date",
				"status",
				"currency",
				"payment_link",
				"creation",
				"stripe_invoice_id",
			],
			order_by="creation desc",
		)
		for payment in payments:
			payment.formatted_amount = frappe.utils.fmt_money(
				payment.amount, 2, payment.currency
			)
			payment.payment_date = frappe.utils.global_date_format(payment.payment_date)
		return payments

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
		res = frappe.db.get_all(
			"Payment Ledger Entry",
			{"team": self.name, "docstatus": 1},
			["sum(amount) as total"],
		)
		amount = res[0].total or 0
		if amount > 0:
			return amount
		return 0

	def get_onboarding(self):
		team_created = True
		card_added = bool(self.default_payment_method)
		site_created = frappe.db.count("Site", {"team": self.name}) > 0
		return {
			"Create a Team": team_created,
			"Add Billing Information": card_added,
			"Create your first site": site_created,
			"complete": team_created and card_added and site_created,
		}

	def suspend_sites(self, reason=None):
		active_sites = map(
			lambda d: d.name, frappe.db.get_all("Site", {"team": self.name, "status": "Active"}),
		)
		for site in active_sites:
			frappe.get_doc("Site", site).suspend(reason)
		return active_sites

	def unsuspend_sites(self, reason=None):
		suspended_sites = map(
			lambda d: d.name,
			frappe.db.get_all("Site", {"team": self.name, "status": "Suspended"}),
		)
		for site in suspended_sites:
			frappe.get_doc("Site", site).unsuspend(reason)
		return suspended_sites


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
	if doc.event_type not in ["payment_method.attached"]:
		return

	event = frappe.parse_json(doc.payload)
	payment_method = event["data"]["object"]
	customer_id = payment_method["customer"]
	team_doc = frappe.get_doc("Team", {"stripe_customer_id": customer_id})
	team_doc.create_payment_method(payment_method, set_default=True)


def suspend_sites_for_teams_without_cards():
	"""
	If a team has not added their card and they have exhausted their credits, their sites will be set to Suspended.
	Runs daily.
	"""

	# find out teams which don't have a card and have exhausted their credit limit
	res = frappe.db.sql(
		"""
		SELECT
			SUM(ple.amount) as total_credits, ple.team
		FROM `tabPayment Ledger Entry` ple
		LEFT JOIN
			`tabTeam` t
		ON
			t.name = ple.team
		WHERE
			ple.docstatus = 1
			AND ifnull(t.default_payment_method, '') = ''
			AND t.free_account = 0
		GROUP BY
			ple.team
		HAVING
			total_credits < 0
	""",
		as_dict=True,
	)

	teams_without_cards_and_exhausted_credit_limit = [r.team for r in res]
	for team in teams_without_cards_and_exhausted_credit_limit:
		team_doc = frappe.get_doc("Team", team)
		sites = team_doc.suspend_sites(reason="Card not added")

		# send email
		if sites:
			email = team_doc.user
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
