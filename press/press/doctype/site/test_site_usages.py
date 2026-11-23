# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site.site_usages import (
	daily_compute_notice_message_id,
	get_changed_disk_usages,
	get_daily_compute_hours,
	notify_sites_nearing_daily_compute_limit,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.site_usage.test_site_usage import create_test_site_usage
from press.press.doctype.subscription.test_subscription import create_test_subscription
from press.press.doctype.team.test_team import create_test_team


class TestChangedDiskUsages(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.plan = create_test_plan("Site", max_database_usage=1000, max_storage_usage=1000)
		self.bench = None

	def tearDown(self):
		frappe.db.rollback()

	def create_site_at_ten_percent(self) -> str:
		site = create_test_site(bench=self.bench)
		self.bench = site.bench
		create_test_subscription(site.name, self.plan.name, site.team)
		site.db_set({"current_database_usage": 10, "current_disk_usage": 10})
		return site.name

	def changed_usages_of(self, *sites: str) -> list[dict]:
		return sorted(
			(usage for usage in get_changed_disk_usages() if usage["site"] in sites),
			key=lambda usage: usage["site"],
		)

	def test_changed_disk_usages_returns_site_and_integer_percentages_of_the_subscription_plan(self):
		site = self.create_site_at_ten_percent()
		create_test_site_usage(site, database=250, public=200, private=300)

		usages = self.changed_usages_of(site)

		self.assertEqual(usages, [{"site": site, "latest_database_usage": 25, "latest_disk_usage": 50}])
		self.assertIsInstance(usages[0]["latest_database_usage"], int)
		self.assertIsInstance(usages[0]["latest_disk_usage"], int)

	def test_changed_disk_usages_counts_only_the_newest_reading_of_each_site(self):
		unchanged_newest = self.create_site_at_ten_percent()
		create_test_site_usage(unchanged_newest, database=500, public=250, private=250, hours_ago=2)
		create_test_site_usage(unchanged_newest, database=100, public=50, private=50)
		changed_newest = self.create_site_at_ten_percent()
		create_test_site_usage(changed_newest, database=100, public=50, private=50, hours_ago=2)
		create_test_site_usage(changed_newest, database=300, public=200, private=200)

		usages = self.changed_usages_of(unchanged_newest, changed_newest)

		self.assertEqual(
			usages, [{"site": changed_newest, "latest_database_usage": 30, "latest_disk_usage": 40}]
		)

	def test_changed_disk_usages_ignores_readings_older_than_twelve_hours(self):
		site = self.create_site_at_ten_percent()
		create_test_site_usage(site, database=900, public=450, private=450, hours_ago=13)

		self.assertEqual(self.changed_usages_of(site), [])

	def test_changed_disk_usages_excludes_archived_sites(self):
		site = self.create_site_at_ten_percent()
		create_test_site_usage(site, database=900, public=450, private=450)
		frappe.db.set_value("Site", site, "status", "Archived")

		self.assertEqual(self.changed_usages_of(site), [])

	def test_changed_disk_usages_excludes_sites_whose_subscription_is_not_for_a_site(self):
		site = self.create_site_at_ten_percent()
		create_test_site_usage(site, database=900, public=450, private=450)
		frappe.db.set_value("Subscription", {"document_name": site}, "document_type", "Release Group")

		self.assertEqual(self.changed_usages_of(site), [])

	def test_changed_disk_usages_skips_sites_that_moved_one_percentage_point_or_less(self):
		moved_up_by_one = self.create_site_at_ten_percent()
		create_test_site_usage(moved_up_by_one, database=110, public=50, private=60)
		moved_down_by_one = self.create_site_at_ten_percent()
		create_test_site_usage(moved_down_by_one, database=90, public=50, private=50)

		self.assertEqual(self.changed_usages_of(moved_up_by_one, moved_down_by_one), [])

	def test_changed_disk_usages_returns_sites_that_moved_more_than_one_percentage_point_in_database_or_disk(
		self,
	):
		database_up = self.create_site_at_ten_percent()
		create_test_site_usage(database_up, database=120, public=50, private=50)
		disk_down = self.create_site_at_ten_percent()
		create_test_site_usage(disk_down, database=100, public=40, private=40)

		usages = self.changed_usages_of(database_up, disk_down)

		self.assertEqual(
			usages,
			sorted(
				[
					{"site": database_up, "latest_database_usage": 12, "latest_disk_usage": 10},
					{"site": disk_down, "latest_database_usage": 10, "latest_disk_usage": 8},
				],
				key=lambda usage: usage["site"],
			),
		)


@patch(
	"press.press.doctype.site.site_usages.get_communication_info",
	new=Mock(return_value=["owner@example.com"]),
)
class TestNotifySitesNearingDailyComputeLimit(FrappeTestCase):
	def setUp(self):
		super().setUp()
		get_daily_compute_hours.cache_clear()
		self.plan = create_test_plan("Site", cpu_time=10)
		self.team = create_test_team()
		self.bench = None

	def tearDown(self):
		get_daily_compute_hours.cache_clear()
		frappe.db.rollback()

	def site_at(self, usage: int, plan: str | None = None, shared: bool = True, **kwargs):
		"""A site that has used `usage`% of the compute its plan allows today."""
		kwargs.setdefault("team", self.team.name)
		site = create_test_site(bench=self.bench if shared else None, public_server=shared, **kwargs)
		if shared:
			self.bench = site.bench
		site.db_set({"plan": plan or self.plan.name, "current_cpu_usage": usage})
		return site

	def notify(self, **kwargs) -> dict[str, dict]:
		with patch.object(frappe, "sendmail") as sendmail:
			notify_sites_nearing_daily_compute_limit(**kwargs)
		return {call.kwargs["reference_name"]: call.kwargs for call in sendmail.call_args_list}

	def mark_notified(self, site, threshold: int = 80, over_limit: bool = False):
		message_id = daily_compute_notice_message_id(
			frappe._dict(name=site.name, team=site.team), threshold, over_limit
		)
		return frappe.get_doc(
			{
				"doctype": "Email Queue",
				"sender": "notifications@frappe.io",
				"message": "sent",
				"status": "Sent",
				"message_id": message_id,
			}
		).insert(ignore_permissions=True)

	def test_warns_the_team_of_a_site_that_reached_the_threshold(self):
		site = self.site_at(80)

		call = self.notify()[site.name]

		self.assertEqual(call["template"], "site_nearing_daily_compute_limit")
		self.assertEqual(call["args"]["usage"], 80)
		self.assertEqual(call["args"]["compute_hours"], 10)
		self.assertFalse(call["args"]["over_limit"])
		self.assertIn("close to its daily compute limit", call["subject"])

	def test_skips_a_site_that_is_below_the_threshold(self):
		site = self.site_at(79)

		self.assertNotIn(site.name, self.notify())

	def test_warns_at_a_lower_threshold_when_one_is_given(self):
		site = self.site_at(60)

		self.assertIn(site.name, self.notify(threshold=50))

	def test_sends_an_over_limit_notice_once_the_site_uses_all_its_compute(self):
		site = self.site_at(100)

		call = self.notify()[site.name]

		self.assertTrue(call["args"]["over_limit"])
		self.assertIn("Action needed", call["subject"])
		self.assertIn("used up its daily compute limit", call["subject"])

	def test_skips_a_free_site_and_a_site_of_a_free_team(self):
		free_site = self.site_at(90, free=True)
		free_team_site = self.site_at(90, team=create_test_team(free_account=True).name)

		calls = self.notify()

		self.assertNotIn(free_site.name, calls)
		self.assertNotIn(free_team_site.name, calls)

	def test_skips_a_site_on_a_dedicated_server(self):
		"""Only a shared server rate limits a site on the daily compute limit of its plan."""
		site = self.site_at(90, shared=False)

		self.assertNotIn(site.name, self.notify())

	def test_skips_a_site_whose_plan_sets_no_daily_compute_limit(self):
		site = self.site_at(90, plan=create_test_plan("Site", cpu_time=0).name)

		self.assertNotIn(site.name, self.notify())

	def test_skips_a_site_that_is_not_active(self):
		site = self.site_at(90)
		site.db_set("status", "Suspended")

		self.assertNotIn(site.name, self.notify())

	def test_does_not_warn_the_same_site_twice_in_a_day(self):
		site = self.site_at(90)
		self.mark_notified(site)

		self.assertNotIn(site.name, self.notify())

	def test_warns_again_once_the_notice_window_has_passed(self):
		site = self.site_at(90)
		email_queue = self.mark_notified(site)
		email_queue.db_set(
			"creation", frappe.utils.add_days(frappe.utils.now_datetime(), -2), update_modified=False
		)

		self.assertIn(site.name, self.notify())

	def test_warning_does_not_suppress_the_later_over_limit_notice(self):
		site = self.site_at(100)
		self.mark_notified(site, over_limit=False)

		self.assertTrue(self.notify()[site.name]["args"]["over_limit"])

	def test_skips_a_site_without_recipients(self):
		site = self.site_at(90)

		with patch("press.press.doctype.site.site_usages.get_communication_info", return_value=[]):
			self.assertNotIn(site.name, self.notify())

	def test_template_renders_the_usage_and_the_limit_of_the_plan(self):
		site = self.site_at(85)
		args = self.notify()[site.name]["args"]

		html = frappe.get_template("templates/emails/site_nearing_daily_compute_limit.html").render(args)

		self.assertIn(site.name, html)
		self.assertIn("85%", html)
		self.assertIn("10 hours", html)
		self.assertIn("close to its daily compute limit", html)
