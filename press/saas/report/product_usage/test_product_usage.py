# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, today

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.team.test_team import create_test_team
from press.saas.doctype.product_trial.test_product_trial import create_test_product_trial
from press.saas.report.product_usage.product_usage import execute


class TestProductUsage(FrappeTestCase):
	def setUp(self):
		app = create_test_app(make_autoname("product_app_.#####"), "Product App")
		product = create_test_product_trial(app)
		self.app_name = str(app.name)
		self.product_name = str(product.name)
		self.trial_plan = str(product.get("trial_plan"))
		self.bench = create_test_bench(group=ReleaseGroup("Release Group", product.get("release_group")))

	def tearDown(self):
		frappe.db.rollback()

	def create_site(self, plan: str | None, **kwargs):
		return create_test_site(bench=self.bench.name, apps=["frappe", self.app_name], plan=plan, **kwargs)

	def get_rows(self, **filters) -> dict[str, dict]:
		filters = {"from_date": add_days(today(), -1), "to_date": today(), "product_apps_only": 1, **filters}
		_, rows, *_ = execute(filters)
		return {row["app"]: row for row in rows}

	def get_row(self, app: str | None) -> dict:
		return self.get_rows()[str(app)]

	def test_active_installs_split_by_plan_and_skip_standby_and_archived_sites(self):
		self.create_site(create_test_plan("Site", price_usd=10).name)
		self.create_site(self.trial_plan)
		self.create_site(create_test_plan("Site", price_usd=0).name)
		self.create_site(self.trial_plan, is_standby=1)
		self.create_site(self.trial_plan).db_set("status", "Archived")

		row = self.get_row(self.app_name)

		counts = {field: row[field] for field in ("active_installs", "paid_installs", "trial_installs")}
		self.assertEqual(counts, {"active_installs": 3, "paid_installs": 1, "trial_installs": 1})
		self.assertEqual((row["free_installs"], row["new_installs"]), (1, 4))

	def test_new_installs_count_only_apps_installed_in_the_date_range(self):
		self.create_site(self.trial_plan)
		old_site = self.create_site(self.trial_plan)
		frappe.db.set_value(
			"Site App",
			{"parent": old_site.name},
			"creation",
			add_days(now_datetime(), -10),
			update_modified=False,
		)

		row = self.get_row(self.app_name)

		self.assertEqual((row["active_installs"], row["new_installs"]), (2, 1))

	def test_signups_count_requests_sites_created_and_completed_setup_wizards(self):
		team = create_test_team().name
		site = self.create_site(self.trial_plan, setup_wizard_complete=1)
		for status, site_name in (("Site Created", site.name), ("Error", None)):
			request = frappe.get_doc(
				{"doctype": "Product Trial Request", "team": team, "product_trial": self.product_name}
			).insert(ignore_permissions=True)
			frappe.db.set_value("Product Trial Request", request.name, {"status": status, "site": site_name})

		row = self.get_row(self.app_name)

		counts = {field: row[field] for field in ("signups", "sites_created", "setup_complete")}
		self.assertEqual(counts, {"signups": 2, "sites_created": 1, "setup_complete": 1})

	def test_product_apps_only_hides_apps_that_no_product_trial_has(self):
		other_app = create_test_app(make_autoname("other_app_.#####"), "Other App")
		group = create_test_release_group([create_test_app(), other_app])
		create_test_site(bench=create_test_bench(group=group).name, apps=["frappe", other_app.name])

		self.assertNotIn(other_app.name, self.get_rows())
		self.assertEqual(self.get_rows(product_apps_only=0)[str(other_app.name)]["active_installs"], 1)

	def test_chart_shows_weekly_new_installs_of_the_top_apps(self):
		self.create_site(self.trial_plan)

		*_, chart, _ = execute(
			{"from_date": add_days(today(), -1), "to_date": today(), "product_apps_only": 1}
		)

		dataset = next(data for data in chart["data"]["datasets"] if data["name"] == self.app_name)
		self.assertEqual(sum(dataset["values"]), 1)
