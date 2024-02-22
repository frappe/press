# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import patch

import frappe

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.subscription.subscription import sites_with_free_hosting
from press.press.doctype.team.test_team import create_test_team


def create_test_subscription(
	document_name: str,
	plan: str,
	team: str,
	document_type: str = "Site",
	plan_type: str = "Site Plan",
):

	subscription = frappe.get_doc(
		{
			"doctype": "Subscription",
			"document_type": document_type,
			"document_name": document_name,
			"team": team,
			"plan_type": plan_type,
			"plan": plan,
			"site": document_name if document_type == "Site" else None,
		}
	).insert(ignore_if_duplicate=True)
	subscription.reload()
	return subscription


class TestSubscription(unittest.TestCase):
	def setUp(self):
		self.team = create_test_team()
		self.team.allocate_credit_amount(1000, source="Prepaid Credits")
		frappe.set_user(self.team.user)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_subscription_daily(self):
		todo = frappe.get_doc(doctype="ToDo", description="Test todo").insert()
		plan = frappe.get_doc(
			doctype="Site Plan",
			name="Plan-10",
			document_type="ToDo",
			interval="Daily",
			price_usd=30,
			price_inr=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="ToDo",
			document_name=todo.name,
			plan_type="Site Plan",
			plan=plan.name,
		).insert()

		today = frappe.utils.getdate()
		tomorrow = frappe.utils.add_days(today, 1)
		desired_value = plan.get_price_per_day("INR") * 2

		is_last_day_of_month = frappe.utils.data.get_last_day(today) == today
		yesterday = frappe.utils.add_days(today, -1)

		# Consider yesterday's and today's record instead of today and tomorrow
		# Became flaky if it was last day of month because
		# tomorrow went outside of this month's invoice's period
		if is_last_day_of_month:
			tomorrow = today
			today = yesterday

		with patch.object(frappe.utils, "today", return_value=today):
			subscription.create_usage_record()
			# this should not create duplicate record
			subscription.create_usage_record()

		# time travel to tomorrow
		with patch.object(frappe.utils, "today", return_value=tomorrow):
			subscription.create_usage_record()

		invoice = frappe.get_doc("Invoice", {"team": self.team.name, "status": "Draft"})
		self.assertEqual(invoice.total, desired_value)

	def test_subscription_for_non_chargeable_document(self):
		todo = frappe.get_doc(doctype="ToDo", description="Test todo").insert()
		plan = frappe.get_doc(
			doctype="Site Plan",
			name="Plan-10",
			document_type="ToDo",
			interval="Daily",
			price_usd=30,
			price_inr=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="ToDo",
			document_name=todo.name,
			plan_type="Site Plan",
			plan=plan.name,
		).insert()

		def method(subscription):
			return False

		# subscription calls this method when checking if it should create a usage record
		todo.can_charge_for_subscription = method

		with patch.object(subscription, "get_subscribed_document", return_value=todo):
			# shouldn't create a usage record
			usage_record = subscription.create_usage_record()
			self.assertTrue(usage_record is None)

	def test_site_in_trial(self):
		self.team.create_upcoming_invoice()

		two_days_after = frappe.utils.add_days(None, 2)
		site = create_test_site()
		site.trial_end_date = two_days_after
		site.save()

		plan = frappe.get_doc(
			doctype="Site Plan",
			name="Plan-10",
			document_type="Site",
			interval="Daily",
			price_usd=30,
			price_inr=30,
			period=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=self.team.name,
			document_type="Site",
			document_name=site.name,
			plan_type="Site Plan",
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

		invoice = frappe.get_doc("Invoice", {"team": self.team.name, "status": "Draft"})
		self.assertEqual(invoice.total, 0)

	def test_sites_with_free_hosting(self):
		self.team.create_upcoming_invoice()

		site1 = create_test_site(team=self.team.name)
		site1.free = 1
		site1.save()
		create_test_site(team=self.team.name)

		# test: site marked as free
		free_sites = sites_with_free_hosting()
		self.assertEqual(len(free_sites), 1)

		self.team.free_account = True
		self.team.save()

		# test: site owned by free account
		free_sites = sites_with_free_hosting()
		self.assertEqual(len(free_sites), 2)
