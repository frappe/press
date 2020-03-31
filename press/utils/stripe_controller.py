# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import stripe
import json
from datetime import datetime
from frappe.utils import get_datetime
from press.press.utils.subscription_controller import SubscriptionController

class StripeController(SubscriptionController):
	def __init__(self, email_id=None, team=None):
		self.customer_obj = None
		self.stripe_obj = stripe
		self.customer_id = None
		self.intent_client_secret = None
		self.payment_methods = {}

		super(StripeController, self).__init__(email_id=email_id, team=team)
		self.setup()

	def setup(self):
		super(StripeController, self).setup()

		self.set_stripe_object()
		self.set_stripe_customer_obj()
		self.set_transaction_currency()
		self.set_subscription_item_id()

	def set_stripe_object(self):
		active_stripe_account = frappe.db.get_single_value("Press Settings", "stripe_account")
		self.stripe_settings = frappe.get_cached_doc("Stripe Settings", active_stripe_account)
		self.stripe_obj.api_key = self.stripe_settings.get_password('secret_key')

	def set_stripe_customer_obj(self):
		self.customer_id = frappe.db.get_value("Team", self.team, 'profile_id')
		if self.customer_id:
			self.customer_obj = self.stripe_obj.Customer.retrieve(self.customer_id)

	def create_customer(self):
		if not self.customer_obj:
			self.customer_obj = self.stripe_obj.Customer.create(
				invoice_settings={
					"default_payment_method": self.payment_methods,
				},
				payment_method=self.payment_methods,
				email=self.email_id,
				name=self.payer_name
			)

			frappe.db.set_value('Team', self.team, 'profile_id', self.customer_obj.id)
			self.customer_id = self.customer_obj.id

	def create_subscription(self):
		if self.payment_methods:
			self.subscription_details = self.stripe_obj.Subscription.create(
				customer= self.customer_obj.id,
				items=self.get_subscription_item(),
				default_payment_method= self.payment_methods['data'][0]['id'],
				expand=["latest_invoice.payment_intent"]
			)

		else:
			self.subscription_details = self.stripe_obj.Subscription.create(
				customer= self.customer_obj.id,
				items=self.get_subscription_item(),
			)

		self.setup_press_subscription_record()

	def create_usage_record(self, qty):
		if self.subscription_item_id:
			d = self.stripe_obj.SubscriptionItem.create_usage_record(
				self.subscription_item_id,
				quantity=qty,
				timestamp = int(datetime.timestamp(get_datetime())),
				action='increment'
			)

	def setup_intent(self):
		intent = stripe.SetupIntent.create(
			customer=self.customer_id,
			payment_method_types=["card"],
		)

		self.intent_client_secret = intent.client_secret

	def setup_payment_method(self):
		self.payment_methods = self.stripe_obj.PaymentMethod.list(
			customer=self.customer_id,
			type="card"
		)

	def retrieve_intent(self, intent_id):
		intent = self.stripe_obj.SetupIntent.retrieve(intent_id)
		self.subscription_details.update({
			'future_intent': intent
		})

	@staticmethod
	def get_publishable_key():
		active_stripe_account = frappe.db.get_single_value("Press Settings", "stripe_account")
		return frappe.db.get_value("Stripe Settings", active_stripe_account, "publishable_key")
