# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import stripe
import datetime

class StripeController(object):
	def __init__(self, payer_name, email_id):
		self.payer_name = payer_name
		self.email_id = email_id
		self.customer_obj = None
		self.stripe_obj = stripe
		self.transaction_currency = 'USD'
		self.subscription_details = {}

		self.setup()

	def setup(self):
		self.set_stripe_object()
		self.set_customer_details()
		self.set_transaction_currency()

	def set_stripe_object(self):
		active_stripe_account = frappe.db.get_single_value("Press Settings", "stripe_account")
		self.stripe_settings = frappe.get_cached_doc("Stripe Setting", active_stripe_account)
		self.stripe_obj.api_key = self.stripe_settings.get_password('secret_key')

	def set_customer_details(self):
		# temporarily using username to maintain customer id

		customer_id = frappe.db.get_value("User", self.email_id, 'username')
		self.customer_obj = self.stripe_obj.Customer.retrieve(customer_id)

	def set_transaction_currency(self):
		if self.customer_obj:
			self.transaction_currency = self.customer_obj.currency

	def create_customer(self):
		if not self.customer_obj:
			self.customer_obj = self.stripe_obj.Customer.create(
				email=self.email_id,
				name=self.payer_name
			)

			# temporarily using username to maintain customer id
			frappe.db.set_value('User', self.email_id, 'username', self.customer_obj.id)

		# Pending
		# Set customer id against user profile

	def create_subscription(self):
		self.subscription_details = self.stripe_obj.Subscription.create(
			customer= self.customer_obj.id,
			items=self.get_subscription_item(),
		)
		self.setup_press_subscription_record()

	def get_subscription_item(self):
		account_plan = frappe.db.sql("Plan", {'is_default': 1, 'for_account': 1})
		account_plan_doc = frappe.get_cached_value("Plan", account_plan)
		plan_id = account_plan_doc.get_plan_id(currency=self.transaction_currency)

		return [
			{
				"plan": plan_id,
			}
		]

	def setup_press_subscription_record(self):
		current_period_end = self.subscription_details['current_period_end']
		current_period_start = self.subscription_details['current_period_start']

		subscription_doc = frappe.gew_doc({
			"doctype": "Subscription",
			"user_account": self.email_id,
			"subscription_id": self.subscription_details['id'],
			"subscription_item_id": self.subscription_details['items']['data'][0]['id'], # charge usage against this id
			"status": "Active",
			"start_date": datetime.fromtimestamp(current_period_start).strftime('%Y-%m-%d')
			"end_date": datetime.fromtimestamp(current_period_end).strftime('%Y-%m-%d')
		}).save(ignore_permissions=True)
