# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for site_config_key_blacklist/site_config_key_blacklist.py.

SiteConfigKeyBlacklist.validate() emits a msgprint when the blacklisted key
is also present as an enabled Site Config Key doc (non-fatal warning).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site_config_key_blacklist.site_config_key_blacklist import (
	SiteConfigKeyBlacklist,
)

_MODULE = "press.press.doctype.site_config_key_blacklist.site_config_key_blacklist"


class TestSiteConfigKeyBlacklistValidate(FrappeTestCase):
	"""validate() warns (msgprint) when an enabled Site Config Key shares the same key."""

	def _doc(self, key: str = "dangerous_key") -> SimpleNamespace:
		return SimpleNamespace(key=key)

	def test_msgprint_called_when_key_exists_in_site_config_key(self):
		"""validate() calls frappe.msgprint when the key already exists as an enabled SCK."""
		doc = self._doc()
		with (
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(frappe, "msgprint") as mock_mp,
		):
			SiteConfigKeyBlacklist.validate(doc)
		mock_mp.assert_called_once()

	def test_msgprint_not_called_when_key_absent_in_site_config_key(self):
		"""validate() is silent when no matching enabled Site Config Key is found."""
		doc = self._doc()
		with (
			patch.object(frappe.db, "exists", return_value=False),
			patch.object(frappe, "msgprint") as mock_mp,
		):
			SiteConfigKeyBlacklist.validate(doc)
		mock_mp.assert_not_called()

	def test_msgprint_includes_key_name(self):
		"""The warning message should mention the key that was found."""
		doc = self._doc(key="rate_limit_num_requests")
		with (
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(frappe, "msgprint") as mock_mp,
		):
			SiteConfigKeyBlacklist.validate(doc)
		call_args = mock_mp.call_args
		msg = call_args.args[0] if call_args.args else ""
		self.assertIn("rate_limit_num_requests", msg)

	def test_validate_does_not_raise(self):
		"""validate() must NOT raise an exception — only emit a warning."""
		doc = self._doc()
		with (
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(frappe, "msgprint"),
		):
			SiteConfigKeyBlacklist.validate(doc)  # must not raise
