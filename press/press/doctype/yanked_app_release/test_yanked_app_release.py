# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for yanked_app_release/yanked_app_release.py.

after_insert() marks the parent App Release as Yanked.
on_trash()     restores the parent App Release to Approved.

Both methods delegate entirely to frappe.db.set_value, so they are tested
by patching that call — no real App Release documents are required.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.yanked_app_release.yanked_app_release import YankedAppRelease

_MODULE = "press.press.doctype.yanked_app_release.yanked_app_release"


def _doc(parent: str = "AR-001") -> SimpleNamespace:
	return SimpleNamespace(parent_app_release=parent)


class TestYankedAppReleaseAfterInsert(FrappeTestCase):
	"""after_insert() marks the release as Yanked."""

	def test_sets_invalid_release_flag(self):
		doc = _doc("AR-TEST-1")
		with patch(f"{_MODULE}.frappe.db.set_value") as mock_sv:
			YankedAppRelease.after_insert(doc)
		mock_sv.assert_called_once_with(
			"App Release",
			{"name": "AR-TEST-1"},
			{
				"invalid_release": True,
				"invalidation_reason": "Yanked-Release",
				"status": "Yanked",
			},
		)

	def test_uses_parent_app_release_as_filter(self):
		"""The filter uses parent_app_release, not the YankedAppRelease doc name."""
		doc = _doc("AR-SPECIFIC")
		with patch(f"{_MODULE}.frappe.db.set_value") as mock_sv:
			YankedAppRelease.after_insert(doc)
		_, filter_arg, _ = mock_sv.call_args.args
		self.assertEqual(filter_arg, {"name": "AR-SPECIFIC"})

	def test_status_set_to_yanked(self):
		doc = _doc()
		with patch(f"{_MODULE}.frappe.db.set_value") as mock_sv:
			YankedAppRelease.after_insert(doc)
		_, _, value_arg = mock_sv.call_args.args
		self.assertEqual(value_arg["status"], "Yanked")


class TestYankedAppReleaseOnTrash(FrappeTestCase):
	"""on_trash() restores the release to Approved."""

	def test_restores_to_approved(self):
		doc = _doc("AR-TEST-2")
		with patch(f"{_MODULE}.frappe.db.set_value") as mock_sv:
			YankedAppRelease.on_trash(doc)
		mock_sv.assert_called_once_with(
			"App Release",
			{"name": "AR-TEST-2"},
			{"invalid_release": False, "invalidation_reason": "", "status": "Approved"},
		)

	def test_clears_invalidation_reason(self):
		doc = _doc()
		with patch(f"{_MODULE}.frappe.db.set_value") as mock_sv:
			YankedAppRelease.on_trash(doc)
		_, _, value_arg = mock_sv.call_args.args
		self.assertEqual(value_arg["invalidation_reason"], "")
		self.assertFalse(value_arg["invalid_release"])

	def test_after_insert_and_on_trash_are_inverse(self):
		"""The set_value calls made by after_insert and on_trash are truly inverse operations."""
		doc = _doc("AR-PAIR")
		inserts = []
		trashes = []

		with patch(f"{_MODULE}.frappe.db.set_value", side_effect=lambda *a: inserts.append(a)):
			YankedAppRelease.after_insert(doc)

		with patch(f"{_MODULE}.frappe.db.set_value", side_effect=lambda *a: trashes.append(a)):
			YankedAppRelease.on_trash(doc)

		_, _, insert_vals = inserts[0]
		_, _, trash_vals = trashes[0]
		# after_insert sets invalid_release=True, on_trash sets it back to False
		self.assertTrue(insert_vals["invalid_release"])
		self.assertFalse(trash_vals["invalid_release"])
		self.assertEqual(insert_vals["status"], "Yanked")
		self.assertEqual(trash_vals["status"], "Approved")
