# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import convert_utc_to_system_timezone
from frappe.utils.password import set_encrypted_password

from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.wazuh import VULNERABILITY_PAGE_SIZE, WazuhIndexer, WazuhManager, wazuh_datetime


def response(status_code: int = 200, json: dict | None = None) -> Mock:
	mocked = Mock(status_code=status_code)
	mocked.json.return_value = json or {}
	mocked.raise_for_status.return_value = None
	return mocked


def page(count: int, start: int = 0) -> dict:
	return {
		"hits": {"hits": [{"_source": {"vulnerability": {"id": f"CVE-{start + i}"}}} for i in range(count)]}
	}


class TestWazuhClients(FrappeTestCase):
	def setUp(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_api_url", "https://wazuh.example.com:55000")
		frappe.db.set_single_value("Press Settings", "wazuh_api_username", "press")
		set_encrypted_password("Press Settings", "Press Settings", "secret", "wazuh_api_password")
		frappe.db.set_single_value("Press Settings", "wazuh_indexer_username", "press")
		set_encrypted_password("Press Settings", "Press Settings", "secret", "wazuh_indexer_password")

	def tearDown(self):
		frappe.db.rollback()

	def test_request_fetches_a_fresh_token_once_after_a_401(self):
		tokens = [response(json={"data": {"token": "first"}}), response(json={"data": {"token": "second"}})]
		replies = [response(401), response(json={"data": {"ok": 1}})]
		with (
			patch("press.wazuh.requests.post", side_effect=tokens),
			patch("press.wazuh.requests.request", side_effect=replies) as request,
		):
			self.assertEqual(WazuhManager().request("GET", "/agents"), {"ok": 1})
		sent = [call.kwargs["headers"]["Authorization"] for call in request.call_args_list]
		self.assertEqual(sent, ["Bearer first", "Bearer second"])

	def test_vulnerabilities_follow_the_pages_until_a_short_one(self):
		pages = [
			response(json=page(VULNERABILITY_PAGE_SIZE)),
			response(json=page(3, VULNERABILITY_PAGE_SIZE)),
		]
		with patch("press.wazuh.requests.post", side_effect=pages) as post:
			findings = WazuhIndexer().vulnerabilities("f1.example.com")
		self.assertEqual(len(findings), VULNERABILITY_PAGE_SIZE + 3)
		self.assertEqual(
			[call.kwargs["json"]["from"] for call in post.call_args_list], [0, VULNERABILITY_PAGE_SIZE]
		)

	def test_severity_counts_are_empty_when_the_agent_has_no_findings(self):
		empty = response(json={"aggregations": {"severity": {"buckets": []}}})
		with patch("press.wazuh.requests.post", return_value=empty):
			self.assertEqual(WazuhIndexer().severity_counts("f1.example.com"), {})

	def test_indexer_queries_the_api_host_on_its_own_port(self):
		empty = response(json={"aggregations": {"severity": {"buckets": []}}})
		with patch("press.wazuh.requests.post", return_value=empty) as post:
			WazuhIndexer().severity_counts("f1.example.com")
		self.assertEqual(
			post.call_args.args[0], "https://wazuh.example.com:9200/wazuh-states-vulnerabilities-*/_search"
		)
		self.assertEqual(post.call_args.kwargs["auth"], ("press", "secret"))

	def test_indexer_refuses_to_start_without_an_indexer_user(self):
		frappe.db.set_single_value("Press Settings", "wazuh_indexer_username", "")
		with self.assertRaisesRegex(frappe.ValidationError, "indexer user"):
			WazuhIndexer()

	def test_wazuh_datetime_converts_utc_to_the_system_timezone_and_drops_the_placeholder(self):
		expected = convert_utc_to_system_timezone(datetime(2026, 11, 4, 10)).replace(tzinfo=None)
		self.assertEqual(wazuh_datetime("2026-11-04T10:00:00Z"), expected)
		self.assertEqual(wazuh_datetime("2026-11-04T10:00:00+00:00"), expected)
		self.assertIsNone(wazuh_datetime("9999-12-31T23:59:59Z"))
		self.assertIsNone(wazuh_datetime(None))
