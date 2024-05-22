# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
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
