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

		# set default user
		if not self.user and self.team_members:
			self.user = self.team_members[0].user

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
		stripe = get_stripe()
		customer = stripe.Customer.create(email=self.user, name=get_fullname(self.user))
		self.db_set("stripe_customer_id", customer.id)

	def set_default_payment_method(self):
		payment_methods = self.get_payment_methods()
		payment_method = payment_methods[0]
		stripe = get_stripe()
		# set default payment method
		stripe.Customer.modify(
			self.stripe_customer_id,
			invoice_settings={"default_payment_method": payment_methods[0]["id"]},
		)

	def get_payment_methods(self):
		stripe = get_stripe()
		res = stripe.PaymentMethod.list(customer=self.stripe_customer_id, type="card")
		return res["data"] or []

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
			filters={"team": self.name, "amount": (">", 0)},
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
			user.roles = user.roles.split(",")

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
	team_doc.set_default_payment_method()
	team_doc.create_subscription()
