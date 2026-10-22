# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
import frappe.utils
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site.site_usages import get_changed_disk_usages
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.subscription.test_subscription import create_test_subscription


def create_test_site_usage(site: str, database: int, public: int, private: int, hours_ago: int = 0):
	usage = frappe.get_doc(
		{"doctype": "Site Usage", "site": site, "database": database, "public": public, "private": private}
	).insert()
	if hours_ago:
		creation = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-hours_ago)
		usage.db_set("creation", creation, update_modified=False)
	return usage


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
