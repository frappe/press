# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import patch
from zoneinfo import ZoneInfo

import frappe
from frappe.core.doctype.log_settings.log_settings import LogSettings, LogType
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_system_timezone, nowdate

from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.press.doctype.request_abuse_daily.request_abuse_daily import (
	RequestAbuseDaily,
	day_bounds_in_milliseconds,
	record_day,
	record_yesterday,
)

if TYPE_CHECKING:
	from collections.abc import Mapping

MODULE = "press.press.doctype.request_abuse_daily.request_abuse_daily"
DATE = "2026-11-04"


def sites_response(sites: list[str]) -> dict:
	return {"aggregations": {"sites": {"buckets": [{"key": site, "doc_count": 1} for site in sites]}}}


def site_response(requests=100, statuses=None, unique_ips=3, rate_limited_ips=None) -> dict:
	statuses = statuses if statuses is not None else {200: 90, 429: 10}
	rate_limited_ips = rate_limited_ips if rate_limited_ips is not None else {"10.0.0.1": 7, "10.0.0.2": 3}
	return {
		"hits": {"total": {"value": requests}},
		"aggregations": {
			"status": {
				"buckets": [{"key": status, "doc_count": count} for status, count in statuses.items()]
			},
			"unique_ips": {"value": unique_ips},
			"rate_limited": {
				"ips": {
					"buckets": [{"key": ip, "doc_count": count} for ip, count in rate_limited_ips.items()]
				}
			},
		},
	}


def queried_site(body: dict) -> str:
	match = next(f for f in body["query"]["bool"]["filter"] if "match_phrase" in f)
	return match["match_phrase"]["http.request.site"]


def fake_elasticsearch(sites: list[str], per_site: Mapping[str, dict | Exception] | None = None):
	"""Answer the sites query with `sites`, and each site query with its canned response or error."""

	def post(body, *, should_redact=True):
		if "sites" in body["aggs"]:
			return sites_response(sites)
		reply = (per_site or {}).get(queried_site(body)) or site_response()
		if isinstance(reply, Exception):
			raise reply
		return reply

	return post


