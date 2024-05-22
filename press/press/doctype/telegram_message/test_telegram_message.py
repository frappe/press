# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.telegram_message.telegram_message import (
	TelegramMessage,
	send_telegram_message,
)
from press.telegram_utils import Telegram


@patch.object(Telegram, "send")
class TestTelegramMessage(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_enqueue_creates_telegram_message(self, mock_send: Mock):
		"""Test if enqueue method creates Telegram Message"""

		before = frappe.db.count("Telegram Message")
		TelegramMessage.enqueue(message="Test Message")
		after = frappe.db.count("Telegram Message")
		self.assertEqual(after, before + 1)

	def test_enqueue_creates_telegram_message_with_queued_status(self, mock_send: Mock):
		"""Test if enqueue method creates Telegram Message with Queued status"""
		message = TelegramMessage.enqueue(message="Test Message")
		self.assertEqual(message.status, "Queued")

	def test_send_calls_telegram_send(self, mock_send: Mock):
		"""Test if send method calls Telegram send method"""
		TelegramMessage.enqueue(message="Test Message")
		send_telegram_message()
		mock_send.assert_called_once()

	def test_successful_send_call_sets_sent_status(self, mock_send: Mock):
		"""Test if successful send call sets status to Sent"""
		first = TelegramMessage.enqueue(message="Test Message")
		send_telegram_message()
		first.reload()
		self.assertEqual(first.status, "Sent")

	def test_failed_send_call_sets_error_status(self, mock_send: Mock):
		"""Test if failed send call sets status to Error"""
		mock_send.side_effect = Exception()
		first = TelegramMessage.enqueue(message="Test Message")
		self.assertRaises(Exception, TelegramMessage.send_one)
		first.reload()
		self.assertEqual(first.status, "Error")
		self.assertIn("Exception", first.error)
