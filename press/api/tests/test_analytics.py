# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

from datetime import datetime, timedelta
from typing import ClassVar
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import set_encrypted_password
from pytz import timezone as pytz_timezone

from press.api.analytics import (
	AggType,
	ResourceType,
	SlowLogGroupByChart,
	align_to_quarter_hour,
	get_weekly_installs,
	plausible_analytics,
)
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_team_with_press_user,
	create_test_marketplace_app,
)

TIMEZONE = "Asia/Kolkata"


class TestAlignToQuarterHour(FrappeTestCase):
	def local(self, hour: int, minute: int) -> datetime:
		return pytz_timezone(TIMEZONE).localize(datetime(2026, 8, 24, hour, minute))

	def test_range_that_crosses_the_hour_keeps_start_before_end(self):
		"""A range like 10:50-10:55 used to align start after end, and prometheus answered with an error"""
		start, end = align_to_quarter_hour(self.local(10, 50), self.local(10, 55), TIMEZONE)
		self.assertEqual(start, self.local(10, 45))
		self.assertEqual(end, self.local(11, 0))

	def test_range_widens_to_the_marks_around_it(self):
		start, end = align_to_quarter_hour(self.local(10, 5), self.local(10, 20), TIMEZONE)
		self.assertEqual(start, self.local(10, 0))
		self.assertEqual(end, self.local(10, 30))

	def test_aligned_end_moves_to_the_next_mark(self):
		_, end = align_to_quarter_hour(self.local(10, 0), self.local(10, 15), TIMEZONE)
		self.assertEqual(end, self.local(10, 30))

	def test_every_minute_of_the_hour_gives_a_range_of_whole_quarters(self):
		for minute in range(60):
			for length in (1, 5, 15, 30, 59):
				original_start = self.local(10, 0) + timedelta(minutes=minute)
				original_end = original_start + timedelta(minutes=length)
				start, end = align_to_quarter_hour(original_start, original_end, TIMEZONE)
				self.assertLessEqual(start, original_start)
				self.assertGreaterEqual(end, original_end)
				self.assertEqual((end - start).total_seconds() % 900, 0)


class TestNormalizedSlowQueries(FrappeTestCase):
	"""Elasticsearch can group only by the raw query text, and literals split one
	query into many. Before the oversample, the top-N was a set of near duplicates,
	and the Other bucket held almost all of the data."""

	labels: ClassVar[list[datetime]] = [datetime(2026, 8, 24, 10, 0), datetime(2026, 8, 24, 10, 15)]

	def chart(self, max_no_of_paths: int = 2) -> SlowLogGroupByChart:
		chart = SlowLogGroupByChart.__new__(SlowLogGroupByChart)
		chart.normalize_slow_logs = True
		chart.agg_type = AggType.COUNT
		chart.max_no_of_paths = max_no_of_paths
		return chart

	def dataset(self, query: str, values: list) -> dict:
		return {"path": query, "values": values, "stack": "path"}

	def aggregations(self, counts: list[int]):
		"""Replace the histogram over all queries. This histogram gives the Other bucket."""
		buckets = [
			frappe._dict(key_as_string=label.isoformat(), doc_count=count)
			for label, count in zip(self.labels, counts, strict=True)
		]
		return frappe._dict(histogram_of_method=frappe._dict(buckets=buckets))

	def test_queries_that_differ_only_in_literals_merge_into_one_dataset(self):
		datasets = [
			self.dataset("SELECT name FROM tabUser WHERE name = 'a'", [1, 2]),
			self.dataset("SELECT name FROM tabUser WHERE name = 'b'", [3, 4]),
		]
		merged = self.chart().get_normalized_datasets(datasets, self.aggregations([4, 6]), self.labels)
		self.assertEqual(len(merged), 1)
		self.assertEqual(merged[0]["values"], [4, 6])

	def test_other_holds_what_the_shown_queries_do_not_cover(self):
		datasets = [
			self.dataset("SELECT name FROM tabUser WHERE name = 'a'", [1, 2]),
			self.dataset("SELECT name FROM tabNote WHERE name = 'b'", [3, 4]),
		]
		merged = self.chart().get_normalized_datasets(datasets, self.aggregations([10, 10]), self.labels)
		self.assertEqual(merged[-1]["path"], "Other")
		self.assertEqual(merged[-1]["values"], [6, 4])

	def test_other_is_dropped_when_the_shown_queries_cover_everything(self):
		datasets = [self.dataset("SELECT name FROM tabUser WHERE name = 'a'", [1, 2])]
		merged = self.chart().get_normalized_datasets(datasets, self.aggregations([1, 2]), self.labels)
		self.assertEqual(len(merged), 1)
		self.assertNotEqual(merged[0]["path"], "Other")

	def test_only_the_largest_queries_are_shown_and_the_rest_fall_into_other(self):
		datasets = [
			self.dataset("SELECT a FROM tabUser", [1, 1]),
			self.dataset("SELECT b FROM tabNote", [5, 5]),
			self.dataset("SELECT c FROM tabFile", [9, 9]),
		]
		merged = self.chart(max_no_of_paths=2).get_normalized_datasets(
			datasets, self.aggregations([15, 15]), self.labels
		)
		self.assertEqual(len(merged), 3)
		self.assertEqual(merged[-1]["path"], "Other")
		self.assertEqual(merged[-1]["values"], [1, 1])

	def test_normalization_asks_elasticsearch_for_more_queries_than_the_chart_shows(self):
		self.assertEqual(self.chart(max_no_of_paths=25).terms_size, 250)

	def test_a_denormalized_chart_asks_for_exactly_what_it_shows(self):
		chart = self.chart(max_no_of_paths=25)
		chart.normalize_slow_logs = False
		self.assertEqual(chart.terms_size, 25)


