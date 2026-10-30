# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


def create_test_enterprise_plan(**overrides):
	return frappe.get_doc(
		{
			"doctype": "Enterprise Warranty Plan",
			"__newname": frappe.mock("name"),
			"title": "Enterprise",
			"price_inr": 2400000,
			"price_usd": 25000,
			"max_price_lock_years": 3,
			"coverage": "Bug fixes\nSecurity fixes",
			**overrides,
		}
	).insert()


class TestEnterpriseWarrantyPlan(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_dashboard_view_is_priced_in_the_team_currency(self):
		plan = create_test_enterprise_plan()

		self.assertEqual(plan.as_dashboard("USD")["yearly_price"], 25000)
		self.assertEqual(plan.as_dashboard("INR")["yearly_price"], 2400000)
		self.assertEqual(plan.as_dashboard("INR")["coverage"], ["Bug fixes", "Security fixes"])
		self.assertEqual(plan.as_dashboard("INR")["price_lock_years"], [1, 2, 3])

	def test_plan_without_a_price_lock_period_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "at least 1 year"):
			create_test_enterprise_plan(max_price_lock_years=0)
