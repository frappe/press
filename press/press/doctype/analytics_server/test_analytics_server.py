# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for analytics_server/analytics_server.py.

validate_monitoring_password() and validate_plausible_password() auto-generate
passwords when absent. Tested with mocked frappe.generate_hash().
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.analytics_server.analytics_server import AnalyticsServer

_MODULE = "press.press.doctype.analytics_server.analytics_server"


class TestAnalyticsServerValidatePasswords(FrappeTestCase):
	"""validate_monitoring_password / validate_plausible_password auto-generate hashes."""

	def _doc(self, monitoring_password=None, plausible_password=None):
		return SimpleNamespace(
			monitoring_password=monitoring_password,
			plausible_password=plausible_password,
		)

	# ── monitoring_password ──────────────────────────────────────────────────

	def test_monitoring_password_generated_when_absent(self):
		doc = self._doc()
		with patch(f"{_MODULE}.frappe.generate_hash", return_value="mon-hash"):
			AnalyticsServer.validate_monitoring_password(doc)
		self.assertEqual(doc.monitoring_password, "mon-hash")

	def test_monitoring_password_preserved_when_already_set(self):
		doc = self._doc(monitoring_password="existing-mon")
		with patch(f"{_MODULE}.frappe.generate_hash") as mock_gh:
			AnalyticsServer.validate_monitoring_password(doc)
		mock_gh.assert_not_called()
		self.assertEqual(doc.monitoring_password, "existing-mon")

	def test_empty_string_monitoring_password_replaced(self):
		doc = self._doc(monitoring_password="")
		with patch(f"{_MODULE}.frappe.generate_hash", return_value="new-mon"):
			AnalyticsServer.validate_monitoring_password(doc)
		self.assertEqual(doc.monitoring_password, "new-mon")

	# ── plausible_password ───────────────────────────────────────────────────

	def test_plausible_password_generated_when_absent(self):
		doc = self._doc()
		with patch(f"{_MODULE}.frappe.generate_hash", return_value="pla-hash"):
			AnalyticsServer.validate_plausible_password(doc)
		self.assertEqual(doc.plausible_password, "pla-hash")

	def test_plausible_password_preserved_when_already_set(self):
		doc = self._doc(plausible_password="existing-pla")
		with patch(f"{_MODULE}.frappe.generate_hash") as mock_gh:
			AnalyticsServer.validate_plausible_password(doc)
		mock_gh.assert_not_called()
		self.assertEqual(doc.plausible_password, "existing-pla")

	def test_empty_string_plausible_password_replaced(self):
		doc = self._doc(plausible_password="")
		with patch(f"{_MODULE}.frappe.generate_hash", return_value="new-pla"):
			AnalyticsServer.validate_plausible_password(doc)
		self.assertEqual(doc.plausible_password, "new-pla")
