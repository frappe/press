# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import unittest
from datetime import date, timedelta

from press.press.doctype.cloud_usage_anomaly.detectors import (
	change_percent,
	detect_level_shift,
	detect_spike,
	median,
	median_absolute_deviation,
)

START = date(2026, 6, 1)


def series(values, start=START):
	return [{"date": start + timedelta(days=index), "value": value} for index, value in enumerate(values)]


class TestStatistics(unittest.TestCase):
	def test_median_of_odd_and_even_length(self):
		self.assertEqual(median([3, 1, 2]), 2)
		self.assertEqual(median([4, 1, 2, 3]), 2.5)
		self.assertEqual(median([]), 0)

	def test_median_absolute_deviation_ignores_a_single_outlier(self):
		values = [10, 10, 10, 10, 90]
		self.assertEqual(median_absolute_deviation(values, median(values)), 0)

	def test_change_percent_handles_a_zero_baseline(self):
		self.assertEqual(change_percent(0, 5), 100)
		self.assertEqual(change_percent(0, 0), 0)
		self.assertEqual(change_percent(100, 150), 50)


class TestSpikeDetector(unittest.TestCase):
	def test_flat_series_is_not_a_spike(self):
		self.assertIsNone(detect_spike(series([100] * 14), 3))

	def test_loud_last_day_is_a_spike(self):
		found = detect_spike(series([100, 105, 95, 100, 102, 98, 101, 340]), 3)
		self.assertIsNotNone(found)
		self.assertEqual(found["changed_on"], START + timedelta(days=7))
		self.assertGreater(found["change_percent"], 200)

	def test_a_drop_is_not_reported(self):
		self.assertIsNone(detect_spike(series([100, 105, 95, 100, 102, 98, 101, 10]), 3))

	def test_weekly_shape_does_not_fire_every_week(self):
		"""Backups run heavier on one day. Four weeks of that shape, then the same day
		again, is the series behaving exactly as it always has."""
		weeks = [100, 100, 100, 100, 100, 100, 400] * 4
		self.assertIsNone(detect_spike(series(weeks, start=date(2026, 6, 1)), 3))

	def test_flat_series_needs_a_relative_jump(self):
		"""With no deviation to measure against, a small rise must not read as infinite."""
		self.assertIsNone(detect_spike(series([100] * 10 + [105]), 3))
		self.assertIsNotNone(detect_spike(series([100] * 10 + [140]), 3))

	def test_too_short_a_series_is_not_judged(self):
		self.assertIsNone(detect_spike(series([100, 400]), 3))


class TestLevelShiftDetector(unittest.TestCase):
	def test_flat_series_has_no_shift(self):
		self.assertIsNone(detect_level_shift(series([100] * 20), 20))

	def test_step_is_found_on_the_day_it_happened(self):
		found = detect_level_shift(series([100] * 10 + [160] * 10), 20)
		self.assertIsNotNone(found)
		self.assertEqual(found["changed_on"], START + timedelta(days=10))
		self.assertAlmostEqual(found["baseline"], 100)
		self.assertAlmostEqual(found["current"], 160)
		self.assertAlmostEqual(found["change_percent"], 60)

	def test_creeping_growth_is_caught(self):
		"""One percent a day is how a bill ends up a third higher than last month
		without any single day ever looking wrong."""
		creep = series([100 * (1.01**day) for day in range(40)])
		found = detect_level_shift(creep, 20)
		self.assertIsNotNone(found)
		self.assertGreater(found["change_percent"], 20)

	def test_spike_answers_today_where_a_shift_answers_the_day_it_started(self):
		"""Both detectors fire on a series that stepped up three weeks ago and stayed
		there. Only one of them names the day it started, which is the question being
		asked."""
		stepped = series([100] * 20 + [160] * 5)

		spike = detect_spike(stepped, 3)
		shift = detect_level_shift(stepped, 20)

		self.assertEqual(spike["changed_on"], START + timedelta(days=24))
		self.assertEqual(shift["changed_on"], START + timedelta(days=20))

	def test_spike_stops_firing_once_the_new_level_is_the_norm(self):
		"""Weeks after a step, the same weekday's history is the new level too, so the
		spike detector falls quiet and only the level shift keeps reporting it."""
		settled = series([100] * 10 + [160] * 20)
		self.assertIsNone(detect_spike(settled, 3))
		self.assertEqual(detect_level_shift(settled, 20)["changed_on"], START + timedelta(days=10))

	def test_a_single_loud_day_is_not_a_new_level(self):
		found = detect_level_shift(series([100] * 10 + [900] + [100] * 10), 20)
		self.assertIsNone(found)

	def test_a_drop_is_not_reported(self):
		self.assertIsNone(detect_level_shift(series([160] * 10 + [100] * 10), 20))

	def test_small_step_below_the_threshold_is_ignored(self):
		self.assertIsNone(detect_level_shift(series([100] * 10 + [105] * 10), 20))
