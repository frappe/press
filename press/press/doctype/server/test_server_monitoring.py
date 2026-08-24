# Copyright (c) 2019, Frappe and Contributors
# See license.txt

from __future__ import annotations

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.server.server_monitoring import (
	MINIMUM_SITE_DISK_BYTES,
	PublicServerHealthMetrics,
	_send_low_disk_alert,
	_servers_with_enough_disk,
)


def create_test_metrics(
	available_disk_bytes: dict[str, float],
	available_disk_ratio: dict[str, float],
) -> PublicServerHealthMetrics:
	return {
		"available_memory_bytes": {},
		"available_memory_ratio": {},
		"cpu_idle_ratio": {},
		"oom_kills": {},
		"available_disk_bytes": available_disk_bytes,
		"available_disk_ratio": available_disk_ratio,
	}


class TestServersWithEnoughDisk(FrappeTestCase):
	def test_server_below_disk_floor_is_not_a_candidate(self):
		servers = _servers_with_enough_disk(
			["low.hetzner", "high.hetzner"],
			{"low.hetzner": MINIMUM_SITE_DISK_BYTES - 1, "high.hetzner": MINIMUM_SITE_DISK_BYTES},
		)
		self.assertEqual(servers, ["high.hetzner"])

	def test_server_of_other_provider_is_a_candidate(self):
		"""Only disk-aware providers are in the map. The others must not be dropped."""
		self.assertEqual(_servers_with_enough_disk(["aws.server"], {}), ["aws.server"])

	def test_all_servers_below_disk_floor_keeps_every_candidate(self):
		servers = ["low.hetzner", "lower.hetzner"]
		self.assertEqual(
			_servers_with_enough_disk(servers, {"low.hetzner": 1.0, "lower.hetzner": 0.0}), servers
		)


@patch("press.press.doctype.server.server_monitoring.send_raven_message")
class TestLowDiskAlert(FrappeTestCase):
	def test_alert_sent_for_selected_server_below_disk_floor(self, send_raven_message):
		metrics = create_test_metrics({"low.hetzner": 20 * 1024**3}, {"low.hetzner": 0.8})
		_send_low_disk_alert({"low.hetzner"}, metrics)
		self.assertIn("low.hetzner", send_raven_message.call_args[0][0])
		self.assertIn("20.00 GiB", send_raven_message.call_args[0][0])

	def test_alert_sent_for_selected_server_that_is_half_full(self, send_raven_message):
		metrics = create_test_metrics({"full.hetzner": 900 * 1024**3}, {"full.hetzner": 0.45})
		_send_low_disk_alert({"full.hetzner"}, metrics)
		self.assertIn("45.00%", send_raven_message.call_args[0][0])

	def test_no_alert_for_selected_server_with_enough_disk(self, send_raven_message):
		metrics = create_test_metrics({"free.hetzner": 900 * 1024**3}, {"free.hetzner": 0.9})
		_send_low_disk_alert({"free.hetzner"}, metrics)
		send_raven_message.assert_not_called()

	def test_no_alert_for_server_of_other_provider(self, send_raven_message):
		_send_low_disk_alert({"aws.server"}, create_test_metrics({}, {}))
		send_raven_message.assert_not_called()
