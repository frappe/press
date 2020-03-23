# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import stripe
from datetime import datetime
from frappe.utils import get_datetime
from press.press.doctype.subscription.subscription import SubscriptionController

class StripeController(SubscriptionController):
	def __init__(self, payer_name=None, email_id=None, token=None):
		self.token = token
		self.customer_obj = None
		self.stripe_obj = stripe
		super(StripeController, self).__init__(payer_name=payer_name, email_id=email_id)
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
		customer_id = frappe.db.get_value("Team", self.team, 'profile_id')
		if customer_id:
			self.customer_obj = self.stripe_obj.Customer.retrieve(customer_id)

	def create_customer(self):
		if not self.customer_obj:
			self.customer_obj = self.stripe_obj.Customer.create(
				source=self.token,
				email=self.email_id,
				name=self.payer_name
			)

			# temporarily using username to maintain customer id
			frappe.db.set_value('Team', self.team, 'profile_id', self.customer_obj.id)

	def create_subscription(self):
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
