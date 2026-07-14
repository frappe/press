# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


def _make_event(tid="TID-1", **overrides):
	base = {
		"transaction_id": tid,
		"timestamp": "06/Jul/2026:12:00:00 +0000",
		"client_ip": "10.0.0.9",
		"request_method": "GET",
		"request_uri": "/api/method/foo?fields=a",
		"rule_id": "30001",
		"rule_msg": "Endpoint blocked",
		"severity": "WARNING",
		"action": "Intercepted",
		"matched_data": "Matched Data: x",
		"raw_log": "--abc-A-- ... --abc-Z--",
	}
	base.update(overrides)
	return base


def _ingest(events, auth_ok=True, token="tok", site="site.test"):
	"""Drive `press.api.waf.ingest_logs` with the heavy bits stubbed."""
	from press.api import waf

	headers = {"Authorization": f"Bearer {token}", "X-Press-Site": site}
	with (
		patch.object(waf, "_authenticate", return_value=auth_ok),
		patch.object(waf, "_server_ips_for_waf", return_value=set()),
		patch.object(frappe, "set_user"),
		patch.object(
			frappe,
			"get_request_header",
			side_effect=lambda k, d="": headers.get(k, d),
		),
		patch("press.api.waf.rate_limit", lambda **kw: (lambda fn: fn)),
	):
		frappe.local.request = type("R", (), {})()
		frappe.local.request.get_data = lambda as_text=True: json.dumps(events)
		frappe.local.request.headers = headers
		return waf.ingest_logs()


def _ingest_raw(body="[]", auth_ok=True, token=None, site="site.test"):
	"""Variant for auth-rejection tests where the body never matters."""
	from press.api import waf

	headers = {}
	if token is not None:
		headers["Authorization"] = f"Bearer {token}"
	headers["X-Press-Site"] = site
	with (
		patch.object(waf, "_authenticate", return_value=auth_ok),
		patch.object(waf, "_server_ips_for_waf", return_value=set()),
		patch.object(frappe, "set_user"),
		patch.object(
			frappe,
			"get_request_header",
			side_effect=lambda k, d="": headers.get(k, d),
		),
		patch("press.api.waf.rate_limit", lambda **kw: (lambda fn: fn)),
	):
		frappe.local.request = type("R", (), {})()
		frappe.local.request.get_data = lambda as_text=True: body
		frappe.local.request.headers = headers
		return waf.ingest_logs()


class TestWAFLogIngest(FrappeTestCase):
	"""End-to-end-ish coverage of `press.api.waf.ingest_logs`.

	`_authenticate` is stubbed so the tests don't depend on a live WAF/site
	bearer token; real credential validation logic is covered by
	`TestWAFIngestHelpers` and the mocked-bad-token cases below.
	"""

	def test_ingest_inserts_waf_log_rows(self):
		result = _ingest([_make_event("TID-A"), _make_event("TID-B")])
		self.assertEqual(result["inserted"], 2)
		self.assertEqual(result["duplicates"], 0)
		rows = frappe.get_all(
			"WAF Log",
			{"transaction_id": ["in", ["TID-A", "TID-B"]]},
			["transaction_id", "rule_id", "severity", "action", "client_ip"],
		)
		self.assertEqual({r["transaction_id"] for r in rows}, {"TID-A", "TID-B"})
		for r in rows:
			self.assertEqual(r["severity"], "WARNING")
			self.assertEqual(r["action"], "Intercepted")
			self.assertEqual(r["client_ip"], "10.0.0.9")

	def test_ingest_skips_duplicates(self):
		frappe.get_doc(
			{
				"doctype": "WAF Log",
				"transaction_id": "DUP-1",
				"timestamp": frappe.utils.now_datetime(),
				"site": "site.test",
			}
		).insert(ignore_permissions=True)
		result = _ingest([_make_event("DUP-1"), _make_event("DUP-2")])
		self.assertEqual(result["inserted"], 1)
		self.assertEqual(result["duplicates"], 1)

	def test_ingest_truncates_oversized_fields(self):
		event = _make_event("BIG-1", raw_log="x" * 100_000, matched_data="m" * 10_000)
		result = _ingest([event])
		self.assertEqual(result["inserted"], 1)
		row = frappe.get_doc("WAF Log", "BIG-1")
		self.assertEqual(len(row.raw_log), 16_000)
		self.assertEqual(row.raw_log[-3:], "...")
		self.assertEqual(len(row.matched_data), 4_000)

	def test_ingest_rejects_missing_token(self):
		# Missing Authorization header → PermissionError.
		self.assertRaises(frappe.PermissionError, _ingest_raw, token=None)

	def test_ingest_rejects_bad_token(self):
		# `_authenticate` returns False → PermissionError.
		self.assertRaises(frappe.PermissionError, _ingest_raw, auth_ok=False, token="wrong")


