# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for usage_record/usage_record.py.

UsageRecord.validate() sets date/time defaults.
validate_duplicate_usage_record() prevents duplicate submitted records.

Both are tested with mocked DB calls so that no real Subscription / Invoice
documents are needed.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.usage_record.usage_record import UsageRecord

_MODULE = "press.press.doctype.usage_record.usage_record"

# ══════════════════════════════════════════════════════════════════════════════
# UsageRecord.validate — date / time defaults
# ══════════════════════════════════════════════════════════════════════════════


class TestUsageRecordValidate(FrappeTestCase):
	"""validate() sets sensible defaults for date and time."""

	def _doc(self, date=None, time=None) -> SimpleNamespace:
		return SimpleNamespace(date=date, time=time)

	def test_date_defaults_to_today_when_absent(self):
		doc = self._doc(date=None, time="12:00:00")
		with patch(f"{_MODULE}.frappe.utils.today", return_value="2026-01-01"):
			UsageRecord.validate(doc)
		self.assertEqual(doc.date, "2026-01-01")

	def test_time_defaults_to_nowtime_when_absent(self):
		doc = self._doc(date="2026-01-01", time=None)
		with patch(f"{_MODULE}.frappe.utils.nowtime", return_value="09:30:00"):
			UsageRecord.validate(doc)
		self.assertEqual(doc.time, "09:30:00")

	def test_explicit_date_not_overwritten(self):
		doc = self._doc(date="2025-06-15", time="10:00:00")
		UsageRecord.validate(doc)
		self.assertEqual(doc.date, "2025-06-15")

	def test_explicit_time_not_overwritten(self):
		doc = self._doc(date="2025-06-15", time="08:00:00")
		UsageRecord.validate(doc)
		self.assertEqual(doc.time, "08:00:00")

	def test_both_defaults_set_when_both_absent(self):
		doc = self._doc(date=None, time=None)
		with (
			patch(f"{_MODULE}.frappe.utils.today", return_value="2026-03-01"),
			patch(f"{_MODULE}.frappe.utils.nowtime", return_value="14:00:00"),
		):
			UsageRecord.validate(doc)
		self.assertEqual(doc.date, "2026-03-01")
		self.assertEqual(doc.time, "14:00:00")


# ══════════════════════════════════════════════════════════════════════════════
# UsageRecord.validate_duplicate_usage_record
# ══════════════════════════════════════════════════════════════════════════════


class TestUsageRecordValidateDuplicate(FrappeTestCase):
	"""validate_duplicate_usage_record() raises DuplicateEntryError for duplicates."""

	def _make_doc(self, document_type="Site", is_primary=True) -> SimpleNamespace:
		return SimpleNamespace(
			name="UR-new",
			team="team-1",
			document_type=document_type,
			document_name="doc-1",
			interval="Daily",
			date="2026-01-01",
			plan="plan-1",
			subscription="sub-1",
			amount=100.0,
		)

	def test_duplicate_site_record_raises(self):
		"""A duplicate submitted Usage Record for a Site raises DuplicateEntryError."""
		doc = self._make_doc(document_type="Site")
		with (
			patch(f"{_MODULE}.frappe.get_all", return_value=["UR-existing"]),
			self.assertRaises(frappe.DuplicateEntryError),
		):
			UsageRecord.validate_duplicate_usage_record(doc)

	def test_no_duplicate_passes(self):
		"""When no duplicate exists, validate_duplicate_usage_record() is a no-op."""
		doc = self._make_doc(document_type="Site")
		with patch(f"{_MODULE}.frappe.get_all", return_value=[]):
			UsageRecord.validate_duplicate_usage_record(doc)  # must not raise

	def test_non_primary_server_skips_duplicate_check(self):
		"""For Server documents, the check is skipped when is_primary=False."""
		doc = self._make_doc(document_type="Server")
		with (
			patch(f"{_MODULE}.frappe.db.get_value", return_value=0),  # is_primary=False
			patch(f"{_MODULE}.frappe.get_all", return_value=["UR-dup"]) as mock_ga,
		):
			# Should NOT raise — primary check bails early
			UsageRecord.validate_duplicate_usage_record(doc)
		# get_all must not have been called (the function returned early)
		mock_ga.assert_not_called()

	def test_primary_server_does_check(self):
		"""For a primary Server document, the duplicate check runs normally."""
		doc = self._make_doc(document_type="Server")
		with (
			patch(f"{_MODULE}.frappe.db.get_value", return_value=1),  # is_primary=True
			patch(f"{_MODULE}.frappe.get_all", return_value=["UR-dup"]),
			self.assertRaises(frappe.DuplicateEntryError),
		):
			UsageRecord.validate_duplicate_usage_record(doc)
