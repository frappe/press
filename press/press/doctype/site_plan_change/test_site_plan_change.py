# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from datetime import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan


class TestSitePlanChange(FrappeTestCase):
	def setUp(self):
		super().setUp()

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
		self.assertEqual(frappe.db.get_value("Site", self.site.name, "plan"), self.nano_plan.name)

	def test_initial_plan_change_of_claimed_standby_site_is_dated_at_signup(self):
		pooled_on = datetime(2026, 9, 20, 20, 35)
		claimed_on = datetime(2026, 9, 23, 15, 2)
		standby_site = create_test_site(
			subdomain="claimedstandbysite", creation=pooled_on, signup_time=claimed_on
		)

		standby_site._create_initial_site_plan_change(self.unlimited_plan.name)

		self.assertEqual(self.get_initial_plan_timestamp(standby_site), claimed_on)

	def test_initial_plan_change_falls_back_to_creation_for_site_without_signup_time(self):
		created_on = datetime(2026, 9, 20, 20, 35)
		site = create_test_site(subdomain="sitewithoutsignuptime", creation=created_on)

		site._create_initial_site_plan_change(self.unlimited_plan.name)

		self.assertEqual(self.get_initial_plan_timestamp(site), created_on)

	def get_initial_plan_timestamp(self, site):
		return frappe.db.get_value(
			"Site Plan Change", {"site": site.name, "type": "Initial Plan"}, "timestamp"
		)