class TestWAFIngestHelpers(FrappeTestCase):
	def test_consttime_eq_same_and_different(self):
		from press.api.waf import _consttime_eq

		self.assertTrue(_consttime_eq("abc", "abc"))
		self.assertFalse(_consttime_eq("abc", "abd"))
		self.assertFalse(_consttime_eq("abc", "abcd"))

	def test_coerce_truncated_none(self):
		from press.api.waf import _coerce_truncated

		self.assertIsNone(_coerce_truncated(None, 10))
		self.assertEqual(_coerce_truncated("abc", 10), "abc")
		out = _coerce_truncated("abcdef", 4)
		self.assertEqual(out, "a...")

	def test_coerce_severity_normalises(self):
		from press.api.waf import _coerce_severity

		self.assertEqual(_coerce_severity("warning"), "WARNING")
		self.assertEqual(_coerce_severity("ERROR"), "ERROR")
		self.assertIsNone(_coerce_severity("BOGUS"))
		self.assertIsNone(_coerce_severity(None))

	def test_coerce_action(self):
		from press.api.waf import _coerce_action

		self.assertEqual(_coerce_action("Intercepted"), "Intercepted")
		self.assertIsNone(_coerce_action("Blocked"))


class TestWAFConfigPayload(FrappeTestCase):
	"""Verify `Agent._waf_config_payload` serialises a WAF doctype correctly."""

	def test_payload_shape(self):
		from press.agent import Agent

		fake_waf = type(
			"WAFStub",
			(),
			{
				"enabled": 1,
				"mode": "Prevention",
				"rate_limits": [type("R", (), {"rate": 100, "window": 60, "burst": 10, "key": "IP"})()],
				"blocked_endpoints": [type("E", (), {"endpoint": "^/admin", "methods": "GET"})()],
				"blocked_parameters": [type("P", (), {"parameter": "evil", "location": "ARGS"})()],
				"allowed_parameters": [type("P", (), {"parameter": "ok", "location": "ARGS"})()],
				"request_limits": [type("L", (), {"limit_type": "Body Size", "value": 1024})()],
				"ip_rules": [
					type("I", (), {"ip": "1.2.3.4", "rule_type": "Allowed"})(),
					type("I", (), {"ip": "5.6.7.8", "rule_type": "Blocked"})(),
				],
				"custom_rules": [
					type(
						"C",
						(),
						{
							"rule_id": 100000,
							"rule_name": "demo",
							"rule_text": 'SecRule ARGS "@streq x" "id:100000,phase:2,deny,log"',
						},
					)()
				],
				"get_log_token": lambda: "tok-secret",
			},
		)()
		agent = Agent.__new__(Agent)
		payload = agent._waf_config_payload(fake_waf)
		self.assertTrue(payload["enabled"])
		self.assertEqual(payload["mode"], "Prevention")
		self.assertEqual(payload["waf_log_token"], "tok-secret")
		self.assertEqual(payload["rate_limits"][0], {"rate": 100, "window": 60, "burst": 10, "key": "IP"})
		self.assertEqual(payload["blocked_endpoints"][0], {"endpoint": "^/admin", "methods": "GET"})
		self.assertEqual(payload["ip_rules"][0], {"ip": "1.2.3.4", "rule_type": "Allowed"})
		self.assertEqual(payload["custom_rules"][0]["rule_id"], 100000)
