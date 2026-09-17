# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.marketplace.doctype.marketplace_app_plan.marketplace_app_plan import MarketplaceAppPlan
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team


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


class TestCreateMarketplaceAppSubscription(FrappeTestCase):
	"""A custom app sharing an id with a Marketplace App must not inherit its paid plan.

	The two apps are told apart by the App Source on the site's bench, not by the
	app id: only a marketplace app registers its source on a Marketplace App Version.
	"""

	def setUp(self):
		self.version = "Version 14"
		self.team = create_test_press_admin_team()
		frappe.set_user(self.team.user)

		self.frappe_app = create_test_app()
		self.frappe_source = create_test_app_source(self.version, self.frappe_app)
		self.frappe_release = create_test_app_release(self.frappe_source)

		# One app id, two sources: one published on the marketplace, one private.
		self.app = create_test_app(frappe.mock("name"), frappe.mock("name"))
		self.marketplace_source = create_test_app_source(self.version, self.app, branch="master")
		self.custom_source = create_test_app_source(self.version, self.app, branch="develop")

		create_test_marketplace_app(
			app=self.app.name,
			team=self.team.name,
			sources=[{"version": self.version, "source": self.marketplace_source.name}],
		)
		self.plan = create_test_marketplace_app_plan(self.app.name, price_inr=1000, price_usd=12)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _create_site_with_app_source(self, source):
		release = create_test_app_release(source)
		group = create_test_release_group(
			[self.frappe_app, self.app],
			frappe_version=self.version,
			app_sources=[self.frappe_source.name, source.name],
		)
		group.db_set("team", self.team.name)
		bench = create_test_bench(
			group=group,
			apps=[
				{
					"app": self.frappe_app.name,
					"hash": self.frappe_release.hash,
					"source": self.frappe_source.name,
					"release": self.frappe_release.name,
				},
				{
					"app": self.app.name,
					"hash": release.hash,
					"source": source.name,
					"release": release.name,
				},
			],
		)
		return create_test_site(bench=bench.name, team=self.team.name)

	def _subscription_exists(self, site):
		return frappe.db.exists(
			"Subscription",
			{"site": site, "document_type": "Marketplace App", "document_name": self.app.name},
		)

	def test_custom_app_sharing_id_with_marketplace_app_is_denied_the_paid_plan(self):
		site = self._create_site_with_app_source(self.custom_source)

		self.assertRaisesRegex(
			frappe.ValidationError,
			"not a Marketplace App",
			MarketplaceAppPlan.create_marketplace_app_subscription,
			site.name,
			self.app.name,
			self.plan.name,
			self.team.name,
		)
		self.assertFalse(self._subscription_exists(site.name))

	def test_marketplace_sourced_app_gets_the_paid_plan(self):
		site = self._create_site_with_app_source(self.marketplace_source)

		MarketplaceAppPlan.create_marketplace_app_subscription(
			site.name, self.app.name, self.plan.name, self.team.name
		)

		self.assertTrue(self._subscription_exists(site.name))
