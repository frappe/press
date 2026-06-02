# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for bench_update/bench_update.py.

The validation methods are tested with mocked Frappe DB calls so that no real
Release Group / Site / BenchUpdate documents are required.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.bench_update.bench_update import BenchUpdate

_MODULE = "press.press.doctype.bench_update.bench_update"

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _bench_update_doc(group="rg-1", sites=None, is_inplace=False):
	return SimpleNamespace(
		group=group,
		sites=sites or [],
		is_inplace_update=is_inplace,
		is_new=lambda: True,
		validate_pending_updates=BenchUpdate.validate_pending_updates,
		validate_pending_site_updates=BenchUpdate.validate_pending_site_updates,
		validate_inplace_update=BenchUpdate.validate_inplace_update,
	)


def _site(name: str) -> SimpleNamespace:
	return SimpleNamespace(site=name)


# ══════════════════════════════════════════════════════════════════════════════
# validate_pending_updates
# ══════════════════════════════════════════════════════════════════════════════


class TestBenchUpdateValidatePendingUpdates(FrappeTestCase):
	"""validate_pending_updates() raises when the release group already has a deploy in progress."""

	def test_raises_when_deploy_in_progress(self):
		doc = _bench_update_doc()
		rg_mock = MagicMock()
		rg_mock.deploy_in_progress = True
		with (
			patch(f"{_MODULE}.frappe.get_doc", return_value=rg_mock),
			self.assertRaises(frappe.ValidationError),
		):
			BenchUpdate.validate_pending_updates(doc)

	def test_passes_when_no_deploy_in_progress(self):
		doc = _bench_update_doc()
		rg_mock = MagicMock()
		rg_mock.deploy_in_progress = False
		with patch(f"{_MODULE}.frappe.get_doc", return_value=rg_mock):
			BenchUpdate.validate_pending_updates(doc)  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# validate_pending_site_updates
# ══════════════════════════════════════════════════════════════════════════════


class TestBenchUpdateValidatePendingSiteUpdates(FrappeTestCase):
	"""validate_pending_site_updates() raises when any site has a Pending/Running update."""

	def test_raises_when_site_has_pending_update(self):
		doc = _bench_update_doc(sites=[_site("site-1")])
		with (
			patch(f"{_MODULE}.frappe.db.exists", return_value=True),
			self.assertRaises(frappe.ValidationError),
		):
			BenchUpdate.validate_pending_site_updates(doc)

	def test_passes_when_no_pending_updates(self):
		doc = _bench_update_doc(sites=[_site("site-1"), _site("site-2")])
		with patch(f"{_MODULE}.frappe.db.exists", return_value=False):
			BenchUpdate.validate_pending_site_updates(doc)  # must not raise

	def test_passes_when_no_sites(self):
		doc = _bench_update_doc(sites=[])
		BenchUpdate.validate_pending_site_updates(doc)  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# validate_inplace_update
# ══════════════════════════════════════════════════════════════════════════════


class TestBenchUpdateValidateInplaceUpdate(FrappeTestCase):
	"""validate_inplace_update() raises when sites span multiple benches or no site is selected."""

	def test_raises_when_no_sites_selected(self):
		doc = _bench_update_doc(sites=[], is_inplace=True)
		with self.assertRaises(frappe.ValidationError):
			BenchUpdate.validate_inplace_update(doc)

	def test_raises_when_sites_span_multiple_benches(self):
		doc = _bench_update_doc(sites=[_site("site-1"), _site("site-2")], is_inplace=True)
		with (
			patch(f"{_MODULE}.frappe.get_all", return_value=["bench-A", "bench-B"]),
			self.assertRaises(frappe.ValidationError),
		):
			BenchUpdate.validate_inplace_update(doc)

	def test_passes_when_all_sites_on_same_bench(self):
		doc = _bench_update_doc(sites=[_site("site-1"), _site("site-2")], is_inplace=True)
		with patch(f"{_MODULE}.frappe.get_all", return_value=["bench-A", "bench-A"]):
			BenchUpdate.validate_inplace_update(doc)  # must not raise

	def test_passes_for_single_site(self):
		doc = _bench_update_doc(sites=[_site("site-1")], is_inplace=True)
		with patch(f"{_MODULE}.frappe.get_all", return_value=["bench-A"]):
			BenchUpdate.validate_inplace_update(doc)  # must not raise
