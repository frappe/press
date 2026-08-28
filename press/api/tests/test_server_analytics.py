# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from __future__ import annotations

import inspect
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.analytics import (
	NICE_STEPS,
	PROMETHEUS_SCRAPE_INTERVAL,
	auto_timespan_timegrain,
	get_rate_interval,
	get_rounded_boundary,
)


class TestAutoTimespanTimegrain(FrappeTestCase):
	def test_one_hour_range_picks_a_sub_two_minute_timegrain(self):
		start = datetime(2024, 1, 1, 13, 0, 0)
		end = start + timedelta(hours=1)

		timespan, timegrain = auto_timespan_timegrain(start, end)

		self.assertEqual(timespan, 3600)
		# ~60 points over an hour lands on a 90s step, which is what regressed the
		# charts: 90s is smaller than 2x the 60s scrape interval.
		self.assertEqual(timegrain, 90)

	def test_timegrain_is_always_a_nice_step(self):
		start = datetime(2024, 1, 1, 0, 0, 0)
		for hours in (1, 6, 24, 24 * 7, 24 * 15):
			_, timegrain = auto_timespan_timegrain(start, start + timedelta(hours=hours))
			self.assertIn(timegrain, NICE_STEPS, f"timegrain {timegrain} for {hours}h is not a nice step")

	def test_zero_length_range_returns_zero_timegrain(self):
		start = datetime(2024, 1, 1, 0, 0, 0)
		self.assertEqual(auto_timespan_timegrain(start, start), (0, 0))

	def test_end_before_start_raises(self):
		start = datetime(2024, 1, 1, 1, 0, 0)
		with self.assertRaises(ValueError):
			auto_timespan_timegrain(start, start - timedelta(hours=1))


class TestRateInterval(FrappeTestCase):
	def test_rate_window_always_spans_at_least_two_scrapes(self):
		# A rate() window narrower than 2x the scrape interval can see a single
		# sample on some steps and return nothing, which the charts draw as a
		# spike down to zero. Guard every timegrain the auto picker can produce.
		for timegrain in NICE_STEPS:
			rate_interval = get_rate_interval(timegrain)
			self.assertGreaterEqual(
				rate_interval,
				2 * PROMETHEUS_SCRAPE_INTERVAL,
				f"rate window {rate_interval}s for timegrain {timegrain}s is too small",
			)

	def test_one_hour_timegrain_gets_a_widened_rate_window(self):
		# The regression: 1h -> 90s step. The step stays 90s (resolution) but the
		# rate window must widen so the CPU chart stops spiking to zero.
		self.assertEqual(get_rate_interval(90), 4 * PROMETHEUS_SCRAPE_INTERVAL)

	def test_large_timegrain_keeps_overlapping_window(self):
		# For coarse ranges the window grows with the step (Grafana's $__rate_interval).
		self.assertEqual(get_rate_interval(1800), 1800 + PROMETHEUS_SCRAPE_INTERVAL)

	def test_zero_timegrain_falls_back_to_a_safe_window(self):
		self.assertEqual(get_rate_interval(0), 4 * PROMETHEUS_SCRAPE_INTERVAL)


class TestServerAnalyticsQuery(FrappeTestCase):
	"""The CPU/network/iops/db charts must not query Prometheus with a rate window
	that is narrower than the scrape interval, regardless of the chosen range."""

	def _capture_query(self, start: datetime, end: datetime, chart: str) -> str:
		from press.api import server

		captured = {}

		def fake_prometheus_query(query, function, *args, **kwargs):
			captured["query"] = query
			return {"datasets": [], "labels": []}

		# strip the whitelist/protected/redis_cache layers to call the real function
		analytics = inspect.unwrap(server.analytics)
		with (
			patch.object(server, "prometheus_query", side_effect=fake_prometheus_query),
			patch.object(server, "get_mount_point", return_value="/"),
		):
			analytics(
				"fs1.frappe.cloud",
				chart,
				"Asia/Kolkata",
				start.isoformat(),
				end.isoformat(),
			)
		return captured["query"]

	def test_cpu_query_uses_widened_rate_window_for_one_hour(self):
		start = datetime(2024, 1, 1, 13, 0, 0)
		end = start + timedelta(hours=1)

		query = self._capture_query(start, end, "cpu")

		# 1h -> 90s step, widened to a 240s rate window.
		self.assertIn("[240s]", query)
		self.assertNotIn("[90s]", query)

	def test_rate_charts_never_use_a_sub_scrape_window(self):
		start = datetime(2024, 1, 1, 0, 0, 0)
		for chart in ("cpu", "network", "iops", "database_commands_count"):
			query = self._capture_query(start, start + timedelta(minutes=10), chart)
			window = int(query.split("[")[1].split("s]")[0])
			self.assertGreaterEqual(
				window,
				2 * PROMETHEUS_SCRAPE_INTERVAL,
				f"{chart} chart queried a {window}s window",
			)


class TestPrometheusQueryAlignment(FrappeTestCase):
	def setUp(self):
		self.timegrain = 120
		self.start = datetime(2024, 1, 1, 12, 0, 0)
		self.end = self.start + timedelta(minutes=10)

	def _labels(self):
		rounded_start = get_rounded_boundary(self.start, self.timegrain)
		rounded_end = get_rounded_boundary(self.end, self.timegrain)
		delta = timedelta(seconds=self.timegrain)
		count = (rounded_end - rounded_start) // delta + 1
		return [(rounded_start + i * delta).timestamp() for i in range(count)]

	def _run_prometheus_query(self, series_values):
		from press.api import server

		response = {"data": {"result": [{"metric": {"mode": "user"}, "values": series_values}]}}
		http_response = MagicMock()
		http_response.json.return_value = response

		with (
			patch.object(frappe.db, "get_single_value", return_value="monitor.frappe.cloud"),
			patch("press.api.server.get_decrypted_password", return_value="secret"),
			patch("press.api.server.requests") as requests_mock,
		):
			requests_mock.get.return_value = http_response
			return server.prometheus_query(
				"some_query",
				lambda metric: metric["mode"],
				"Asia/Kolkata",
				0,
				self.timegrain,
				use_timestamps=True,
				start=self.start,
				end=self.end,
			)

	def test_full_series_has_no_gaps(self):
		labels = self._labels()
		result = self._run_prometheus_query([[label, "42"] for label in labels])

		values = result["datasets"][0]["values"]
		self.assertEqual(len(values), len(labels))
		self.assertTrue(all(value == 42 for value in values))

	def test_missing_steps_become_none_not_zero(self):
		# This is the shape that produced the spiky chart: a step Prometheus did
		# not return a value for stays None (later rendered as a 0 spike). The
		# rate-window fix is what stops Prometheus from omitting these steps.
		labels = self._labels()
		present = [[label, "42"] for i, label in enumerate(labels) if i % 2 == 0]
		result = self._run_prometheus_query(present)

		values = result["datasets"][0]["values"]
		self.assertEqual(values[0], 42)
		self.assertIsNone(values[1])
		self.assertNotIn(0, values)
