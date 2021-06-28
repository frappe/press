# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import unittest
from datetime import date
from unittest.mock import patch

import frappe


def create_test_plan(
	document_type: str,
	price_usd: float = 10.0,
	price_inr: float = 750.0,
	cpu_time: int = 1,
):
	"""Create test Plan doc."""
	name = frappe.mock("name")
	return frappe.get_doc(
		{
			"name": f"Test 10 dollar plan {name}",
			"doctype": "Plan",
			"document_type": document_type,
			"price_inr": price_inr,
			"price_usd": price_usd,
			"cpu_time_per_day": cpu_time,
		}
	).insert(ignore_if_duplicate=True)


class TestPlan(unittest.TestCase):
	def setUp(self):
		self.plan = create_test_plan("Site")

	def tearDown(self):
		self.plan.delete()

	def test_period_int(self):
		self.assertIsInstance(self.plan.period, int)

	def test_per_day_difference(self):
		per_day_usd = self.plan.get_price_per_day("USD")
		per_day_inr = self.plan.get_price_per_day("INR")
		self.assertIsInstance(per_day_inr, (int, float))
		self.assertIsInstance(per_day_usd, (int, float))
		self.assertNotEqual(per_day_inr, per_day_usd)

	def test_dynamic_period(self):
		month_with_29_days = frappe.utils.get_last_day(date(2020, 2, 3))
		month_with_30_days = frappe.utils.get_last_day(date(1997, 4, 3))

		with patch.object(frappe.utils, "get_last_day", return_value=month_with_30_days):
			self.assertEqual(self.plan.period, 30)
			per_day_for_30_usd = self.plan.get_price_per_day("USD")
			per_day_for_30_inr = self.plan.get_price_per_day("INR")

		with patch.object(frappe.utils, "get_last_day", return_value=month_with_29_days):
			self.assertEqual(self.plan.period, 29)
			per_day_for_29_usd = self.plan.get_price_per_day("USD")
			per_day_for_29_inr = self.plan.get_price_per_day("INR")

		self.assertNotEqual(per_day_for_29_usd, per_day_for_30_usd)
		self.assertNotEqual(per_day_for_29_inr, per_day_for_30_inr)
