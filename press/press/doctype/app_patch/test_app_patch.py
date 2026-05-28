# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for app_patch/app_patch.py.

validate_bench() raises when the linked bench is not Active.
before_insert() raises when a patch for the same bench already exists.
Both are tested with mocked frappe DB calls — no real Bench documents required.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app_patch.app_patch import AppPatch

_MODULE = "press.press.doctype.app_patch.app_patch"


def _doc(bench="bench-1", patch_name="fix.patch", filename="fix.patch"):
	return SimpleNamespace(bench=bench, patch=patch_name, filename=filename)


# ══════════════════════════════════════════════════════════════════════════════
# AppPatch.validate_bench
# ══════════════════════════════════════════════════════════════════════════════


class TestAppPatchValidateBench(FrappeTestCase):
	"""validate_bench() raises when the bench is not Active."""

	def test_passes_when_bench_is_active(self):
		doc = _doc()
		with patch(f"{_MODULE}.frappe.get_value", return_value="Active"):
			AppPatch.validate_bench(doc)  # must not raise

	def test_raises_when_bench_is_inactive(self):
		doc = _doc()
		with (
			patch(f"{_MODULE}.frappe.get_value", return_value="Inactive"),
			self.assertRaises(frappe.ValidationError),
		):
			AppPatch.validate_bench(doc)

	def test_raises_when_bench_is_archived(self):
		doc = _doc()
		with (
			patch(f"{_MODULE}.frappe.get_value", return_value="Archived"),
			self.assertRaises(frappe.ValidationError),
		):
			AppPatch.validate_bench(doc)

	def test_raises_when_bench_status_is_none(self):
		"""None bench status is not 'Active' → raises."""
		doc = _doc()
		with (
			patch(f"{_MODULE}.frappe.get_value", return_value=None),
			self.assertRaises(frappe.ValidationError),
		):
			AppPatch.validate_bench(doc)


# ══════════════════════════════════════════════════════════════════════════════
# AppPatch.before_insert
# ══════════════════════════════════════════════════════════════════════════════


class TestAppPatchBeforeInsert(FrappeTestCase):
	"""before_insert() raises when a patch for the same bench already exists."""

	def test_raises_when_duplicate_patch_exists(self):
		doc = _doc()
		existing = [{"name": "AP-001", "filename": "fix.patch"}]
		with (
			patch(f"{_MODULE}.frappe.get_all", return_value=existing),
			self.assertRaises(frappe.ValidationError),
		):
			AppPatch.before_insert(doc)

	def test_passes_when_no_duplicate_exists(self):
		doc = _doc()
		with patch(f"{_MODULE}.frappe.get_all", return_value=[]):
			AppPatch.before_insert(doc)  # must not raise
