# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.site.test_site import create_test_site


class TestSitePlanChange(unittest.TestCase):
	def setUp(self):
		self.tiny_plan = create_test_plan(
			"Site",
			plan_name="Tiny Plan",
			allow_downgrading_from_other_plan=False,
			price_usd=5.0,
			price_inr=375.0,
		)
		self.nano_plan = create_test_plan(
			"Site",
			plan_name="Nano Plan",
			allow_downgrading_from_other_plan=True,
			price_usd=7.0,
			price_inr=525.0,
		)
		self.unlimited_plan = create_test_plan(
			"Site",
			plan_name="Unlimited Plan",
			allow_downgrading_from_other_plan=True,
			price_usd=10.0,
			price_inr=750.0,
		)
		self.site = create_test_site(subdomain="testsite")

	def tearDown(self):
		frappe.db.rollback()

	def test_raise_error_while_downgrading_to_plan_in_which__allow_downgrading_from_other_plan__flag_is_disabled(
		self,
	):
		# Initially Set `Unlimited Plan` to site
		self.site._create_initial_site_plan_change(self.unlimited_plan.name)
		self.site.reload()
		self.assertEqual(self.site.plan, self.unlimited_plan.name)
		# Try to downgrade to `Tiny Plan` from `Unlimited Plan`
		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			frappe.get_doc(
				{
					"doctype": "Site Plan Change",
					"site": self.site.name,
					"from_plan": self.unlimited_plan.name,
					"to_plan": self.tiny_plan.name,
				}
			).insert(ignore_permissions=True)

		self.assertTrue("you cannot downgrade" in str(context.exception))

	def test_allowed_to_downgrade_while__allow_downgrading_from_other_plan__flag_is_enabled(
		self,
	):
		# Initially Set `Unlimited Plan` to site
		self.site._create_initial_site_plan_change(self.unlimited_plan.name)
		self.site.reload()
		self.assertEqual(self.site.plan, self.unlimited_plan.name)
		# Try to downgrade to `Nano Plan` from `Unlimited Plan`
		frappe.get_doc(
			{
				"doctype": "Site Plan Change",
				"site": self.site.name,
				"from_plan": self.unlimited_plan.name,
				"to_plan": self.nano_plan.name,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(
			frappe.db.get_value("Site", self.site.name, "plan"), self.nano_plan.name
		)
