# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import patch

import frappe

from press.press.doctype.site.test_site import create_test_site


def create_test_subscription(
	document_name: str, plan: str, team: str, document_type: str = "Site"
):

	return frappe.get_doc(
		{
			"doctype": "Subscription",
			"document_type": document_type,
			"document_name": document_name,
			"team": team,
			"plan": plan,
		}
	).insert(ignore_if_duplicate=True)


class TestSubscription(unittest.TestCase):
	def test_subscription_daily(self):
		email = "testuser@example.com"
		team = frappe.get_doc(doctype="Team", name=email, country="India", enabled=1).insert()
		todo = frappe.get_doc(doctype="ToDo", description="Test todo").insert()
		plan = frappe.get_doc(
			doctype="Plan",
			name="Plan-10",
			document_type="ToDo",
			interval="Daily",
			price_usd=30,
			price_inr=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=team.name,
			document_type="ToDo",
			document_name=todo.name,
			plan=plan.name,
		).insert()

		today = frappe.utils.getdate()
		tomorrow = frappe.utils.add_days(today, 1)
		desired_value = plan.get_price_per_day("INR") * 2

		with patch.object(frappe.utils, "today", return_value=today):
			subscription.create_usage_record()
			# this should not create duplicate record
			subscription.create_usage_record()

		# time travel to tomorrow
		with patch.object(frappe.utils, "today", return_value=tomorrow):
			subscription.create_usage_record()

		invoice = frappe.get_doc("Invoice", {"team": email, "status": "Draft"})
		self.assertEqual(invoice.total, desired_value)

	def test_subscription_for_non_chargeable_document(self):
		email = "testuser@example.com"
		team = frappe.get_doc(doctype="Team", name=email, country="India", enabled=1).insert()
		todo = frappe.get_doc(doctype="ToDo", description="Test todo").insert()
		plan = frappe.get_doc(
			doctype="Plan",
			name="Plan-10",
			document_type="ToDo",
			interval="Daily",
			price_usd=30,
			price_inr=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=team.name,
			document_type="ToDo",
			document_name=todo.name,
			plan=plan.name,
		).insert()

		def method():
			return False

		# subscription calls this method when checking if it should create a usage record
		todo.can_charge_for_subscription = method

		with patch.object(subscription, "get_subscribed_document", return_value=todo):
			# shouldn't create a usage record
			usage_record = subscription.create_usage_record()
			self.assertTrue(usage_record is None)

	def test_site_in_trial(self):
		email = "testuser@example.com"
		team = frappe.get_doc(doctype="Team", name=email, country="India", enabled=1).insert()
		team.create_upcoming_invoice()

		two_days_after = frappe.utils.add_days(None, 2)
		site = create_test_site()
		site.trial_end_date = two_days_after
		site.save()

		plan = frappe.get_doc(
			doctype="Plan",
			name="Plan-10",
			document_type="Site",
			interval="Daily",
			price_usd=30,
			price_inr=30,
			period=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=team.name,
			document_type="Site",
			document_name=site.name,
			plan=plan.name,
		).insert()

		today = frappe.utils.getdate()
		tomorrow = frappe.utils.add_days(today, 1)

		with patch.object(frappe.utils, "today", return_value=today):
			# shouldn't create a usage record as site is in trial
			subscription.create_usage_record()

		# time travel to tomorrow
		with patch.object(frappe.utils, "today", return_value=tomorrow):
			# shouldn't create a usage record as site is in trial
			subscription.create_usage_record()

		invoice = frappe.get_doc("Invoice", {"team": email, "status": "Draft"})
		self.assertEqual(invoice.total, 0)

	def tearDown(self):
		frappe.db.rollback()
