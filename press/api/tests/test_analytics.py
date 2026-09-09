# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

from datetime import datetime, timedelta
from typing import ClassVar

import frappe
from frappe.tests.utils import FrappeTestCase
from pytz import timezone as pytz_timezone

from press.api.analytics import AggType, SlowLogGroupByChart, align_to_quarter_hour

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
