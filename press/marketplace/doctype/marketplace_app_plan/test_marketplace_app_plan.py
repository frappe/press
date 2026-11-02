# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)


def create_test_marketplace_app_plan(
	app: str = "frappe",
	*,
	price_inr: float = 1000,
	price_usd: float = 12,
	title: str = "Test Plan",
	enabled: int = 1,
):
	"""Create a test marketplace_app_plan"""
	if not frappe.db.exists("Marketplace App", app):
		create_test_app(name=app)
		create_test_marketplace_app(app)

	return frappe.get_doc(
		{
			"doctype": "Marketplace App Plan",
			"title": title,
			"price_inr": price_inr,
			"price_usd": price_usd,
			"app": app,
			"features": [{"description": "Feature 1"}],
			"enabled": enabled,
		}
	).insert(ignore_permissions=True)


class TestMarketplaceAppPlan(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _new_app(self) -> str:
		app = create_test_app(name=f"mp_plan_{frappe.generate_hash(length=8).lower()}")
		create_test_marketplace_app(app.name)
		return app.name

	def test_paid_plan_sets_subscription_type_paid(self):
		app = self._new_app()
		create_test_marketplace_app_plan(app, price_inr=1000, price_usd=12)

		self.assertEqual(frappe.db.get_value("Marketplace App", app, "subscription_type"), "Paid")

	def test_free_plan_sets_subscription_type_free(self):
		app = self._new_app()
		create_test_marketplace_app_plan(app, price_inr=0, price_usd=0, title="Free Plan")

		self.assertEqual(frappe.db.get_value("Marketplace App", app, "subscription_type"), "Free")

	def test_free_and_paid_plans_set_subscription_type_freemium(self):
		app = self._new_app()
		create_test_marketplace_app_plan(app, price_inr=0, price_usd=0, title="Free Plan")
		create_test_marketplace_app_plan(app, price_inr=1000, price_usd=12, title="Paid Plan")

		self.assertEqual(frappe.db.get_value("Marketplace App", app, "subscription_type"), "Freemium")

	def test_disabling_paid_plan_reverts_to_free(self):
		app = self._new_app()
		create_test_marketplace_app_plan(app, price_inr=0, price_usd=0, title="Free Plan")
		paid = create_test_marketplace_app_plan(app, price_inr=1000, price_usd=12, title="Paid Plan")

		self.assertEqual(frappe.db.get_value("Marketplace App", app, "subscription_type"), "Freemium")

		paid.enabled = 0
		paid.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Marketplace App", app, "subscription_type"), "Free")

	def test_deleting_paid_plan_reverts_to_free(self):
		app = self._new_app()
		create_test_marketplace_app_plan(app, price_inr=0, price_usd=0, title="Free Plan")
		paid = create_test_marketplace_app_plan(app, price_inr=1000, price_usd=12, title="Paid Plan")

		self.assertEqual(frappe.db.get_value("Marketplace App", app, "subscription_type"), "Freemium")

		paid.delete(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Marketplace App", app, "subscription_type"), "Free")
