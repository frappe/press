# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for press_method_permission/press_method_permission.py.

available_actions() is a pure aggregation function tested with mocked frappe.get_all.
"""

from __future__ import annotations

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_method_permission.press_method_permission import available_actions

_MODULE = "press.press.doctype.press_method_permission.press_method_permission"


class TestAvailableActions(FrappeTestCase):
	"""available_actions() builds a nested dict: {doctype: {label: method}}."""

	def _run(self, doctypes, perms_by_doctype):
		"""Helper: mock get_all for distinct doctypes and then per-doctype perms."""
		call_count = [0]

		def _get_all(doctype, *args, **kwargs):
			if call_count[0] == 0:
				call_count[0] += 1
				return doctypes
			# Subsequent calls return perms for a specific doctype
			doctype_filter = args[0] if args else kwargs.get("filters", {})
			if isinstance(doctype_filter, dict):
				dt = doctype_filter.get("document_type", next(iter(perms_by_doctype.keys())))
			else:
				dt = list(perms_by_doctype.keys())[call_count[0] - 1]
			call_count[0] += 1
			return perms_by_doctype.get(dt, [])

		with patch(f"{_MODULE}.frappe.get_all", side_effect=_get_all):
			return available_actions()

	def test_empty_when_no_permissions_configured(self):
		"""Returns {} when no Press Method Permission records exist."""
		with patch(f"{_MODULE}.frappe.get_all", return_value=[]):
			result = available_actions()
		self.assertEqual(result, {})

	def test_single_doctype_single_action(self):
		"""Returns a dict with one doctype containing one action."""
		doctypes = ["Site"]
		perms = {"Site": [{"checkbox_label": "Restart", "method": "restart"}]}

		def _get_all(doctype, *args, **kwargs):
			if not args and not kwargs:
				return doctypes
			filters = args[0] if args else kwargs.get("filters", {})
			if isinstance(filters, str) and filters == "Site":
				return perms["Site"]
			if isinstance(filters, dict):
				return perms.get(filters.get("document_type", ""), [])
			return perms.get("Site", [])

		with patch(f"{_MODULE}.frappe.get_all", side_effect=_get_all):
			result = available_actions()
		self.assertIn("Site", result)
		self.assertEqual(result["Site"]["Restart"], "restart")

	def test_multiple_actions_for_same_doctype(self):
		"""All actions for a doctype are included in its inner dict."""
		perm_list = [
			{"checkbox_label": "Restart", "method": "restart"},
			{"checkbox_label": "Update", "method": "update"},
		]

		call_no = [0]

		def _ga(doctype, *args, **kwargs):
			if call_no[0] == 0:
				call_no[0] += 1
				return ["Server"]
			call_no[0] += 1
			return perm_list

		with patch(f"{_MODULE}.frappe.get_all", side_effect=_ga):
			result = available_actions()
		self.assertEqual(len(result["Server"]), 2)
		self.assertIn("Restart", result["Server"])
		self.assertIn("Update", result["Server"])

	def test_returns_dict_not_list(self):
		"""The return type must be a dict."""
		with patch(f"{_MODULE}.frappe.get_all", return_value=[]):
			result = available_actions()
		self.assertIsInstance(result, dict)
