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
from telegram.error import TimedOut, RetryAfter


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

	def test_sends_messages_in_priority_order(self, mock_send: Mock):
		"""Test if messages are sent in priority order"""
		high = TelegramMessage.enqueue(message="Test Message", priority="High")
		medium = TelegramMessage.enqueue(message="Test Message", priority="Medium")
		low = TelegramMessage.enqueue(message="Test Message", priority="Low")

		self.assertEqual(TelegramMessage.get_one(), high)
		send_telegram_message()
		self.assertEqual(TelegramMessage.get_one(), medium)
		send_telegram_message()
		self.assertEqual(TelegramMessage.get_one(), low)
		send_telegram_message()

		low = TelegramMessage.enqueue(message="Test Message", priority="Low")
		medium = TelegramMessage.enqueue(message="Test Message", priority="Medium")
		high = TelegramMessage.enqueue(message="Test Message", priority="High")

		self.assertEqual(TelegramMessage.get_one(), high)
		send_telegram_message()
		self.assertEqual(TelegramMessage.get_one(), medium)
		send_telegram_message()
		self.assertEqual(TelegramMessage.get_one(), low)
		send_telegram_message()

	def test_sends_messages_in_creation_order(self, mock_send: Mock):
		"""Test if messages are sent in creation order"""
		first = TelegramMessage.enqueue(message="Test Message")
		second = TelegramMessage.enqueue(message="Test Message")

		self.assertEqual(TelegramMessage.get_one(), first)
		send_telegram_message()
		self.assertEqual(TelegramMessage.get_one(), second)
		send_telegram_message()

	def test_failed_send_network_error_increases_retry(self, mock_send: Mock):
		"""Test if failed send call because of network issues increases retry count"""
		mock_send.side_effect = TimedOut()
		first = TelegramMessage.enqueue(message="Test Message")
		self.assertRaises(TimedOut, TelegramMessage.send_one)
		first.reload()
		self.assertEqual(first.status, "Queued")
		self.assertEqual(first.retry_count, 1)

	def test_test_failed_send_after_max_retries_sets_error_status(self, mock_send: Mock):
		"""Test if failed send call after max_errors sets status to Error"""
		mock_send.side_effect = TimedOut()
		first = TelegramMessage.enqueue(message="Test Message")
		first.retry_count = 4
		first.save()
		self.assertRaises(TimedOut, TelegramMessage.send_one)
		first.reload()
		self.assertEqual(first.status, "Error")

	def test_failed_send_retry_after_doesnt_change_anything(self, mock_send: Mock):
		"""Test if failed send call because of rate limits doesn't change status"""
		mock_send.side_effect = RetryAfter(10)
		first = TelegramMessage.enqueue(message="Test Message")
		self.assertRaises(RetryAfter, TelegramMessage.send_one)
		first.reload()
		self.assertEqual(first.status, "Queued")

	def test_send_message_returns_on_empty_queue(self, mock_send: Mock):
		"""Test if send_telegram_message returns on empty queue"""
		first = TelegramMessage.enqueue(message="Test Message")
		first.status = "Sent"
		first.save()
		send_telegram_message()
		mock_send.assert_not_called()

	def test_send_message_does_not_raise_on_failure(self, mock_send: Mock):
		"""Test if send_telegram_message does not raise on failure"""
		mock_send.side_effect = Exception()
		first = TelegramMessage.enqueue(message="Test Message")
		send_telegram_message()
		first.reload()
		self.assertEqual(first.status, "Error")
		self.assertIn("Exception", first.error)
