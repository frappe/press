# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.account_request.test_account_request import create_test_account_request
from press.press.doctype.agent_job.test_agent_job import create_test_agent_job
from press.press.doctype.database_server.test_database_server import create_test_database_server
from press.press.doctype.server import server_monitoring
from press.press.doctype.server.server_monitoring import (
	STUCK_AGENT_JOBS_ALERT_THRESHOLD,
	STUCK_AGENT_JOBS_WINDOW_HOURS,
	PublicServerHealthMetrics,
	SignupFailureRate,
	_breaches_signup_failure_threshold,
	_get_excluded_public_server_disk_issues,
	_get_incomplete_signup_rate,
	_get_servers_with_stuck_agent_jobs,
	_get_trial_signup_failure_rate,
	_send_signup_failure_alert,
	alert_on_failing_signups,
	alert_on_servers_with_stuck_agent_jobs,
	get_public_servers_with_free_capacity,
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


def create_stuck_agent_jobs(server, count: int, status: str = "Undelivered", minutes_ago: int = 60):
	for _ in range(count):
		job = create_test_agent_job(server=server.name, server_type=server.doctype, status=status)
		created = frappe.utils.add_to_date(None, minutes=-minutes_ago)
		frappe.db.set_value("Agent Job", job.name, "creation", created, update_modified=False)


def get_stuck_agent_jobs_row(server):
	rows = _get_servers_with_stuck_agent_jobs()
	return next((row for row in rows if row["server"] == server.name), None)


class TestServersWithStuckAgentJobs(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_server_with_undelivered_and_pending_jobs_at_threshold_is_reported(self):
		server = create_test_server()
		create_stuck_agent_jobs(server, STUCK_AGENT_JOBS_ALERT_THRESHOLD - 1)
		create_stuck_agent_jobs(server, 1, status="Pending")

		row = get_stuck_agent_jobs_row(server)

		self.assertEqual((row["undelivered"], row["pending"]), (STUCK_AGENT_JOBS_ALERT_THRESHOLD - 1, 1))

	def test_server_below_threshold_is_not_reported(self):
		server = create_test_server()
		create_stuck_agent_jobs(server, STUCK_AGENT_JOBS_ALERT_THRESHOLD - 1)

		self.assertIsNone(get_stuck_agent_jobs_row(server))

	def test_jobs_younger_than_the_minimum_age_are_not_counted(self):
		server = create_test_server()
		create_stuck_agent_jobs(server, STUCK_AGENT_JOBS_ALERT_THRESHOLD, minutes_ago=5)

		self.assertIsNone(get_stuck_agent_jobs_row(server))

	def test_jobs_older_than_the_window_are_not_counted(self):
		server = create_test_server()
		minutes_ago = (STUCK_AGENT_JOBS_WINDOW_HOURS + 1) * 60
		create_stuck_agent_jobs(server, STUCK_AGENT_JOBS_ALERT_THRESHOLD, minutes_ago=minutes_ago)

		self.assertIsNone(get_stuck_agent_jobs_row(server))

	def test_archived_server_is_not_reported(self):
		server = create_test_server()
		create_stuck_agent_jobs(server, STUCK_AGENT_JOBS_ALERT_THRESHOLD)
		frappe.db.set_value("Server", server.name, "status", "Archived")

		self.assertIsNone(get_stuck_agent_jobs_row(server))

	@patch("press.press.doctype.server.server_monitoring.send_raven_message")
	def test_alert_names_the_halted_database_server_with_its_job_counts(self, send_raven_message):
		database_server = create_test_database_server()
		frappe.db.set_value("Database Server", database_server.name, "halt_agent_jobs", 1)
		create_stuck_agent_jobs(database_server, STUCK_AGENT_JOBS_ALERT_THRESHOLD)

		alert_on_servers_with_stuck_agent_jobs()

		message = send_raven_message.call_args[0][0]
		self.assertIn(
			f"| Database Server | {STUCK_AGENT_JOBS_ALERT_THRESHOLD} | 0 | Yes |",
			next(line for line in message.splitlines() if database_server.name in line),
		)


def build_public_server_health_metrics(
	servers: dict[str, tuple[float, float, float]],
) -> PublicServerHealthMetrics:
	"""Metrics built from {server: (free memory ratio, idle cpu ratio, used disk ratio)}."""
	return {
		"available_memory_bytes": {server: ratios[0] * 16 * 1024**3 for server, ratios in servers.items()},
		"available_memory_ratio": {server: ratios[0] for server, ratios in servers.items()},
		"cpu_idle_ratio": {server: ratios[1] for server, ratios in servers.items()},
		"disk_used_ratio": {server: ratios[2] for server, ratios in servers.items()},
		"oom_kills": {},
	}


def patch_public_server_health_metrics(servers: dict[str, tuple[float, float, float]]):
	"""Answer the Prometheus lookup with handpicked metrics, for the servers asked about."""
	metrics = build_public_server_health_metrics(servers)

	def get_metrics(server_names: list[str]) -> PublicServerHealthMetrics:
		return {
			metric: {server: value for server, value in values.items() if server in server_names}
			for metric, values in metrics.items()
		}

	return patch(
		"press.press.doctype.server.server_monitoring._get_public_server_health_metrics",
		new=get_metrics,
	)


class TestPublicServersWithFreeCapacity(FrappeTestCase):
	"""The servers a site can be moved to, picked on live memory, CPU and disk."""

	def test_server_with_the_most_free_memory_and_idle_cpu_comes_first(self):
		with patch_public_server_health_metrics(
			{"crowded.fc.dev": (0.25, 0.55, 0.5), "roomy.fc.dev": (0.60, 0.90, 0.2)}
		):
			servers = get_public_servers_with_free_capacity(["crowded.fc.dev", "roomy.fc.dev"])

		self.assertEqual([server["name"] for server in servers], ["roomy.fc.dev", "crowded.fc.dev"])
		self.assertEqual(servers[0]["free_memory_percent"], 60.0)
		self.assertEqual(servers[0]["idle_cpu_percent"], 90.0)
		self.assertEqual(servers[0]["free_disk_percent"], 80.0)

	def test_server_short_on_memory_is_left_out(self):
		with patch_public_server_health_metrics({"tight.fc.dev": (0.19, 0.90, 0.2)}):
			self.assertEqual(get_public_servers_with_free_capacity(["tight.fc.dev"]), [])

	def test_server_short_on_idle_cpu_is_left_out(self):
		with patch_public_server_health_metrics({"busy.fc.dev": (0.60, 0.49, 0.2)}):
			self.assertEqual(get_public_servers_with_free_capacity(["busy.fc.dev"]), [])

	def test_server_with_a_nearly_full_disk_is_left_out(self):
		with patch_public_server_health_metrics({"full.fc.dev": (0.60, 0.90, 0.86)}):
			self.assertEqual(get_public_servers_with_free_capacity(["full.fc.dev"]), [])

	def test_server_with_disk_to_spare_is_kept(self):
		with patch_public_server_health_metrics({"roomy.fc.dev": (0.60, 0.90, 0.84)}):
			servers = get_public_servers_with_free_capacity(["roomy.fc.dev"])

		self.assertEqual([server["name"] for server in servers], ["roomy.fc.dev"])
		self.assertEqual(servers[0]["free_disk_percent"], 16.0)

	def test_capacity_is_not_guessed_when_prometheus_has_no_answer(self):
		with patch(
			"press.press.doctype.server.server_monitoring._get_public_server_health_metrics",
			new=lambda server_names: None,
		):
			self.assertRaisesRegex(
				frappe.ValidationError,
				"Server capacity is unavailable right now",
				get_public_servers_with_free_capacity,
				["quiet.fc.dev"],
			)


@patch.object(
	server_monitoring, "_get_public_server_pool_prometheus_connection", return_value=("url", ("user", "pass"))
)
@patch.object(server_monitoring, "_query_prometheus_vector")
class TestExcludedPublicServerDiskIssues(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_excluded_public_server_above_90_percent_disk_is_reported(self, query_prometheus, _):
		excluded = create_test_server(public=True)
		frappe.db.set_value("Server", excluded.name, "exclude_for_scheduling", 1)
		in_pool = create_test_server(public=True)
		query_prometheus.return_value = [
			{"metric": {"instance": server.name}, "value": [0, "0.95"]} for server in (excluded, in_pool)
		]

		issues = _get_excluded_public_server_disk_issues()

		self.assertEqual(issues[excluded.name], ["Disk utilization: 95.00%"])
		self.assertNotIn(in_pool.name, issues)  # the pool check already reports it
