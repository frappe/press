# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import typing
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

if typing.TYPE_CHECKING:
	from press.press.doctype.app.app import App

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.team.test_team import create_test_team
from press.saas.doctype.product_trial.product_trial import ProductTrial


def create_test_product_trial(
	app: "App",
):
	frappe_app = create_test_app()
	trial_plan = create_test_plan("Site", is_trial_plan=True)
	domain = create_test_root_domain("local.fc.frappe.dev")
	release_group = create_test_release_group([frappe_app, app])
	product_trial = frappe.get_doc(
		{
			"doctype": "Product Trial",
			"name": app.name,
			"title": app.title,
			"apps": [
				{
					"app": "frappe",
				},
				{
					"app": app.name,
				},
			],
			"trial_plan": trial_plan.name,
			"domain": domain.name,
			"release_group": release_group.name,
			"email_subject": "Test Subject",
			"email_header_content": "Test Header",
		}
	).insert(ignore_if_duplicate=True)
	product_trial.reload()
	return product_trial


class TestProductTrial(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _create_standby_site(self, product, bench):
		return create_test_site(
			bench=bench.name,
			standby_for_product=product.name,
			is_standby=1,
		)

	def _two_benches_on_same_server(self, product):
		"""An old and a new Active bench for the product's group on one server."""
		group = frappe.get_doc("Release Group", product.release_group)
		old_bench = create_test_bench(
			group=group,
			creation=frappe.utils.add_to_date(None, days=-2),
		)
		new_bench = create_test_bench(
			group=group,
			server=old_bench.server,
			creation=frappe.utils.now_datetime(),
		)
		return old_bench, new_bench

	def test_get_latest_benches_returns_newest_active_bench_per_server(self):
		product = create_test_product_trial(create_test_app("test_latest_bench", "Test Latest Bench"))
		old_bench, new_bench = self._two_benches_on_same_server(product)

		latest_benches = product.get_latest_benches()

		self.assertIn(new_bench.name, latest_benches)
		self.assertNotIn(old_bench.name, latest_benches)

	def test_standby_site_on_older_bench_is_not_handed_out(self):
		product = create_test_product_trial(create_test_app("test_stale_standby", "Test Stale Standby"))
		old_bench, new_bench = self._two_benches_on_same_server(product)

		stale_site = self._create_standby_site(product, old_bench)
		fresh_site = self._create_standby_site(product, new_bench)

		chosen = product.get_standby_site()

		self.assertEqual(chosen, fresh_site.name)
		self.assertNotEqual(chosen, stale_site.name)

	def test_no_standby_site_handed_out_when_only_stale_sites_exist(self):
		product = create_test_product_trial(create_test_app("test_only_stale", "Test Only Stale"))
		old_bench, _new_bench = self._two_benches_on_same_server(product)

		self._create_standby_site(product, old_bench)

		self.assertIsNone(product.get_standby_site())

	@patch("press.saas.doctype.product_trial.product_trial.frappe.db.commit", new=Mock())
	@patch("press.saas.doctype.product_trial.product_trial.frappe.db.rollback", new=Mock())
	def test_failed_standby_handover_returns_site_to_pool_and_undoes_the_customer_team(self):
		# Rollback is mocked, so the customer's team stays written as if it had been committed
		product = create_test_product_trial(create_test_app("test_failed_handover", "Test Failed Handover"))
		bench = create_test_bench(group=frappe.get_doc("Release Group", product.release_group))
		standby_site = self._create_standby_site(product, bench)
		pool_team, pool_signup_time = standby_site.team, standby_site.signup_time
		customer = create_test_team()

		with (
			patch.object(ProductTrial, "set_site_domain", side_effect=Exception("Domain setup failed")),
			self.assertRaisesRegex(Exception, "Domain setup failed"),
		):
			product.setup_trial_site("failed-handover", product.domain, team=customer.name)

		standby_site.reload()
		self.assertEqual(standby_site.is_standby, 1)
		self.assertEqual(standby_site.team, pool_team)
		self.assertEqual(standby_site.signup_time, pool_signup_time)
