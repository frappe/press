# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch
import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import (
	AlertmanagerWebhookLog,
)

from press.press.doctype.alertmanager_webhook_log.test_alertmanager_webhook_log import (
	create_test_alertmanager_webhook_log,
)
from press.press.doctype.prometheus_alert_rule.test_prometheus_alert_rule import (
	create_test_prometheus_alert_rule,
)
from press.utils.test import foreground_enqueue_doc


@patch(
	"press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log.enqueue_doc",
	new=foreground_enqueue_doc,
)
@patch.object(AlertmanagerWebhookLog, "send_telegram_notification", new=Mock())
class TestPrometheusAlertReaction(FrappeTestCase):
	def test_reaction_gets_created_for_alert_after_duration(self):
		rule = create_test_prometheus_alert_rule("Disk Full")

		reactions_before = frappe.db.count("Prometheus Alert Reaction")
		create_test_alertmanager_webhook_log(rule)
		reactions_after = frappe.db.count("Prometheus Alert Reaction")
		self.assertEqual(reactions_after, reactions_before + 1)
