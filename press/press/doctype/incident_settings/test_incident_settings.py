# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.incident_settings.incident_settings import alert_if_phone_call_alerts_disabled


@patch("press.press.doctype.incident_settings.incident_settings.send_raven_message")
class TestIncidentSettings(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_raven_alert_sent_when_phone_call_alerts_disabled(self, mock_send_raven_message):
		frappe.db.set_single_value("Incident Settings", "phone_call_alerts", 0)
		alert_if_phone_call_alerts_disabled()
		self.assertIn("Phone call alerts are disabled", mock_send_raven_message.call_args[0][0])

	def test_no_raven_alert_when_phone_call_alerts_enabled(self, mock_send_raven_message):
		frappe.db.set_single_value("Incident Settings", "phone_call_alerts", 1)
		alert_if_phone_call_alerts_disabled()
		mock_send_raven_message.assert_not_called()
