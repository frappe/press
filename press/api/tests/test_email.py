# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import io
import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.test_api import FrappeAPITestCase, make_request
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request
from frappe.utils.password import set_encrypted_password

from press.api.email import event_log, sign_mailgun_event


# The request runs on another connection, so it does not see an uncommitted key
@patch("press.api.email.get_decrypted_password", new=Mock(return_value="test-key"))
class TestSendMimeMail(FrappeAPITestCase):
	"""Test send_mime_mail endpoint with the same parameters email_delivery_service uses."""

	ENDPOINT = "/api/method/press.api.email.send_mime_mail"

	def _post_mime_mail(
		self,
		data: dict,
		mime_content: bytes = b"MIME-Version: 1.0\r\nContent-Type: text/plain\r\n\r\nTest email body",
	):
		"""Send a multipart form request with a MIME file, matching email_delivery_service.

		The email_delivery_service app sends:
		requests.post(url, data={"data": json.dumps(data)}, files={"mime": msg})
		"""
		return make_request(
			target=self.TEST_CLIENT.post,
			args=(self.ENDPOINT,),
			kwargs={
				"data": {
					"data": json.dumps(data),
					"mime": (io.BytesIO(mime_content), "message.eml"),
				},
				"content_type": "multipart/form-data",
				"buffered": True,
			},
		)

	@patch("press.api.email.validate_plan")
	@patch("press.api.email.check_spam")
	@patch("press.api.email.requests.post")
	def test_send_mime_mail_success(self, mock_mailgun_post, mock_check_spam, mock_validate_plan):
		"""Test that send_mime_mail correctly parses the data parameter as a JSON string,
		using the same request format as email_delivery_service."""
		mock_mailgun_response = Mock()
		mock_mailgun_response.status_code = 200
		mock_mailgun_post.return_value = mock_mailgun_response

		frappe.db.set_single_value("Press Settings", "root_domain", "example.com")

		data = {
			"sender": "sender@example.com",
			"recipients": "recipient@example.com",
			"sk_mail": "test-secret-key",
			"site": "test.frappe.cloud",
		}
		mime_content = b"MIME-Version: 1.0\r\nContent-Type: text/plain\r\n\r\nTest email body"

		response = self._post_mime_mail(data, mime_content)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json["message"], "Sending")

		mock_validate_plan.assert_called_once_with("test-secret-key")
		mock_check_spam.assert_called_once_with(mime_content)
		mock_mailgun_post.assert_called_once()

		call_kwargs = mock_mailgun_post.call_args
		self.assertEqual(call_kwargs.kwargs["data"]["to"], "recipient@example.com")
		self.assertEqual(call_kwargs.kwargs["data"]["v:sk_mail"], "test-secret-key")

	@patch("press.api.email.validate_plan")
	@patch("press.api.email.check_spam", new=Mock())
	@patch("press.api.email.requests.post")
	def test_send_mime_mail_parses_json_string_data(self, mock_mailgun_post, mock_validate_plan):
		"""Verify the data parameter is correctly parsed as a JSON string (not a dict)."""
		mock_mailgun_response = Mock()
		mock_mailgun_response.status_code = 200
		mock_mailgun_post.return_value = mock_mailgun_response

		frappe.db.set_single_value("Press Settings", "root_domain", "example.com")

		data = {
			"sender": "test@site.com",
			"recipients": "user@domain.com",
			"sk_mail": "sk-12345",
			"site": "mysite.frappe.cloud",
		}

		response = self._post_mime_mail(data)

		self.assertEqual(response.status_code, 200)
		# Verify validate_plan received the correct sk_mail from the parsed JSON
		mock_validate_plan.assert_called_once_with("sk-12345")

	@patch("press.api.email.validate_plan", new=Mock())
	@patch("press.api.email.check_spam", new=Mock())
	def test_send_mime_mail_mailgun_400_error(self):
		"""Test that a 400 response from mailgun raises InvalidEmail."""

		frappe.db.set_single_value("Press Settings", "root_domain", "example.com")

		data = {
			"sender": "sender@example.com",
			"recipients": "invalid",
			"sk_mail": "test-secret-key",
			"site": "test.frappe.cloud",
		}

		response = self._post_mime_mail(data)

		self.assertIn(response.status_code, (400, 417))

	def test_email_ping(self):
		"""Test the email_ping endpoint."""
		response = self.get(self.method("press.api.email.email_ping"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json["message"], "pong")


SIGNING_KEY = "test-signing-key"  # pragma: allowlist secret


def make_mailgun_event(secret_key: str, signing_key: str = SIGNING_KEY) -> dict:
	signature = {"timestamp": "1700000000", "token": frappe.generate_hash()}
	signature["signature"] = sign_mailgun_event(signing_key, signature)
	return {
		"signature": signature,
		"event-data": {
			"event": "delivered",
			"user-variables": {"sk_mail": secret_key},
			"message": {"headers": {"message-id": "a@attacker.example", "from": "a@b.com", "to": "c@d.com"}},
			"delivery-status": {"message": "OK", "description": ""},
		},
	}


@patch("press.api.email.requests.post")
@patch.object(frappe.db, "commit", new=Mock())
class TestEventLog(FrappeTestCase):
	def setUp(self):
		set_encrypted_password("Press Settings", "Press Settings", SIGNING_KEY, "mailgun_webhook_signing_key")
		self.secret_key = frappe.generate_hash()
		self.site = f"{frappe.generate_hash(length=8)}.frappe.cloud"
		frappe.get_doc(
			{
				"doctype": "Subscription",
				"name": frappe.generate_hash(),
				"secret_key": self.secret_key,
				"site": self.site,
			}
		).db_insert()

	def tearDown(self):
		frappe.local.request = None
		frappe.db.rollback()

	def call_event_log(self, event: dict):
		set_request(method="POST", data=json.dumps(event), content_type="application/json")
		return event_log()

	def assert_rejected(self, event: dict, post: Mock):
		with self.assertRaisesRegex(frappe.AuthenticationError, "Invalid Mailgun signature"):
			self.call_event_log(event)
		self.assertFalse(frappe.db.exists("Mail Log", {"subscription_key": self.secret_key}))
		post.assert_not_called()

	def test_event_log_rejects_event_without_signature(self, post: Mock):
		event = make_mailgun_event(self.secret_key)
		del event["signature"]
		self.assert_rejected(event, post)

	def test_event_log_rejects_event_signed_with_another_key(self, post: Mock):
		self.assert_rejected(make_mailgun_event(self.secret_key, signing_key="other-key"), post)

	def test_event_log_rejects_every_event_when_no_signing_key_is_set(self, post: Mock):
		frappe.db.delete("__Auth", {"doctype": "Press Settings", "fieldname": "mailgun_webhook_signing_key"})
		self.assert_rejected(make_mailgun_event(self.secret_key), post)

	def test_event_log_logs_signed_event_and_forwards_it_to_the_subscription_site(self, post: Mock):
		self.call_event_log(make_mailgun_event(self.secret_key))
		self.assertEqual(
			frappe.db.get_value("Mail Log", {"subscription_key": self.secret_key}, "site"), self.site
		)
		self.assertTrue(post.call_args.args[0].startswith(f"https://{self.site}/"))
		self.assertEqual(post.call_args.kwargs["timeout"], 5)

	def test_event_log_ignores_signed_event_whose_key_matches_no_subscription(self, post: Mock):
		self.call_event_log(make_mailgun_event("unknown-key"))
		self.assertFalse(frappe.db.exists("Mail Log", {"subscription_key": "unknown-key"}))
		post.assert_not_called()
