# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for press_webhook/press_webhook.py.

validate_endpoint_url_format() is a pure URL-parsing method with no Frappe DB
round-trips, so we test it by calling it directly on an in-memory doc.
"""

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_webhook.press_webhook import PressWebhook

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _webhook(endpoint: str) -> PressWebhook:
	"""Return a PressWebhook instance (not DB-backed) with the given endpoint."""
	# Use __new__ + manual attribute setting to avoid DB look-ups from Document.__init__
	doc = object.__new__(PressWebhook)
	doc.endpoint = endpoint
	doc.team = "test-team"
	doc.name = "WH-001"
	doc.events = [object()]  # non-empty so that the events check passes
	return doc


# ══════════════════════════════════════════════════════════════════════════════
# validate_endpoint_url_format — valid cases
# ══════════════════════════════════════════════════════════════════════════════


class TestValidateEndpointUrlFormatValid(FrappeTestCase):
	"""Calls that must NOT raise ValidationError."""

	def test_https_domain_passes(self):
		_webhook("https://example.com/hook").validate_endpoint_url_format()

	def test_http_domain_passes(self):
		_webhook("http://example.com/hook").validate_endpoint_url_format()

	def test_https_domain_with_port_passes(self):
		_webhook("https://example.com:8080/hook").validate_endpoint_url_format()

	def test_https_subdomain_passes(self):
		_webhook("https://hooks.myapp.io/press").validate_endpoint_url_format()

	def test_public_ipv4_address_passes(self):
		# 8.8.8.8 is a public IP — must not raise
		_webhook("https://8.8.8.8/webhook").validate_endpoint_url_format()


# ══════════════════════════════════════════════════════════════════════════════
# validate_endpoint_url_format — invalid cases
# ══════════════════════════════════════════════════════════════════════════════


class TestValidateEndpointUrlFormatInvalid(FrappeTestCase):
	"""Calls that MUST raise ValidationError."""

	def test_missing_scheme_raises(self):
		with self.assertRaises(frappe.ValidationError):
			_webhook("example.com/webhook").validate_endpoint_url_format()

	def test_ftp_scheme_raises(self):
		with self.assertRaises(frappe.ValidationError):
			_webhook("ftp://example.com/data").validate_endpoint_url_format()

	def test_url_with_query_params_raises(self):
		with self.assertRaises(frappe.ValidationError):
			_webhook("https://example.com/hook?key=val").validate_endpoint_url_format()

	def test_private_ip_raises(self):
		# 192.168.x.x is a private/non-global IP
		with self.assertRaises(frappe.ValidationError):
			_webhook("https://192.168.1.100/hook").validate_endpoint_url_format()

	def test_loopback_ip_raises(self):
		# 127.0.0.1 is loopback — not global
		with self.assertRaises(frappe.ValidationError):
			_webhook("https://127.0.0.1/hook").validate_endpoint_url_format()

	def test_localhost_raises_when_not_developer_mode(self):
		"""localhost domain is rejected when developer_mode is off."""
		with (
			patch.object(frappe, "conf", frappe._dict(developer_mode=0)),
			self.assertRaises(frappe.ValidationError),
		):
			_webhook("https://localhost/hook").validate_endpoint_url_format()

	def test_local_domain_raises_when_not_developer_mode(self):
		"""*.local domains are rejected when developer_mode is off."""
		with (
			patch.object(frappe, "conf", frappe._dict(developer_mode=0)),
			self.assertRaises(frappe.ValidationError),
		):
			_webhook("https://myapp.local/hook").validate_endpoint_url_format()


# ══════════════════════════════════════════════════════════════════════════════
# validate — event and duplicate guards (mocked DB)
# ══════════════════════════════════════════════════════════════════════════════


class TestPressWebhookValidate(FrappeTestCase):
	"""Tests for PressWebhook.validate() — guards that require DB mocking."""

	def _make(self, endpoint="https://example.com/hook", events=None):
		doc = object.__new__(PressWebhook)
		doc.endpoint = endpoint
		doc.team = "team-1"
		doc.name = "WH-new"
		doc.enabled = 1
		doc.events = events if events is not None else [object()]
		# Simulate a new document (not yet in DB)
		doc.is_new = lambda: True
		doc.has_value_changed = lambda field: False
		return doc

	def test_no_events_raises(self):
		"""validate() raises when events list is empty."""
		doc = self._make(events=[])
		with (
			patch(
				"press.press.doctype.press_webhook.press_webhook.frappe.db.count",
				return_value=0,
			),
			patch(
				"press.press.doctype.press_webhook.press_webhook.frappe.get_all",
				return_value=[],
			),
			self.assertRaises(frappe.ValidationError),
		):
			PressWebhook.validate(doc)

	def test_too_many_webhooks_raises(self):
		"""validate() raises when team already has > 5 webhooks."""
		doc = self._make()
		with (
			patch(
				"press.press.doctype.press_webhook.press_webhook.frappe.db.count",
				return_value=6,
			),
			patch(
				"press.press.doctype.press_webhook.press_webhook.frappe.get_all",
				return_value=[],
			),
			self.assertRaises(frappe.ValidationError),
		):
			PressWebhook.validate(doc)

	def test_duplicate_endpoint_raises(self):
		"""validate() raises when the same endpoint already exists for the team."""
		doc = self._make()
		with (
			patch(
				"press.press.doctype.press_webhook.press_webhook.frappe.db.count",
				return_value=0,
			),
			patch(
				"press.press.doctype.press_webhook.press_webhook.frappe.get_all",
				return_value=["WH-existing"],
			),
			self.assertRaises(frappe.ValidationError),
		):
			PressWebhook.validate(doc)
