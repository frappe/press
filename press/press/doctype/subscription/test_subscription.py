# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from unittest.mock import patch


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
			period=30,
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

		with patch.object(frappe.utils, "today", return_value=today):
			subscription.create_usage_record()
			# this should not create duplicate record
			subscription.create_usage_record()

		# time travel to tomorrow
		with patch.object(frappe.utils, "today", return_value=tomorrow):
			subscription.create_usage_record()

		invoice = frappe.get_doc("Invoice", {"team": email, "status": "Draft"})
		self.assertEqual(invoice.total, 2)

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
			period=30,
		).insert()

		subscription = frappe.get_doc(
			doctype="Subscription",
			team=team.name,
			document_type="ToDo",
			document_name=todo.name,
			plan=plan.name,
		).insert()

		def method(self):
			return False

		# subscription calls this method when checking if it should create a usage record
		todo.can_charge_for_subscription = method

		# shouldn't create a usage record
		usage_record = subscription.create_usage_record()
		self.assertTrue(usage_record is None)

	def tearDown(self):
		frappe.db.rollback()
