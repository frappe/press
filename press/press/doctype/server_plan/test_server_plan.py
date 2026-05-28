# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import typing

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

if typing.TYPE_CHECKING:
	from press.press.doctype.server_plan.server_plan import ServerPlan


def create_test_server_plan(server_type: str = "Server") -> "ServerPlan":
	"""Create test Server Plan doc."""
	server_plan = frappe.get_doc(
		{
			"doctype": "Server Plan",
			"name": make_autoname("SP-.####"),
			"server_type": server_type,
			"title": frappe.mock("name"),
			"price_inr": 1000,
			"price_usd": 200,
			"enabled": 1,
			"disk": 25,
		}
	).insert()
	server_plan.reload()
	return server_plan


class TestServerPlan(FrappeTestCase):
	"""Tests for ServerPlan price helpers and validation."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.plan = create_test_server_plan()

	def tearDown(self):
		frappe.db.rollback()

	# ── price helpers ────────────────────────────────────────────────────────

	def test_price_per_day_usd_calculated_correctly(self):
		"""price_usd / period (days in month) should equal price_per_day in USD."""
		expected = round(self.plan.price_usd / self.plan.period, 2)
		self.assertAlmostEqual(self.plan.get_price_per_day("USD"), expected, places=2)

	def test_price_per_day_inr_calculated_correctly(self):
		"""price_inr / period should equal price_per_day in INR."""
		expected = round(self.plan.price_inr / self.plan.period, 2)
		self.assertAlmostEqual(self.plan.get_price_per_day("INR"), expected, places=2)

	def test_daily_price_usd_matches_price_per_day(self):
		"""get_price_for_interval('Daily', 'USD') == get_price_per_day('USD')."""
		self.assertAlmostEqual(
			self.plan.get_price_for_interval("Daily", "USD"),
			self.plan.get_price_per_day("USD"),
			places=2,
		)

	def test_monthly_price_is_30x_daily(self):
		"""Monthly price should be price_per_day * 30 (rounded)."""
		expected = round(self.plan.get_price_per_day("USD") * 30, 2)
		result = self.plan.get_price_for_interval("Monthly", "USD")
		self.assertAlmostEqual(result, expected, places=2)

	def test_unknown_interval_returns_none(self):
		"""An unrecognised interval returns None (not an exception)."""
		result = self.plan.get_price_for_interval("Quarterly", "USD")
		self.assertIsNone(result)

	# ── validate_active_subscriptions ────────────────────────────────────────

	def test_disabling_plan_with_no_active_subscriptions_allowed(self):
		"""Disabling a plan that has zero active subscriptions must succeed."""
		from unittest.mock import patch

		with patch(
			"press.press.doctype.server_plan.server_plan.frappe.db.count",
			return_value=0,
		):
			# Simulate transitioning from enabled=1 to enabled=0
			self.plan.enabled = 0
			old = frappe.get_doc("Server Plan", self.plan.name)
			old.enabled = 1
			with patch.object(self.plan, "get_doc_before_save", return_value=old):
				self.plan.validate_active_subscriptions()  # must not raise

	def test_disabling_plan_with_active_subscriptions_raises(self):
		"""Disabling a plan that still has active subscriptions raises ValidationError."""
		from unittest.mock import patch

		with patch(
			"press.press.doctype.server_plan.server_plan.frappe.db.count",
			return_value=3,
		):
			self.plan.enabled = 0
			old = frappe.get_doc("Server Plan", self.plan.name)
			old.enabled = 1
			with (
				patch.object(self.plan, "get_doc_before_save", return_value=old),
				self.assertRaises(frappe.ValidationError),
			):
				self.plan.validate_active_subscriptions()

	def test_disabling_legacy_plan_allowed_regardless_of_subscriptions(self):
		"""Legacy plans are exempt from the active-subscription guard."""
		from unittest.mock import patch

		with patch(
			"press.press.doctype.server_plan.server_plan.frappe.db.count",
			return_value=99,
		):
			self.plan.enabled = 0
			self.plan.legacy_plan = 1
			old = frappe.get_doc("Server Plan", self.plan.name)
			old.enabled = 1
			with patch.object(self.plan, "get_doc_before_save", return_value=old):
				self.plan.validate_active_subscriptions()  # must not raise
