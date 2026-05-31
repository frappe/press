# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

if TYPE_CHECKING:
	from press.press.doctype.static_ip_plan.static_ip_plan import StaticIPPlan


def create_test_static_ip_plan(
	provider: str = "AWS EC2",
	price_usd: float = 10.0,
	price_inr: float = 850.0,
	enabled: int = 1,
) -> StaticIPPlan:
	"""Create a test Static IP Plan doc."""
	plan = frappe.get_doc(
		{
			"doctype": "Static IP Plan",
			"name": make_autoname("SIP-.####"),
			"title": f"Test Static IP Plan {frappe.mock('name')}",
			"provider": provider,
			"price_usd": price_usd,
			"price_inr": price_inr,
			"enabled": enabled,
		}
	).insert(ignore_if_duplicate=True)
	plan.reload()
	return plan


class TestStaticIPPlan(FrappeTestCase):
	def setUp(self):
		self.plan = create_test_static_ip_plan(price_usd=10.0, price_inr=850.0)

	def tearDown(self):
		frappe.db.rollback()

	# ── get_price_for_interval ──────────────────────────────────────────────
	# StaticIPPlan only supports the "Daily" interval; everything else raises.

	def test_daily_usd_returns_base_price(self):
		"""Daily USD price equals the raw price_usd value."""
		price = self.plan.get_price_for_interval("Daily", "USD")
		self.assertAlmostEqual(price, 10.0, places=2)

	def test_daily_inr_returns_base_price(self):
		"""Daily INR price equals the raw price_inr value."""
		price = self.plan.get_price_for_interval("Daily", "INR")
		self.assertAlmostEqual(price, 850.0, places=2)

	def test_hourly_interval_raises_validation_error(self):
		"""'Hourly' is not a valid interval for StaticIPPlan."""
		with self.assertRaises(frappe.ValidationError):
			self.plan.get_price_for_interval("Hourly", "USD")

	def test_monthly_interval_raises_validation_error(self):
		"""Any interval other than 'Daily' raises a ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			self.plan.get_price_for_interval("Monthly", "USD")

	def test_weekly_interval_raises_validation_error(self):
		"""'Weekly' is not a valid interval."""
		with self.assertRaises(frappe.ValidationError):
			self.plan.get_price_for_interval("Weekly", "INR")
