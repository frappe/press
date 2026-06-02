# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for log_server/log_server.py.

validate_monitoring_password() and validate_kibana_password() auto-generate
passwords when absent. Tested with mocked frappe.generate_hash().
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.log_server.log_server import LogServer

_MODULE = "press.press.doctype.log_server.log_server"


class TestLogServerValidatePasswords(FrappeTestCase):
	"""validate_monitoring_password / validate_kibana_password auto-generate hashes."""

	def _doc(self, monitoring_password=None, kibana_password=None):
		return SimpleNamespace(
			monitoring_password=monitoring_password,
			kibana_password=kibana_password,
		)

	# ── monitoring_password ──────────────────────────────────────────────────

	def test_monitoring_password_generated_when_absent(self):
		doc = self._doc(monitoring_password=None)
		with patch(f"{_MODULE}.frappe.generate_hash", return_value="mock-hash-mon"):
			LogServer.validate_monitoring_password(doc)
		self.assertEqual(doc.monitoring_password, "mock-hash-mon")

	def test_monitoring_password_preserved_when_set(self):
		doc = self._doc(monitoring_password="existing-secret")
		with patch(f"{_MODULE}.frappe.generate_hash") as mock_gh:
			LogServer.validate_monitoring_password(doc)
		mock_gh.assert_not_called()
		self.assertEqual(doc.monitoring_password, "existing-secret")

	def test_empty_string_monitoring_password_is_replaced(self):
		"""An empty-string password is falsy and should be replaced."""
		doc = self._doc(monitoring_password="")
		with patch(f"{_MODULE}.frappe.generate_hash", return_value="new-hash"):
			LogServer.validate_monitoring_password(doc)
		self.assertEqual(doc.monitoring_password, "new-hash")

	# ── kibana_password ──────────────────────────────────────────────────────

	def test_kibana_password_generated_when_absent(self):
		doc = self._doc(kibana_password=None)
		with patch(f"{_MODULE}.frappe.generate_hash", return_value="mock-hash-kib"):
			LogServer.validate_kibana_password(doc)
		self.assertEqual(doc.kibana_password, "mock-hash-kib")

	def test_kibana_password_preserved_when_set(self):
		doc = self._doc(kibana_password="existing-kib-secret")
		with patch(f"{_MODULE}.frappe.generate_hash") as mock_gh:
			LogServer.validate_kibana_password(doc)
		mock_gh.assert_not_called()
		self.assertEqual(doc.kibana_password, "existing-kib-secret")

	def test_empty_string_kibana_password_is_replaced(self):
		doc = self._doc(kibana_password="")
		with patch(f"{_MODULE}.frappe.generate_hash", return_value="new-kib-hash"):
			LogServer.validate_kibana_password(doc)
		self.assertEqual(doc.kibana_password, "new-kib-hash")
