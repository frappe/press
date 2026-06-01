# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for agent_request_failure/agent_request_failure.py.

is_server_archived() is a pure predicate function tested with mocked frappe.db.get_value.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_request_failure.agent_request_failure import is_server_archived

_MODULE = "press.press.doctype.agent_request_failure.agent_request_failure"


def _failure(server_type="Server", server="srv-1"):
	return SimpleNamespace(server_type=server_type, server=server)


class TestIsServerArchived(FrappeTestCase):
	"""is_server_archived() returns True only for servers that have been Archived > 1 hour ago."""

	def test_returns_true_when_archived_over_one_hour_ago(self):
		"""An Archived server modified more than 1 hour ago is considered archived."""
		old_time = datetime.now() - timedelta(hours=2)
		server_info = SimpleNamespace(status="Archived", modified=old_time)
		failure = _failure()
		with (
			patch(f"{_MODULE}.frappe.db.get_value", return_value=server_info),
			patch(f"{_MODULE}.frappe.utils.add_to_date", return_value=datetime.now() - timedelta(hours=1)),
		):
			result = is_server_archived(failure)
		self.assertTrue(result)

	def test_returns_false_when_archived_less_than_one_hour_ago(self):
		"""An Archived server modified less than 1 hour ago is NOT considered fully archived."""
		recent_time = datetime.now() - timedelta(minutes=30)
		server_info = SimpleNamespace(status="Archived", modified=recent_time)
		failure = _failure()
		with (
			patch(f"{_MODULE}.frappe.db.get_value", return_value=server_info),
			patch(f"{_MODULE}.frappe.utils.add_to_date", return_value=datetime.now() - timedelta(hours=1)),
		):
			result = is_server_archived(failure)
		self.assertFalse(result)

	def test_returns_false_when_server_is_active(self):
		"""A server with status != 'Archived' always returns False."""
		old_time = datetime.now() - timedelta(hours=3)
		server_info = SimpleNamespace(status="Active", modified=old_time)
		failure = _failure()
		with (
			patch(f"{_MODULE}.frappe.db.get_value", return_value=server_info),
			patch(f"{_MODULE}.frappe.utils.add_to_date", return_value=datetime.now() - timedelta(hours=1)),
		):
			result = is_server_archived(failure)
		self.assertFalse(result)

	def test_returns_false_when_server_is_pending(self):
		"""A Pending server (not Archived) returns False even if modified long ago."""
		old_time = datetime.now() - timedelta(hours=5)
		server_info = SimpleNamespace(status="Pending", modified=old_time)
		failure = _failure()
		with (
			patch(f"{_MODULE}.frappe.db.get_value", return_value=server_info),
			patch(f"{_MODULE}.frappe.utils.add_to_date", return_value=datetime.now() - timedelta(hours=1)),
		):
			result = is_server_archived(failure)
		self.assertFalse(result)
