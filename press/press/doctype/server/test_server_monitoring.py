# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.account_request.test_account_request import create_test_account_request
from press.press.doctype.server.server import BENCH_DATA_MNT_POINT
from press.press.doctype.server.server_monitoring import (
	DISK_FILL_HORIZON_HOURS,
	SignupFailureRate,
	_breaches_signup_failure_threshold,
	_describe_filling_filesystems,
	_disk_fill_mountpoints,
	_disk_fill_selector,
	_get_incomplete_signup_rate,
	_get_trial_signup_failure_rate,
	_send_disk_fill_alert,
	_send_signup_failure_alert,
	alert_on_build_servers_filling_up,
	alert_on_failing_signups,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_team

if TYPE_CHECKING:
	from press.press.doctype.account_request.account_request import AccountRequest


def create_test_trial_request(status: str, owner: str | None = None, settled_minutes_ago: int = 0):
	"""Product Trial Request in a terminal state.

	Status goes in through the db so the terminal-status hooks, which expect a real site,
	don't run. The monitor reads these columns, so that is what the fixture has to get right.
	"""
	request = frappe.get_doc({"doctype": "Product Trial Request", "status": "Pending"}).insert(
		ignore_permissions=True
	)
	values = {
		"status": status,
		"status_updated_on": frappe.utils.add_to_date(None, minutes=-settled_minutes_ago),
	}
	if owner:
		values["owner"] = owner
	frappe.db.set_value("Product Trial Request", request.name, values, update_modified=False)
	return request


def create_test_signups(count: int, with_team: bool = False, minutes_ago: int = 90) -> list[AccountRequest]:
	"""Signup requests aged into the window the monitor looks at, optionally completed."""
	requests = []
	for _ in range(count):
		email = f"failing-signup-{frappe.generate_hash(length=8)}@example.com"
		requests.append(
			create_test_account_request(
				subdomain=frappe.mock("name"),
				email=email,
				creation=frappe.utils.add_to_date(None, minutes=-minutes_ago),
			)
		)
		if with_team:
			create_test_team(email)
	return requests


def build_signup_failure_rate(
	failed: int,
	total: int,
	minimum_count: int = 5,
	ratio_threshold: float = 0.3,
	label: str = "Product trial signups that errored out",
) -> SignupFailureRate:
	return {
		"label": label,
		"failed": failed,
		"total": total,
		"ratio_threshold": ratio_threshold,
		"minimum_count": minimum_count,
		"breakdown": {"gameplan": failed},
		"link": "https://frappecloud.com/app/product-trial-request?status=Error",
	}


def patch_signup_failure_rates(trial: SignupFailureRate, incomplete: SignupFailureRate):
	return patch.multiple(
		"press.press.doctype.server.server_monitoring",
		_get_trial_signup_failure_rate=lambda: trial,
		_get_incomplete_signup_rate=lambda: incomplete,
	)


class TestSignupFailureRates(FrappeTestCase):
	"""Rates are asserted as deltas against a baseline taken first.

	The monitor counts every signup on the site, so the alternative was deleting rows
	this test didn't create, which would wipe fixtures and real signups alike.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def test_trial_signups_that_errored_out_are_counted_against_settled_requests(self):
		baseline = _get_trial_signup_failure_rate()
		for _ in range(4):
			create_test_trial_request("Error")
		for _ in range(2):
			create_test_trial_request("Site Created")

		rate = _get_trial_signup_failure_rate()

		self.assertEqual(rate["failed"] - baseline["failed"], 4)
		self.assertEqual(rate["total"] - baseline["total"], 6)

	def test_trial_signups_that_have_not_settled_are_not_counted(self):
		baseline = _get_trial_signup_failure_rate()
		create_test_trial_request("Pending")
		create_test_trial_request("Wait for Site")

		rate = _get_trial_signup_failure_rate()

		self.assertEqual(rate["total"] - baseline["total"], 0)

	def test_trial_signup_that_took_hours_to_fail_is_counted_in_the_hour_it_failed(self):
		baseline = _get_trial_signup_failure_rate()
		request = create_test_trial_request("Error")
		frappe.db.set_value(
			"Product Trial Request",
			request.name,
			"creation",
			frappe.utils.add_to_date(None, hours=-3),
			update_modified=False,
		)

		rate = _get_trial_signup_failure_rate()

		self.assertEqual(rate["failed"] - baseline["failed"], 1)

	def test_trial_signup_that_settled_before_the_window_is_not_counted(self):
		baseline = _get_trial_signup_failure_rate()
		create_test_trial_request("Error", settled_minutes_ago=90)

		rate = _get_trial_signup_failure_rate()

		self.assertEqual(rate["failed"] - baseline["failed"], 0)

	def test_trial_signup_written_to_after_it_settled_is_not_counted_again(self):
		"""A settled request keeps getting written to - the accessibility check at login,
		the subscription flag - and none of that makes its outcome recent."""
		baseline = _get_trial_signup_failure_rate()
		request = create_test_trial_request("Error", settled_minutes_ago=90)
		frappe.db.set_value("Product Trial Request", request.name, "is_site_accessible", "Yes")

		rate = _get_trial_signup_failure_rate()

		self.assertEqual(rate["failed"] - baseline["failed"], 0)

	def test_trial_signup_is_stamped_when_its_status_changes(self):
		request = create_test_trial_request("Pending", settled_minutes_ago=90)
		request.reload()
		request.status = "Error"
		request.save(ignore_permissions=True)

		self.assertGreater(
			frappe.utils.get_datetime(request.status_updated_on),
			frappe.utils.add_to_date(None, minutes=-1),
		)

	def test_signup_canary_trial_requests_are_not_counted(self):
		baseline = _get_trial_signup_failure_rate()
		create_test_trial_request("Error", owner="fc-signup-test+1@example.com")

		rate = _get_trial_signup_failure_rate()

		self.assertEqual(rate["total"] - baseline["total"], 0)

	def test_signups_without_a_team_past_the_grace_period_are_counted_as_failures(self):
		baseline = _get_incomplete_signup_rate()
		create_test_signups(2)

		rate = _get_incomplete_signup_rate()

		self.assertEqual(rate["failed"] - baseline["failed"], 2)
		self.assertEqual(rate["total"] - baseline["total"], 2)

	def test_signups_that_became_teams_are_not_counted_as_failures(self):
		baseline = _get_incomplete_signup_rate()
		create_test_signups(2, with_team=True)

		rate = _get_incomplete_signup_rate()

		self.assertEqual(rate["failed"] - baseline["failed"], 0)
		self.assertEqual(rate["total"] - baseline["total"], 2)

	def test_signups_still_within_the_grace_period_are_not_counted(self):
		baseline = _get_incomplete_signup_rate()
		create_test_signups(2, minutes_ago=5)

		rate = _get_incomplete_signup_rate()

		self.assertEqual(rate["total"] - baseline["total"], 0)

	def test_team_invites_are_not_counted_as_signups(self):
		baseline = _get_incomplete_signup_rate()
		[request] = create_test_signups(1)
		frappe.db.set_value(
			"Account Request", request.name, "invited_by", "member@example.com", update_modified=False
		)

		rate = _get_incomplete_signup_rate()

		self.assertEqual(rate["total"] - baseline["total"], 0)


class TestSignupFailureThreshold(FrappeTestCase):
	def test_failure_ratio_above_threshold_breaches(self):
		self.assertTrue(_breaches_signup_failure_threshold(build_signup_failure_rate(failed=4, total=6)))

	def test_failure_ratio_at_threshold_does_not_breach(self):
		self.assertFalse(_breaches_signup_failure_threshold(build_signup_failure_rate(failed=3, total=10)))

	def test_signup_count_below_the_floor_does_not_breach(self):
		self.assertFalse(_breaches_signup_failure_threshold(build_signup_failure_rate(failed=4, total=4)))


@patch("press.press.doctype.server.server_monitoring.send_raven_message")
class TestSignupFailureAlert(FrappeTestCase):
	def test_alert_names_the_signal_the_ratio_and_the_breakdown(self, send_raven_message):
		_send_signup_failure_alert([build_signup_failure_rate(failed=4, total=6)])

		message = send_raven_message.call_args[0][0]
		self.assertIn("Product trial signups that errored out", message)
		self.assertIn("4 of 6 (66.67%)", message)
		self.assertIn("- gameplan: 4", message)

	def test_alert_lists_only_the_signal_that_breached(self, send_raven_message):
		with patch_signup_failure_rates(
			trial=build_signup_failure_rate(failed=4, total=6),
			incomplete=build_signup_failure_rate(
				failed=1,
				total=100,
				minimum_count=10,
				ratio_threshold=0.9,
				label="Signups that never became a team",
			),
		):
			alert_on_failing_signups()

		message = send_raven_message.call_args[0][0]
		self.assertIn("**Signup Failure Alerts** - 1", message)
		self.assertIn("Product trial signups that errored out", message)
		self.assertNotIn("Signups that never became a team", message)

	def test_no_alert_when_neither_signal_breaches(self, send_raven_message):
		with patch_signup_failure_rates(
			trial=build_signup_failure_rate(failed=1, total=10),
			incomplete=build_signup_failure_rate(failed=1, total=100, minimum_count=10, ratio_threshold=0.9),
		):
			alert_on_failing_signups()

		send_raven_message.assert_not_called()


GIGABYTE = 1024**3


class TestDiskFillMountpoints(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_mountpoints_come_from_the_mounts_of_the_server(self):
		server = create_test_server(use_for_build=True)
		server.append(
			"mounts", {"mount_point": "/home/frappe/mnt/builds", "mount_type": "Volume", "source": "/dev/vdb"}
		)
		server.save()

		self.assertEqual(_disk_fill_mountpoints([server.name]), ["/", "/home/frappe/mnt/builds"])

	def test_a_server_without_a_data_volume_still_reads_the_root_filesystem(self):
		server = create_test_server(use_for_build=True)

		self.assertEqual(_disk_fill_mountpoints([server.name]), ["/"])

	def test_a_data_volume_on_the_machine_counts_even_without_a_mount_row(self):
		"""Server Mount and the volumes of the machine go out of sync."""
		server = create_test_server(use_for_build=True, has_data_volume=True)
		server.mounts = []
		server.save()

		self.assertEqual(_disk_fill_mountpoints([server.name]), ["/", BENCH_DATA_MNT_POINT])

	def test_the_mounts_of_another_server_are_left_out(self):
		server = create_test_server(use_for_build=True)
		other = create_test_server(use_for_build=True)
		other.append(
			"mounts", {"mount_point": "/mnt/volume_blr1_01", "mount_type": "Volume", "source": "/dev/vdb"}
		)
		other.save()

		self.assertNotIn("/mnt/volume_blr1_01", _disk_fill_mountpoints([server.name]))

	def test_the_selector_names_the_servers_and_their_mountpoints(self):
		server = create_test_server(use_for_build=True)
		server.append(
			"mounts", {"mount_point": "/opt/volumes/benches", "mount_type": "Volume", "source": "/dev/vdb"}
		)
		server.save()

		selector = _disk_fill_selector([server.name])

		self.assertIn(f'instance=~"^({server.name.replace(".", chr(92) * 2 + ".")})$"', selector)
		self.assertIn('mountpoint=~"^(/|/opt/volumes/benches)$"', selector)


class TestFillingFilesystems(FrappeTestCase):
	def test_a_disk_that_drains_to_empty_reports_the_minutes_it_has_left(self):
		# 10 GB free now, 5 GB left after an hour, so it drains in two hours
		filesystems = _describe_filling_filesystems(
			{("f1.frappe.cloud", "/opt/volumes/docker"): 5 * GIGABYTE},
			{("f1.frappe.cloud", "/opt/volumes/docker"): 10 * GIGABYTE},
			DISK_FILL_HORIZON_HOURS * 3600,
		)

		self.assertEqual(len(filesystems), 1)
		self.assertEqual(filesystems[0]["server"], "f1.frappe.cloud")
		self.assertEqual(filesystems[0]["mountpoint"], "/opt/volumes/docker")
		self.assertAlmostEqual(filesystems[0]["minutes_to_full"], 120)

	def test_a_disk_that_gained_space_is_left_out(self):
		filesystems = _describe_filling_filesystems(
			{("f1.frappe.cloud", "/"): 20 * GIGABYTE},
			{("f1.frappe.cloud", "/"): 10 * GIGABYTE},
			DISK_FILL_HORIZON_HOURS * 3600,
		)

		self.assertEqual(filesystems, [])

	def test_a_disk_without_a_current_reading_is_left_out(self):
		filesystems = _describe_filling_filesystems(
			{("f1.frappe.cloud", "/"): -1 * GIGABYTE}, {}, DISK_FILL_HORIZON_HOURS * 3600
		)

		self.assertEqual(filesystems, [])


@patch("press.press.doctype.server.server_monitoring.send_raven_message")
class TestDiskFillAlert(FrappeTestCase):
	def test_alert_names_the_server_the_mountpoint_the_free_space_and_the_time_left(self, send_raven_message):
		_send_disk_fill_alert(
			[
				{
					"server": "f1.frappe.cloud",
					"mountpoint": "/opt/volumes/docker",
					"free_bytes": 4.5 * GIGABYTE,
					"minutes_to_full": 23.4,
				}
			]
		)

		message = send_raven_message.call_args[0][0]
		self.assertIn("**Build Server Disk Filling** - 1", message)
		self.assertIn("f1.frappe.cloud", message)
		self.assertIn("/opt/volumes/docker", message)
		self.assertIn("4.5 GB", message)
		self.assertIn("23 min", message)

	def test_the_disk_with_the_least_time_left_comes_first(self, send_raven_message):
		_send_disk_fill_alert(
			[
				{
					"server": "f2.frappe.cloud",
					"mountpoint": "/",
					"free_bytes": GIGABYTE,
					"minutes_to_full": 50,
				},
				{
					"server": "f1.frappe.cloud",
					"mountpoint": "/",
					"free_bytes": GIGABYTE,
					"minutes_to_full": 10,
				},
			]
		)

		message = send_raven_message.call_args[0][0]
		self.assertLess(message.index("f1.frappe.cloud"), message.index("f2.frappe.cloud"))

	def test_no_alert_when_no_disk_is_filling(self, send_raven_message):
		with patch("press.press.doctype.server.server_monitoring._filesystems_filling_up", return_value=[]):
			alert_on_build_servers_filling_up()

		send_raven_message.assert_not_called()
