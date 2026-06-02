# Copyright (c) 2024, Frappe and Contributors
# See license.txt
"""
Tests for site_database_user/site_database_user.py.

validate(), _raise_error_if_archived(), _is_permissions_changed(),
user_addressable_error_from_stacktrace(), and fetch_logs() range guard
are all tested without DB or Agent calls.
"""

from __future__ import annotations

import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.site_database_user.site_database_user import SiteDatabaseUser

_MODULE = "press.press.doctype.site_database_user.site_database_user"


def _doc(**kwargs):
	defaults = dict(
		site="mysite.frappe.cloud",
		label="test user",
		mode="read_only",
		permissions=[],
		max_connections=5,
		status="Active",
		use_replica_server=0,
		user_created_in_database=0,
		user_added_in_proxysql=0,
		username=None,
		password=None,
		team="team1",
	)
	defaults.update(kwargs)
	return SimpleNamespace(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# _raise_error_if_archived
# ══════════════════════════════════════════════════════════════════════════════


class TestRaiseErrorIfArchived(FrappeTestCase):
	def test_raises_when_archived(self):
		doc = _doc(status="Archived")
		with self.assertRaises(frappe.ValidationError):
			SiteDatabaseUser._raise_error_if_archived(doc)

	def test_does_not_raise_when_active(self):
		doc = _doc(status="Active")
		SiteDatabaseUser._raise_error_if_archived(doc)  # must not raise

	def test_does_not_raise_when_pending(self):
		doc = _doc(status="Pending")
		SiteDatabaseUser._raise_error_if_archived(doc)  # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# validate
# ══════════════════════════════════════════════════════════════════════════════


class TestSiteDatabaseUserValidate(FrappeTestCase):
	def _doc_with_hvc(self, hvc=False, **kwargs):
		doc = _doc(**kwargs)
		doc.has_value_changed = MagicMock(return_value=hvc)
		doc.is_new = MagicMock(return_value=False)
		doc._raise_error_if_archived = types.MethodType(SiteDatabaseUser._raise_error_if_archived, doc)
		return doc

	def test_raises_when_max_connections_is_zero(self):
		doc = self._doc_with_hvc(max_connections=0)
		with self.assertRaises(frappe.ValidationError):
			SiteDatabaseUser.validate(doc)

	def test_clears_permissions_when_mode_is_not_granular(self):
		perm = SimpleNamespace(table="tab1", mode="read_only")
		doc = self._doc_with_hvc(mode="read_only", permissions=[perm])
		SiteDatabaseUser.validate(doc)
		self.assertEqual(doc.permissions, [])

	def test_keeps_permissions_when_mode_is_granular(self):
		perm = SimpleNamespace(table="tab1", mode="read_only")
		doc = self._doc_with_hvc(mode="granular", permissions=[perm])
		SiteDatabaseUser.validate(doc)
		self.assertEqual(len(doc.permissions), 1)

	def test_raises_when_max_connections_changed_on_existing_doc(self):
		doc = _doc(max_connections=10)
		doc.has_value_changed = MagicMock(side_effect=lambda f: f == "max_connections")
		doc.is_new = MagicMock(return_value=False)
		doc._raise_error_if_archived = types.MethodType(SiteDatabaseUser._raise_error_if_archived, doc)
		with self.assertRaises(frappe.ValidationError):
			SiteDatabaseUser.validate(doc)

	def test_raises_when_status_is_archived(self):
		doc = self._doc_with_hvc(status="Archived")
		with self.assertRaises(frappe.ValidationError):
			SiteDatabaseUser.validate(doc)


# ══════════════════════════════════════════════════════════════════════════════
# _is_permissions_changed
# ══════════════════════════════════════════════════════════════════════════════


def _perm(table, mode="read_only", allow_all_columns=1, selected_columns=""):
	return SimpleNamespace(
		table=table,
		mode=mode,
		allow_all_columns=allow_all_columns,
		selected_columns=selected_columns,
	)


def _new_perm(table, mode="read_only", allow_all_columns=1, selected_columns=None):
	return {
		"table": table,
		"mode": mode,
		"allow_all_columns": allow_all_columns,
		"selected_columns": selected_columns or [],
	}


class TestIsPermissionsChanged(FrappeTestCase):
	def test_unchanged_when_empty(self):
		doc = _doc(permissions=[])
		self.assertFalse(SiteDatabaseUser._is_permissions_changed(doc, []))

	def test_changed_when_count_differs(self):
		doc = _doc(permissions=[_perm("tab1")])
		self.assertTrue(SiteDatabaseUser._is_permissions_changed(doc, []))

	def test_changed_when_mode_differs(self):
		doc = _doc(permissions=[_perm("tab1", mode="read_only")])
		self.assertTrue(SiteDatabaseUser._is_permissions_changed(doc, [_new_perm("tab1", mode="read_write")]))

	def test_changed_when_allow_all_columns_differs(self):
		doc = _doc(permissions=[_perm("tab1", allow_all_columns=1)])
		self.assertTrue(
			SiteDatabaseUser._is_permissions_changed(doc, [_new_perm("tab1", allow_all_columns=0)])
		)

	def test_unchanged_when_same_permissions(self):
		doc = _doc(permissions=[_perm("tab1", mode="read_only", allow_all_columns=1)])
		self.assertFalse(
			SiteDatabaseUser._is_permissions_changed(
				doc, [_new_perm("tab1", mode="read_only", allow_all_columns=1)]
			)
		)


# ══════════════════════════════════════════════════════════════════════════════
# user_addressable_error_from_stacktrace
# ══════════════════════════════════════════════════════════════════════════════


class TestUserAddressableErrorFromStacktrace(FrappeTestCase):
	def test_returns_default_for_empty_stacktrace(self):
		result = SiteDatabaseUser.user_addressable_error_from_stacktrace("")
		self.assertIn("Unknown error", result)

	def test_returns_default_for_unrecognized_error_code(self):
		stacktrace = 'peewee.OperationalError: (9999, "some unknown error")'
		result = SiteDatabaseUser.user_addressable_error_from_stacktrace(stacktrace)
		self.assertIn("Unknown error", result)

	def test_returns_column_message_for_error_1054(self):
		stacktrace = "peewee.OperationalError: (1054, \"Unknown column 'col1' in 'mytable'\")"
		result = SiteDatabaseUser.user_addressable_error_from_stacktrace(stacktrace)
		self.assertIn("col1", result)
		self.assertIn("mytable", result)

	def test_returns_table_message_for_error_1146(self):
		stacktrace = "peewee.ProgrammingError: (1146, \"Table 'mydb.missing_table' doesn't exist\")"
		result = SiteDatabaseUser.user_addressable_error_from_stacktrace(stacktrace)
		self.assertIn("missing_table", result)

	def test_returns_default_when_1054_pattern_not_matched(self):
		stacktrace = 'peewee.OperationalError: (1054, "malformed message")'
		result = SiteDatabaseUser.user_addressable_error_from_stacktrace(stacktrace)
		self.assertIn("Unknown error", result)


# ══════════════════════════════════════════════════════════════════════════════
# fetch_logs — time range guard
# ══════════════════════════════════════════════════════════════════════════════


class TestFetchLogsRangeGuard(FrappeTestCase):
	def test_raises_when_range_exceeds_30_days(self):
		doc = _doc(username="u1")
		# 31 days in seconds
		start = 0
		end = 31 * 24 * 3600
		with self.assertRaises(frappe.ValidationError):
			SiteDatabaseUser.fetch_logs(doc, start, end)

	def test_returns_empty_when_no_log_server_configured(self):
		doc = _doc(username="u1")
		start = 0
		end = 7 * 24 * 3600  # 7 days
		with patch(f"{_MODULE}.frappe.db.get_single_value", return_value=None):
			result = SiteDatabaseUser.fetch_logs(doc, start, end)
		self.assertEqual(result, [])