class TestRequestAbuseDaily(FrappeTestCase):
	def setUp(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "log_server", "log.example.com")

	def tearDown(self):
		frappe.db.rollback()

	def summaries(self) -> dict[str, frappe._dict]:
		fields = [
			"name",
			"site",
			"requests",
			"rate_limited",
			"unauthorized",
			"forbidden",
			"server_errors",
			"unique_ips",
		]
		return {row.site: row for row in frappe.get_all("Request Abuse Daily", {"date": DATE}, fields)}

	def test_record_day_creates_a_summary_per_rate_limited_site_and_for_press_itself(self):
		with patch(
			f"{MODULE}.elasticsearch_post", side_effect=fake_elasticsearch(["a.example.com", "b.example.com"])
		):
			record_day(DATE)
		self.assertEqual(set(self.summaries()), {"a.example.com", "b.example.com", frappe.local.site})

	def test_record_day_counts_status_codes_unique_ips_and_the_most_rate_limited_ips(self):
		response = site_response(
			requests=1000,
			statuses={200: 900, 401: 20, 403: 30, 429: 40, 500: 5, 502: 5},
			unique_ips=12,
			rate_limited_ips={"10.0.0.1": 30, "10.0.0.2": 10},
		)
		fake = fake_elasticsearch(["a.example.com"], {"a.example.com": response})
		with patch(f"{MODULE}.elasticsearch_post", side_effect=fake) as elasticsearch_post:
			record_day(DATE)

		summary = self.summaries()["a.example.com"]
		self.assertEqual(summary.requests, 1000)
		self.assertEqual(summary.rate_limited, 40)
		self.assertEqual(summary.unauthorized, 20)
		self.assertEqual(summary.forbidden, 30)
		self.assertEqual(summary.server_errors, 10)
		self.assertEqual(summary.unique_ips, 12)
		top_ips = frappe.get_all(
			"Request Abuse Daily IP", {"parent": summary.name}, ["ip", "rate_limited"], order_by="idx"
		)
		self.assertEqual(
			[(row.ip, row.rate_limited) for row in top_ips], [("10.0.0.1", 30), ("10.0.0.2", 10)]
		)
		start, end = day_bounds_in_milliseconds(DATE)
		sent_range = elasticsearch_post.call_args.args[0]["query"]["bool"]["filter"][0]["range"]["@timestamp"]
		self.assertEqual(sent_range, {"gte": start, "lt": end})

	def test_record_day_run_twice_updates_the_summary_instead_of_adding_a_duplicate(self):
		with patch(f"{MODULE}.elasticsearch_post", side_effect=fake_elasticsearch(["a.example.com"])):
			record_day(DATE)
		later = {"a.example.com": site_response(requests=250, statuses={200: 200, 429: 50})}
		with patch(f"{MODULE}.elasticsearch_post", side_effect=fake_elasticsearch(["a.example.com"], later)):
			record_day(DATE)

		self.assertEqual(frappe.db.count("Request Abuse Daily", {"date": DATE, "site": "a.example.com"}), 1)
		self.assertEqual(self.summaries()["a.example.com"].rate_limited, 50)

	def test_a_site_whose_query_fails_is_logged_and_the_other_sites_are_still_recorded(self):
		fake = fake_elasticsearch(["a.example.com", "b.example.com"], {"a.example.com": TimeoutError("slow")})
		with (
			patch(f"{MODULE}.elasticsearch_post", side_effect=fake),
			patch(f"{MODULE}.log_error") as log_error,
		):
			record_day(DATE)

		self.assertEqual(set(self.summaries()), {"b.example.com", frappe.local.site})
		self.assertEqual(log_error.call_args.kwargs["site"], "a.example.com")

	def test_hosts_that_are_not_plain_host_names_are_skipped(self):
		hosts = ["a.example.com", "x" * 141 + ".com", "<script>.example.com", "evil.example.com/path"]
		with patch(f"{MODULE}.elasticsearch_post", side_effect=fake_elasticsearch(hosts)):
			record_day(DATE)
		self.assertEqual(set(self.summaries()), {"a.example.com", frappe.local.site})

	def test_record_yesterday_does_not_query_the_log_server_when_none_is_configured(self):
		frappe.db.set_single_value("Press Settings", "log_server", "")
		with patch(f"{MODULE}.elasticsearch_post") as elasticsearch_post:
			record_yesterday()
		elasticsearch_post.assert_not_called()

	def test_day_bounds_start_at_local_midnight_and_end_where_the_next_day_starts(self):
		start, end = day_bounds_in_milliseconds(DATE)
		local_start = datetime.fromtimestamp(start / 1000, ZoneInfo(get_system_timezone()))
		self.assertEqual(local_start.strftime("%Y-%m-%d %H:%M"), f"{DATE} 00:00")
		self.assertEqual(end, day_bounds_in_milliseconds("2026-11-05")[0])

	def test_day_bounds_refuse_a_missing_date_instead_of_summarising_today(self):
		with self.assertRaisesRegex(frappe.ValidationError, "date is required"):
			day_bounds_in_milliseconds(None)

	def make_summary_with_ip(self, days_ago: int) -> str:
		summary = RequestAbuseDaily(
			{
				"doctype": "Request Abuse Daily",
				"date": add_days(nowdate(), -days_ago),
				"site": f"retention-{days_ago}.example.com",
			}
		)
		summary.append("top_ips", {"ip": "192.0.2.1", "rate_limited": 1})
		summary.insert()
		return str(summary.name)

	def test_request_abuse_daily_supports_log_settings(self):
		self.assertTrue(issubclass(RequestAbuseDaily, LogType))
		self.assertIn(90, frappe.get_hooks("default_log_clearing_doctypes")["Request Abuse Daily"])

	def test_log_settings_runs_the_cleanup_for_the_configured_retention_period(self):
		old = self.make_summary_with_ip(31)
		recent = self.make_summary_with_ip(29)
		settings = LogSettings({"doctype": "Log Settings"})
		settings.append("logs_to_clear", {"ref_doctype": "Request Abuse Daily", "days": 30})

		with patch.object(frappe.db, "commit") as commit:
			settings.clear_logs()

		commit.assert_called_once()
		self.assertFalse(frappe.db.exists("Request Abuse Daily", old))
		self.assertEqual(frappe.db.count("Request Abuse Daily IP", {"parent": old}), 0)
		self.assertTrue(frappe.db.exists("Request Abuse Daily", recent))
		self.assertEqual(frappe.db.count("Request Abuse Daily IP", {"parent": recent}), 1)

	def test_clear_old_logs_removes_expired_summaries_and_ips_but_keeps_the_cutoff_day(self):
		old = self.make_summary_with_ip(91)
		boundary = self.make_summary_with_ip(90)
		recent = self.make_summary_with_ip(1)

		RequestAbuseDaily.clear_old_logs(90)

		self.assertFalse(frappe.db.exists("Request Abuse Daily", old))
		self.assertEqual(frappe.db.count("Request Abuse Daily IP", {"parent": old}), 0)
		for name in (boundary, recent):
			self.assertTrue(frappe.db.exists("Request Abuse Daily", name))
			self.assertEqual(frappe.db.count("Request Abuse Daily IP", {"parent": name}), 1)

	def test_failed_retention_cleanup_can_roll_back_the_ip_deletion(self):
		old = self.make_summary_with_ip(91)
		frappe.db.savepoint("request_abuse_retention_test")
		with (
			patch.object(frappe.db, "delete", side_effect=RuntimeError("delete failed")),
			self.assertRaisesRegex(RuntimeError, "delete failed"),
		):
			RequestAbuseDaily.clear_old_logs(90)
		self.assertEqual(frappe.db.count("Request Abuse Daily IP", {"parent": old}), 0)
		frappe.db.rollback(save_point="request_abuse_retention_test")

		self.assertTrue(frappe.db.exists("Request Abuse Daily", old))
		self.assertEqual(frappe.db.count("Request Abuse Daily IP", {"parent": old}), 1)
