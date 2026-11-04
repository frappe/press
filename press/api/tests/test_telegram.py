# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import json
from unittest.mock import Mock, patch

import frappe
import requests
import responses
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request
from frappe.utils.password import set_encrypted_password

from press.api.telegram import hook
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.telegram_group.test_telegram_group import create_test_telegram_group
from press.telegram_utils import (
	HELP_MESSAGE,
	NetworkError,
	RetryAfter,
	Telegram,
	TelegramError,
)

SECRET = "correct-secret"  # pragma: allowlist secret
MESSAGE = {"chat": {"id": "1"}, "text": "@bot ping", "entities": []}
SEND_MESSAGE_URL = "https://api.telegram.org/botsettings-token/sendMessage"


@patch.object(Telegram, "respond")
class TestTelegramHook(FrappeTestCase):
	def setUp(self):
		set_encrypted_password("Press Settings", "Press Settings", SECRET, "telegram_webhook_secret")

	def tearDown(self):
		frappe.local.request = None
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def call_hook(self, headers: dict):
		set_request(method="POST", headers=headers)
		hook(message=MESSAGE)

	def test_hook_rejects_request_without_secret_token_header(self, respond: Mock):
		with self.assertRaisesRegex(frappe.AuthenticationError, "Invalid Telegram secret token"):
			self.call_hook({})
		respond.assert_not_called()

	def test_hook_rejects_request_with_wrong_secret_token(self, respond: Mock):
		with self.assertRaisesRegex(frappe.AuthenticationError, "Invalid Telegram secret token"):
			self.call_hook({"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"})
		respond.assert_not_called()

	def test_hook_rejects_every_request_when_no_secret_is_configured(self, respond: Mock):
		frappe.db.delete("__Auth", {"doctype": "Press Settings", "fieldname": "telegram_webhook_secret"})
		with self.assertRaisesRegex(frappe.AuthenticationError, "Invalid Telegram secret token"):
			self.call_hook({"X-Telegram-Bot-Api-Secret-Token": ""})
		respond.assert_not_called()

	def test_hook_responds_to_request_with_matching_secret_token(self, respond: Mock):
		self.call_hook({"X-Telegram-Bot-Api-Secret-Token": SECRET})
		respond.assert_called_once_with(MESSAGE)


class TestTelegramToken(FrappeTestCase):
	def setUp(self):
		set_encrypted_password("Press Settings", "Press Settings", "settings-token", "telegram_bot_token")

	def tearDown(self):
		frappe.db.rollback()

	def test_telegram_uses_decrypted_token_of_its_group(self):
		group = create_test_telegram_group(token="group-token")
		self.assertEqual(Telegram(group=group.name).token, "group-token")

	def test_telegram_falls_back_to_decrypted_press_settings_token_when_group_has_none(self):
		group = create_test_telegram_group()
		self.assertEqual(Telegram(group=group.name).token, "settings-token")


class TestTelegramProcess(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_process_refuses_set_on_doctype_outside_allowlist(self):
		team = create_test_team()
		response = Telegram().process(f"team {team.name} set monthly_alert_threshold 42")
		self.assertEqual(response, HELP_MESSAGE)
		self.assertEqual(frappe.db.get_value("Team", team.name, "monthly_alert_threshold"), 0)

	def test_process_refuses_get_password_on_allowed_doctype(self):
		response = Telegram().process("server f1.frappe.cloud execute get_password agent_password")
		self.assertEqual(response, "Reading passwords is not allowed")


class TestTelegramCall(FrappeTestCase):
	def setUp(self):
		set_encrypted_password("Press Settings", "Press Settings", "settings-token", "telegram_bot_token")

	def tearDown(self):
		frappe.db.rollback()

	def reply(self, status: int, body: dict):
		responses.add(responses.POST, SEND_MESSAGE_URL, json=body, status=status)

	@responses.activate
	def test_send_posts_message_to_bot_api_without_empty_parameters(self):
		self.reply(200, {"ok": True, "result": {"message_id": 7}})
		result = Telegram().send("hello", html=True, reraise=True)
		self.assertEqual(result, {"message_id": 7})
		body = json.loads(responses.calls[0].request.body)
		self.assertEqual(body["text"], "hello")
		self.assertEqual(body["parse_mode"], "HTML")
		self.assertNotIn("message_thread_id", body)

	@responses.activate
	def test_send_raises_retry_after_when_telegram_rate_limits(self):
		self.reply(429, {"ok": False, "description": "Too Many Requests", "parameters": {"retry_after": 9}})
		with self.assertRaises(RetryAfter) as context:
			Telegram().send("hello", reraise=True)
		self.assertEqual(context.exception.retry_after, 9)

	@responses.activate
	def test_send_raises_network_error_on_server_error_without_json(self):
		responses.add(responses.POST, SEND_MESSAGE_URL, body="Bad Gateway", status=502)
		with self.assertRaisesRegex(NetworkError, r"Unknown error \(502\)"):
			Telegram().send("hello", reraise=True)

	@responses.activate
	def test_send_raises_network_error_without_token_when_connection_fails(self):
		error = requests.ConnectionError(f"Max retries exceeded with url: {SEND_MESSAGE_URL}")
		responses.add(responses.POST, SEND_MESSAGE_URL, body=error)
		with self.assertRaisesRegex(NetworkError, "Max retries exceeded") as context:
			Telegram().send("hello", reraise=True)
		self.assertNotIn("settings-token", str(context.exception))

	@responses.activate
	def test_send_raises_non_retryable_error_for_unauthorized_token(self):
		self.reply(401, {"ok": False, "description": "Unauthorized"})
		with self.assertRaisesRegex(TelegramError, r"Unauthorized \(401\)") as context:
			Telegram().send("hello", reraise=True)
		self.assertNotIsInstance(context.exception, NetworkError)
