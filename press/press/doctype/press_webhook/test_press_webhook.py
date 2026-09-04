# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_webhook.press_webhook import auto_disable_high_delivery_failure_webhooks
from press.press.doctype.team.test_team import create_test_press_admin_team


def create_test_webhook(team: str, endpoint: str) -> "frappe.model.document.Document":
	webhook = frappe.get_doc(
		{
			"doctype": "Press Webhook",
			"team": team,
			"endpoint": endpoint,
			"secret": "test-secret",
			"enabled": 1,
			"events": [{"event": "Site Status Update"}],
		}
	).insert(ignore_permissions=True)
	webhook.reload()
	webhook.enabled = 1
	webhook.save(ignore_permissions=True)
	return webhook


def log_delivery_attempts(endpoint: str, statuses: list[str]):
	"""Record delivery attempts for `endpoint`, split across as many Press Webhook Log
	parents as needed, mirroring how PressWebhookLog._send_webhook_call appends them."""
	for status in statuses:
		log = frappe.get_doc(
			{
				"doctype": "Press Webhook Log",
				"event": "Site Status Update",
				"team": frappe.db.get_value("Press Webhook", {"endpoint": endpoint}, "team"),
				"request_payload": "{}",
				"status": "Sent" if status == "Sent" else "Failed",
			}
		)
		log.append(
			"attempts",
			{
				"endpoint": endpoint,
				"webhook": frappe.db.get_value("Press Webhook", {"endpoint": endpoint}, "name"),
				"status": status,
				"response_status_code": 200 if status == "Sent" else 500,
				"response_body": "",
				"timestamp": frappe.utils.now(),
			},
		)
		log.insert(ignore_permissions=True)


class TestPressWebhook(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_single_failed_attempt_does_not_disable_low_volume_webhook(self):
		team = create_test_press_admin_team()
		webhook = create_test_webhook(team.name, "https://example.com/low-volume-webhook")

		# Only one delivery attempt this hour, and it failed — 100% failure rate,
		# but well below the minimum sample size the check requires.
		log_delivery_attempts(webhook.endpoint, ["Failed"])

		auto_disable_high_delivery_failure_webhooks()

		webhook.reload()
		self.assertEqual(
			webhook.enabled,
			1,
			"A single transient failure on a low-volume webhook should not auto-disable it",
		)

	@patch("frappe.sendmail")
	def test_majority_failed_attempts_disables_high_volume_webhook(self, mock_sendmail):
		team = create_test_press_admin_team()
		webhook = create_test_webhook(team.name, "https://example.com/high-volume-webhook")

		# 4 out of 5 attempts failed (80% > 70%), at/above the minimum sample size.
		log_delivery_attempts(webhook.endpoint, ["Failed", "Failed", "Failed", "Failed", "Sent"])

		auto_disable_high_delivery_failure_webhooks()

		webhook.reload()
		self.assertEqual(
			webhook.enabled,
			0,
			"A webhook with a sustained high failure rate over enough attempts should be auto-disabled",
		)
