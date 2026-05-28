# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for site_config_key/site_config_key.py.

SiteConfigKey.validate() has two branches:
 1. Auto-generate title from key when title is absent.
 2. Raise ValidationError when the key is blacklisted (and doc is not internal).
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site_config_key.site_config_key import SiteConfigKey

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _key_doc(**kwargs) -> SiteConfigKey:
	"""Create an in-memory SiteConfigKey doc (not saved to DB)."""
	defaults = {
		"doctype": "Site Config Key",
		"key": "my_config_key",
		"type": "String",
		"internal": 0,
		"title": None,
	}
	defaults.update(kwargs)
	return frappe.get_doc(defaults)


# ══════════════════════════════════════════════════════════════════════════════
# SiteConfigKey.validate — title auto-generation
# ══════════════════════════════════════════════════════════════════════════════


class TestSiteConfigKeyTitleGeneration(FrappeTestCase):
	"""validate() derives a human-readable title from key when title is blank."""

	def test_title_generated_from_underscore_key(self):
		"""Underscores become spaces and the title is Title-Cased."""
		doc = _key_doc(key="my_config_key", title=None)
		SiteConfigKey.validate(doc)
		self.assertEqual(doc.title, "My Config Key")

	def test_title_generated_for_single_word_key(self):
		"""A key with no underscores is just Title-Cased."""
		doc = _key_doc(key="debug", title=None)
		SiteConfigKey.validate(doc)
		self.assertEqual(doc.title, "Debug")

	def test_existing_title_not_overwritten(self):
		"""An explicitly set title must survive validate()."""
		doc = _key_doc(key="my_key", title="Custom Label")
		SiteConfigKey.validate(doc)
		self.assertEqual(doc.title, "Custom Label")

	def test_empty_string_title_is_replaced(self):
		"""An empty string title is treated as missing and auto-generated."""
		doc = _key_doc(key="rate_limit", title="")
		SiteConfigKey.validate(doc)
		self.assertEqual(doc.title, "Rate Limit")


# ══════════════════════════════════════════════════════════════════════════════
# SiteConfigKey.validate — blacklist enforcement
# ══════════════════════════════════════════════════════════════════════════════


class TestSiteConfigKeyBlacklistCheck(FrappeTestCase):
	"""validate() raises when a non-internal key is in the Site Config Key Blacklist."""

	def setUp(self):
		frappe.set_user("Administrator")
		# Insert a blacklist entry that tests can reference
		if not frappe.db.exists("Site Config Key Blacklist", {"key": "blocked_cfg"}):
			frappe.get_doc(
				{
					"doctype": "Site Config Key Blacklist",
					"key": "blocked_cfg",
					"reason": "Used in tests",
				}
			).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_blacklisted_non_internal_key_raises(self):
		"""validate() raises for a blacklisted key when internal=False."""
		doc = _key_doc(key="blocked_cfg", internal=0)
		with self.assertRaises(frappe.ValidationError):
			SiteConfigKey.validate(doc)

	def test_blacklisted_internal_key_does_not_raise(self):
		"""Internal keys bypass the blacklist check."""
		doc = _key_doc(key="blocked_cfg", internal=1)
		SiteConfigKey.validate(doc)  # must not raise

	def test_non_blacklisted_key_does_not_raise(self):
		"""A key not in the blacklist passes regardless of internal flag."""
		doc = _key_doc(key="safe_config_key", internal=0)
		SiteConfigKey.validate(doc)  # must not raise
