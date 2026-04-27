# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import io
import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.test_api import FrappeAPITestCase, make_request


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

		frappe.db.set_single_value("Press Settings", "mailgun_api_key", "test-key")
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

		frappe.db.set_single_value("Press Settings", "mailgun_api_key", "test-key")
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

		frappe.db.set_single_value("Press Settings", "mailgun_api_key", "test-key")
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
