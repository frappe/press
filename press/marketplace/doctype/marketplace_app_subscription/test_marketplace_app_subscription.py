# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import frappe
import unittest
from unittest.mock import patch

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)
from press.marketplace.doctype.marketplace_app_plan.test_marketplace_app_plan import (
	create_test_marketplace_app_plan,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_team


def create_test_marketplace_app_subscription():
	app = create_test_app()
	create_test_marketplace_app(app.name)
	plan = create_test_marketplace_app_plan()
	team = create_test_team()
	site = create_test_site(team=team.name)
	subscription = frappe.get_doc(
		{
			"doctype": "Marketplace App Subscription",
			"app": app.name,
			"marketplace_app_plan": plan.name,
			"site": site.name,
			"team": site.team,
		}
	).insert(ignore_if_duplicate=True)
	return subscription


class TestMarketplaceAppSubscription(unittest.TestCase):
	def setUp(self) -> None:
		self.marketplace_subscription = create_test_marketplace_app_subscription()
		self.subscription = frappe.get_doc(
			"Subscription",
			{

				"marketplace_app_subscription": self.marketplace_subscription.name,
				"document_type": "Marketplace App",
				"site": self.marketplace_subscription.site,
				"document_name": self.marketplace_subscription.name,
				"enabled": 1,
			},
		)
		self.plan = frappe.get_doc("Plan", self.subscription.plan)

	def tearDown(self) -> None:
		frappe.db.rollback()

	def test_subscription_creation(self):
		"""
		Check if subscription doc is created and linked after_insert of Marketplace App Subscription
		"""
		self.assertEqual(self.subscription.document_name, self.marketplace_subscription.name)

	def test_subscription_daily(self):
		"""
		Check if usage records are created for chargable document
		Check if only one subscription is created and invoice total is correct
		"""

		today = frappe.utils.getdate()
		tomorrow = frappe.utils.add_days(today, 1)
		desired_value = self.plan.get_price_per_day("INR") * 2

		is_last_day_of_month = frappe.utils.data.get_last_day(today) == today
		yesterday = frappe.utils.add_days(today, -1)

		# Consider yesterday's and today's record instead of today and tomorrow
		# Became flaky if it was last day of month because
		# tomorrow went outside of this month's invoice's period
		if is_last_day_of_month:
			tomorrow = today
			today = yesterday

		with patch.object(frappe.utils, "today", return_value=today):
			self.subscription.create_usage_record()
			self.assertTrue(
				frappe.db.exists("Usage Record", {"subscription": self.subscription.name})
			)
			# this should not create duplicate record
			self.subscription.create_usage_record()

		# time travel to tomorrow
		with patch.object(frappe.utils, "today", return_value=tomorrow):
			self.subscription.create_usage_record()

		invoice = frappe.get_doc(
			"Invoice", {"team": self.subscription.team, "status": "Draft"}
		)
		self.assertEqual(invoice.total, desired_value)

	def test_subscription_for_non_chargable_document(self):
		def method():
			return False

		# subscription calls this method when checking if it should create a usage record
		self.subscription.can_charge_for_subscription = method

		with patch.object(
			self.subscription,
			"get_subscribed_document",
			return_value=self.marketplace_subscription,
		):
			# shouldn't create a usage record
			usage_record = self.subscription.create_usage_record()
			self.assertTrue(usage_record is None)

	def test_subscription_on_trial_plan(self):
		self.plan.price_usd = 0
		self.plan.price_inr = 0
		self.plan.save()

		today = frappe.utils.getdate()
		tomorrow = frappe.utils.add_days(today, 1)

		with patch.object(frappe.utils, "today", return_value=today):
			# shouldn't create a usage record as site is in trial
			self.subscription.create_usage_record()

		# time travel to tomorrow
		with patch.object(frappe.utils, "today", return_value=tomorrow):
			# shouldn't create a usage record as site is in trial
			self.subscription.create_usage_record()

		invoice = frappe.get_doc(
			"Invoice", {"team": self.marketplace_subscription.team, "status": "Draft"}
		)
		self.assertEqual(invoice.total, 0)
