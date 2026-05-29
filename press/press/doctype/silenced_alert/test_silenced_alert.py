# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for silenced_alert/silenced_alert.py.

get_duration() computes a human-readable duration from from_time/to_time.
get_keyword_based_on_instance_type() maps instance types to Prometheus label keys.
Both are pure methods tested with SimpleNamespace docs — no DB needed.
"""

from __future__ import annotations

from types import SimpleNamespace

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.silenced_alert.silenced_alert import SilencedAlert

# ══════════════════════════════════════════════════════════════════════════════
# SilencedAlert.get_duration
# ══════════════════════════════════════════════════════════════════════════════


class TestSilencedAlertGetDuration(FrappeTestCase):
	"""get_duration() sets self.duration to a human-readable timedelta string."""

	def _doc(self, from_time: str, to_time: str) -> SimpleNamespace:
		return SimpleNamespace(from_time=from_time, to_time=to_time, duration=None)

	def test_one_hour_duration(self):
		doc = self._doc("2026-01-01 10:00:00", "2026-01-01 11:00:00")
		SilencedAlert.get_duration(doc)
		self.assertIsNotNone(doc.duration)
		# format_duration(3600) → "1h" (Frappe compact format)
		self.assertEqual(doc.duration, "1h")

	def test_zero_duration(self):
		doc = self._doc("2026-01-01 10:00:00", "2026-01-01 10:00:00")
		SilencedAlert.get_duration(doc)
		self.assertIsNotNone(doc.duration)

	def test_duration_thirty_minutes(self):
		doc = self._doc("2026-01-01 09:00:00", "2026-01-01 09:30:00")
		SilencedAlert.get_duration(doc)
		self.assertIsNotNone(doc.duration)
		# format_duration(1800) → "30m"
		self.assertEqual(doc.duration, "30m")

	def test_duration_two_days(self):
		doc = self._doc("2026-01-01 00:00:00", "2026-01-03 00:00:00")
		SilencedAlert.get_duration(doc)
		self.assertIsNotNone(doc.duration)
		# format_duration(172800) → "2d"
		self.assertEqual(doc.duration, "2d")


# ══════════════════════════════════════════════════════════════════════════════
# SilencedAlert.get_keyword_based_on_instance_type
# ══════════════════════════════════════════════════════════════════════════════


class TestSilencedAlertGetKeyword(FrappeTestCase):
	"""get_keyword_based_on_instance_type() maps instance types to Prometheus label keys."""

	def _doc(self, instance_type: str) -> SimpleNamespace:
		return SimpleNamespace(instance_type=instance_type)

	def test_site_returns_instance(self):
		self.assertEqual(SilencedAlert.get_keyword_based_on_instance_type(self._doc("Site")), "instance")

	def test_server_returns_instance(self):
		self.assertEqual(SilencedAlert.get_keyword_based_on_instance_type(self._doc("Server")), "instance")

	def test_cluster_returns_cluster(self):
		self.assertEqual(SilencedAlert.get_keyword_based_on_instance_type(self._doc("Cluster")), "cluster")

	def test_release_group_returns_group(self):
		self.assertEqual(
			SilencedAlert.get_keyword_based_on_instance_type(self._doc("Release Group")), "group"
		)

	def test_bench_returns_bench(self):
		self.assertEqual(SilencedAlert.get_keyword_based_on_instance_type(self._doc("Bench")), "bench")

	def test_prometheus_alert_rule_returns_alertname(self):
		self.assertEqual(
			SilencedAlert.get_keyword_based_on_instance_type(self._doc("Prometheus Alert Rule")),
			"alertname",
		)

	def test_unknown_instance_type_returns_empty_string(self):
		self.assertEqual(SilencedAlert.get_keyword_based_on_instance_type(self._doc("Unknown")), "")
