# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.report.build_server_stats.build_server_stats import (
	floor_to_bucket,
	get_chart,
	get_period,
	group_by_server,
	last_number,
	percentile,
	seconds_of,
)


def build(server="f1.frappe.cloud", **stamps):
	return frappe._dict({"build_server": server, "status": "Success", **stamps})


class TestBuildSpans(FrappeTestCase):
	def test_a_build_reports_the_seconds_between_its_two_stamps(self):
		builds = [
			build(
				build_start=datetime(2026, 9, 10, 10, 0, 0),
				build_end=datetime(2026, 9, 10, 10, 5, 30),
			)
		]

		self.assertEqual(seconds_of(builds, "build_start", "build_end"), [330])

	def test_a_build_that_has_not_finished_is_left_out(self):
		builds = [build(build_start=datetime(2026, 9, 10, 10, 0, 0), build_end=None)]

		self.assertEqual(seconds_of(builds, "build_start", "build_end"), [])

	def test_builds_are_grouped_under_the_server_that_ran_them(self):
		grouped = group_by_server([build(server="f1.frappe.cloud"), build(server="f2.frappe.cloud")])

		self.assertEqual(sorted(grouped), ["f1.frappe.cloud", "f2.frappe.cloud"])
		self.assertEqual(len(grouped["f1.frappe.cloud"]), 1)


class TestPercentile(FrappeTestCase):
	def test_the_median_of_five_values_is_the_middle_one(self):
		self.assertEqual(percentile([50, 10, 30, 20, 40], 0.5), 30)

	def test_the_p95_of_a_short_list_is_the_largest_value(self):
		self.assertEqual(percentile([10, 20, 30], 0.95), 30)

	def test_a_window_without_builds_reports_zero(self):
		self.assertEqual(percentile([], 0.5), 0)


class TestLastNumber(FrappeTestCase):
	def test_the_last_point_of_a_series_is_the_value(self):
		self.assertEqual(last_number([1.0, 2.0, 3.5]), 3.5)

	def test_a_series_that_ends_in_a_nan_reads_as_zero(self):
		self.assertEqual(last_number([1.0, float("nan")]), 0)

	def test_a_series_without_points_reads_as_zero(self):
		self.assertEqual(last_number([]), 0)


class TestChart(FrappeTestCase):
	def test_builds_in_the_same_bucket_share_one_bar(self):
		builds = [
			build(build_start=datetime(2026, 9, 10, 10, 0, 10)),
			build(build_start=datetime(2026, 9, 10, 10, 4, 50)),
			build(build_start=datetime(2026, 9, 10, 10, 6, 0)),
		]

		chart = get_chart(3600, builds)

		self.assertEqual(chart["title"], "Builds started per 5 minutes")
		self.assertEqual(chart["data"]["datasets"][0]["values"], [2, 1])

	def test_a_window_without_builds_gives_an_empty_chart(self):
		chart = get_chart(3600, [])

		self.assertEqual(chart["data"]["labels"], [])

	def test_a_stamp_is_floored_to_the_start_of_its_bucket(self):
		floored = floor_to_bucket(datetime(2026, 9, 10, 10, 7, 42), 300)

		self.assertEqual(floored.minute, 5)
		self.assertEqual(floored.second, 0)


class TestPeriod(FrappeTestCase):
	def test_from_and_to_set_the_period_and_the_duration_is_ignored(self):
		period = get_period(
			frappe._dict(
				from_datetime="2026-09-10 10:00:00", to_datetime="2026-09-10 12:30:00", duration="1 hour"
			)
		)

		self.assertEqual(period.start, datetime(2026, 9, 10, 10, 0, 0))
		self.assertEqual(period.end, datetime(2026, 9, 10, 12, 30, 0))
		self.assertEqual(period.seconds, 9000)

	def test_a_to_without_a_from_counts_the_duration_back_from_to(self):
		period = get_period(frappe._dict(to_datetime="2026-09-10 12:00:00", duration="3 hours"))

		self.assertEqual(period.start, datetime(2026, 9, 10, 9, 0, 0))

	def test_without_from_or_to_the_duration_ends_now(self):
		period = get_period(frappe._dict(duration="15 minutes"))

		self.assertEqual(period.seconds, 15 * 60)
		self.assertLess((datetime.now() - period.end).total_seconds(), 60)

	def test_a_from_after_the_to_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "From must be at least 5 minutes before To"):
			get_period(frappe._dict(from_datetime="2026-09-10 12:00:00", to_datetime="2026-09-10 10:00:00"))

	def test_a_period_too_short_for_two_prometheus_scrapes_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "From must be at least 5 minutes before To"):
			get_period(frappe._dict(from_datetime="2026-09-10 12:00:00", to_datetime="2026-09-10 12:00:01"))

	def test_a_period_of_exactly_five_minutes_is_accepted(self):
		period = get_period(
			frappe._dict(from_datetime="2026-09-10 12:00:00", to_datetime="2026-09-10 12:05:00")
		)

		self.assertEqual(period.seconds, 300)
