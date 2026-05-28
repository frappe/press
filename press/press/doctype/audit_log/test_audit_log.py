# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for audit_log/audit_log.py.

AuditLog.after_insert() — calls notify() only for Failure status.
AuditLog.notify()       — dispatches a TelegramMessage (mocked).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.audit_log.audit_log import AuditLog

_MODULE = "press.press.doctype.audit_log.audit_log"


class TestAuditLogAfterInsert(FrappeTestCase):
	"""after_insert() triggers notification only when status is 'Failure'."""

	def test_notify_called_on_failure(self):
		doc = MagicMock()
		doc.status = "Failure"
		AuditLog.after_insert(doc)
		doc.notify.assert_called_once()

	def test_notify_not_called_on_success(self):
		doc = MagicMock()
		doc.status = "Success"
		AuditLog.after_insert(doc)
		doc.notify.assert_not_called()

	def test_notify_not_called_for_other_statuses(self):
		"""Any status other than 'Failure' must not trigger notify."""
		for status in ("Pending", "Running", ""):
			doc = MagicMock()
			doc.status = status
			AuditLog.after_insert(doc)
			doc.notify.assert_not_called(), f"Unexpected notify() call for status={status!r}"


class TestAuditLogNotify(FrappeTestCase):
	"""notify() sends a Telegram message with the audit log URL and snippet."""

	def _make_doc(self, audit_type="Billing Audit", status="Failure", log="Error details here"):
		doc = MagicMock()
		doc.audit_type = audit_type
		doc.status = status
		doc.log = log
		doc.get_url = lambda: "/app/audit-log/AL-001"
		doc.telegram_topic = "Errors"
		doc.telegram_group = "press-alerts"
		return doc

	@patch(f"{_MODULE}.TelegramMessage")
	@patch(f"{_MODULE}.frappe.get_value", return_value="cloud.example.com")
	def test_telegram_enqueue_called(self, _mock_gv, mock_telegram):
		doc = self._make_doc()
		AuditLog.notify(doc)
		mock_telegram.enqueue.assert_called_once()

	@patch(f"{_MODULE}.TelegramMessage")
	@patch(f"{_MODULE}.frappe.get_value", return_value="cloud.example.com")
	def test_message_contains_audit_type(self, _mock_gv, mock_telegram):
		doc = self._make_doc(audit_type="Server Plan Sanity Check")
		AuditLog.notify(doc)
		msg_kwarg = mock_telegram.enqueue.call_args.kwargs.get(
			"message", mock_telegram.enqueue.call_args.args[0] if mock_telegram.enqueue.call_args.args else ""
		)
		self.assertIn("Server Plan Sanity Check", msg_kwarg)

	@patch(f"{_MODULE}.TelegramMessage")
	@patch(f"{_MODULE}.frappe.get_value", return_value="cloud.example.com")
	def test_group_passed_to_telegram(self, _mock_gv, mock_telegram):
		doc = self._make_doc()
		AuditLog.notify(doc)
		call_kwargs = mock_telegram.enqueue.call_args.kwargs
		self.assertEqual(call_kwargs.get("group"), "press-alerts")

	@patch(f"{_MODULE}.TelegramMessage")
	@patch(f"{_MODULE}.frappe.get_value", return_value="cloud.example.com")
	def test_topic_defaults_to_errors_when_telegram_topic_absent(self, _mock_gv, mock_telegram):
		doc = self._make_doc()
		doc.telegram_topic = None  # falsy — should fall back to "Errors"
		AuditLog.notify(doc)
		call_kwargs = mock_telegram.enqueue.call_args.kwargs
		self.assertEqual(call_kwargs.get("topic"), "Errors")
