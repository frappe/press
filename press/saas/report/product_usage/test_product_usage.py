# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

import frappe
from frappe.desk.query_report import run
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_datetime, now_datetime, today

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_activity.site_activity import log_site_activity
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.team.test_team import create_test_team
from press.saas.doctype.product_trial.test_product_trial import create_test_product_trial
from press.saas.report.product_usage.product_usage import execute
from press.tests.test_staff_role_scopes import create_staff_user


class TestProductUsage(FrappeTestCase):
	def setUp(self):
		app = create_test_app(make_autoname("product_app_.#####"), "Product App")
		product = create_test_product_trial(app)
		self.app_name = str(app.name)
		self.product_name = str(product.name)
		self.trial_plan = str(product.get("trial_plan"))
		self.bench = create_test_bench(group=ReleaseGroup("Release Group", product.get("release_group")))

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def create_site(self, plan: str | None = None, apps: list[str] | None = None, **kwargs):
		apps = apps or ["frappe", self.app_name]
		return create_test_site(bench=self.bench.name, apps=apps, plan=plan or self.trial_plan, **kwargs)

	def get_rows(self, from_date=None, to_date=None, **filters) -> dict[str, dict]:
		dates = {"from_date": from_date or add_days(today(), -1), "to_date": to_date or today()}
		_, rows, *_ = execute({**dates, "product_apps_only": 1, **filters})
		return {row["app"]: row for row in rows}

	def get_row(self) -> dict:
		return self.get_rows()[self.app_name]

	def test_active_installs_split_by_plan_and_skip_standby_and_archived_sites(self):
		self.create_site(create_test_plan("Site", price_usd=10).name)
		self.create_site(create_test_plan("Site", price_usd=0, price_inr=500).name)
		self.create_site()
		self.create_site(create_test_plan("Site", price_usd=0, price_inr=0).name)
		self.create_site(is_standby=1)
		self.create_site().db_set("status", "Archived")

		row = self.get_row()

		fields = ("active_installs", "paid_installs", "trial_installs", "free_installs")
		self.assertEqual([row[field] for field in fields], [4, 2, 1, 1])

	def test_new_installs_count_new_sites_claimed_standby_sites_and_apps_added_to_old_sites(self):
		self.create_site()
		self.create_site(creation=add_days(now_datetime(), -10), signup_time=now_datetime())
		self.create_site(creation=add_days(now_datetime(), -10))
		old_site_with_later_install = self.create_site(
			apps=["frappe"], creation=add_days(now_datetime(), -10)
		)
		log_site_activity(old_site_with_later_install.name, "Install App", self.app_name)

		row = self.get_row()

		self.assertEqual((row["active_installs"], row["new_installs"]), (3, 3))

	def test_signups_count_requests_sites_created_and_completed_setup_wizards(self):
		team = create_test_team().name
		site = self.create_site(setup_wizard_complete=1)
		for status, site_name in (("Site Created", site.name), ("Error", None)):
			request = frappe.get_doc(
				{"doctype": "Product Trial Request", "team": team, "product_trial": self.product_name}
			).insert(ignore_permissions=True)
			frappe.db.set_value("Product Trial Request", request.name, {"status": status, "site": site_name})

		row = self.get_row()

		counts = [row[field] for field in ("signups", "sites_created", "setup_complete")]
		self.assertEqual(counts, [2, 1, 1])

	def test_product_apps_only_hides_frappe_and_apps_that_no_product_trial_has(self):
		other_app = create_test_app(make_autoname("other_app_.#####"), "Other App")
		group = create_test_release_group([create_test_app(), other_app])
		create_test_site(bench=create_test_bench(group=group).name, apps=["frappe", str(other_app.name)])

		self.assertFalse({"frappe", other_app.name} & set(self.get_rows()))
		self.assertEqual(self.get_rows(product_apps_only=0)[str(other_app.name)]["active_installs"], 1)

	def test_chart_has_every_week_of_the_range_also_weeks_without_installs(self):
		self.create_site(creation=get_datetime("2001-01-03 10:00"))

		*_, chart, _ = execute({"from_date": "2001-01-01", "to_date": "2001-01-20", "product_apps_only": 1})

		self.assertEqual(chart["data"]["labels"], ["2001-01-01", "2001-01-08", "2001-01-15"])
		self.assertEqual(chart["data"]["datasets"], [{"name": self.app_name, "values": [1, 0, 0]}])

	def test_product_team_runs_the_report_and_gets_only_counts_per_app(self):
		self.create_site()
		frappe.set_user(create_staff_user("Press Product Team"))

		result = run("Product Usage", {"from_date": add_days(today(), -1), "to_date": today()})

		self.assertFalse(frappe.has_permission("Site", "read"))
		keys = {key for row in result["result"] for key in row}
		self.assertEqual(keys - {"app"}, {column["fieldname"] for column in result["columns"][1:]})
		self.assertTrue(all(isinstance(row[key], int) for row in result["result"] for key in keys - {"app"}))