class TestServerSlowQueryGrouping(FrappeTestCase):
	"""A server chart groups by database, so a reader sees which site is slow.
	The per-query variant groups by query text, so a reader can compare the
	queries a primary and its read replica get."""

	def chart(self, group_by_query: bool) -> SlowLogGroupByChart:
		chart = SlowLogGroupByChart.__new__(SlowLogGroupByChart)
		chart.resource_type = ResourceType.SERVER
		chart.group_by_query = group_by_query
		return chart

	def test_server_chart_groups_by_database_by_default(self):
		self.assertTrue(self.chart(group_by_query=False).groups_by_site)

	def test_server_chart_groups_by_query_when_asked(self):
		self.assertFalse(self.chart(group_by_query=True).groups_by_site)

	def test_site_chart_never_groups_by_site(self):
		chart = self.chart(group_by_query=False)
		chart.resource_type = ResourceType.SITE
		self.assertFalse(chart.groups_by_site)


class TestSlowQueriesWithoutLogServer(FrappeTestCase):
	def test_chart_is_empty_when_no_log_server_is_set(self):
		"""__init__ returns before it sets the filters, and run() used to read them"""
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		frappe.db.set_single_value("Press Settings", "log_server", "")
		try:
			chart = SlowLogGroupByChart(
				False,
				"m1.example.com",
				AggType.COUNT,
				TIMEZONE,
				datetime(2026, 8, 24, 10, 0),
				datetime(2026, 8, 24, 11, 0),
				3600,
				900,
				ResourceType.SERVER,
			)
			self.assertEqual(chart.run(), {"datasets": [], "labels": []})
		finally:
			frappe.db.set_single_value("Press Settings", "log_server", log_server)


def create_install_activity(app: str):
	frappe.get_doc(
		{"doctype": "Site Activity", "site": frappe.mock("name"), "action": "Install App", "reason": app}
	).db_insert()


class TestWeeklyInstalls(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_weekly_installs_counts_the_installs_of_the_app(self):
		create_install_activity("my-app")
		create_install_activity("other-app")
		installs = get_weekly_installs("my-app")
		self.assertEqual(sum(week.value for week in installs), 1)

	def test_weekly_installs_reads_a_quote_in_the_app_name_as_text(self):
		create_install_activity("my-app")
		self.assertEqual(get_weekly_installs("x' OR 1=1#"), [])


@patch("press.api.analytics.requests.get", new=Mock(return_value=Mock(status_code=500)))
class TestPlausibleAnalyticsAccess(FrappeTestCase):
	def setUp(self):
		frappe.db.set_single_value("Press Settings", "plausible_url", "https://plausible.example.com")
		set_encrypted_password(
			"Press Settings", "Press Settings", "test-key", "plausible_api_key"
		)  # pragma: allowlist secret
		self.team = create_team_with_press_user()
		create_test_app("my-app", "My App")
		create_test_marketplace_app("my-app", self.team.name)
		frappe.set_user(self.team.user)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_plausible_analytics_returns_installs_of_own_app(self):
		self.assertEqual(plausible_analytics(name="my-app")["weekly_installs"], [])

	def test_plausible_analytics_rejects_a_list_that_includes_own_app(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Invalid name, API access not permitted"):
			plausible_analytics(name=["other-app", "my-app"])
