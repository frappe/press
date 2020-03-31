# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime
import json
from press.utils import get_formated_date
from press.press.doctype.stripe_webhook_log.stripe_webhook_log import set_status
from frappe.utils import getdate

class Subscription(Document):
	def validate(self):
		if self.status == "Active" and self.is_new():
			for subscription in frappe.get_all("Subscription",
					{
						"status": "Active",
						"team": self.team,
						"name": ["!=", self.name]
					}
				):

				frappe.db.set_value("Subscription", subscription.name, 'status', 'Completed')

class SubscriptionController(object):
	def __init__(self, email_id, team):
		self.email_id = email_id
		self.payer_name = None
		self.team = team
		self.transaction_currency = 'USD'
		self.subscription_item_id = None

		self.subscription_details = {}

	def setup(self):
		self.set_team()
		self.set_subscription_item_id()

	def set_team(self):
		if not self.team:
			self.team = frappe.db.get_value('Team Member', {'user': self.email_id}, 'parent')
			self.payer_name = frappe.db.get_value('User', self.email_id, 'full_name')

	def set_transaction_currency(self):
		if self.team:
			self.transaction_currency = frappe.db.get_value("Team", self.team, 'transaction_currency')

	def get_subscription_item(self):
		account_plan = frappe.db.get_value("Plan", {'is_default': 1, 'for_account': 1})
		account_plan_doc = frappe.get_cached_doc("Plan", account_plan)
		plan_id = account_plan_doc.get_plan_id(currency=self.transaction_currency)

		return [
			{
				"plan": plan_id,
			}
		]

	def set_subscription_item_id(self):
		self.subscription_item_id = frappe.db.get_value("Subscription",
			{
				'team': self.team,
				'status': "Active",
			},
			'subscription_item_id'
		)

	def setup_press_subscription_record(self):
		from press.utils import get_formated_date

		current_period_end = get_formated_date(self.subscription_details['current_period_end'])
		current_period_start = get_formated_date(self.subscription_details['current_period_start'])

		subscription_doc = frappe.get_doc({
			"doctype": "Subscription",
			"team": self.team,
			"subscription_id": self.subscription_details['id'],
			"subscription_item_id": self.subscription_details['items']['data'][0]['id'], # charge usage against this id
			"status": "Active",
			"start_date": current_period_start,
			"current_period_start": current_period_start,
			"end_date": current_period_end,
			"current_period_end": current_period_end
		})

		subscription_doc.save(ignore_permissions=True)

def handle_subscription_logs():
	for log in frappe.get_all("Stripe Webhook Log", {
			'event_type': 'customer.subscription.updated',
			'status': 'Queued'
		}, ["data", "name"]):

		set_status(log.name, 'In Progress')

		webhook_data = json.loads(log.data)
		subscription_data = webhook_data['data']['object']

		subscription_doc_name = frappe.db.get_value("Subscription",
			{"subscription_id": subscription_data['id']})

		subscription_doc = frappe.get_cached_doc("Subscription", subscription_doc_name)

		subscription_doc.update({
			"current_period_end": get_formated_date(subscription_data['current_period_end']),
			"current_period_start": get_formated_date(subscription_data['current_period_start'])
		})

		subscription_doc.save()

		set_status(log.name, 'Complete')
