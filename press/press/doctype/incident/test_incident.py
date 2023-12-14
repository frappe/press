# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import patch, Mock
import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_press_admin_team


@patch("press.press.doctype.incident.incident.frappe.db.commit", new=Mock())
class MockTwilioClient:
	def __init__(self, account_sid, auth_token):  # noqa
		pass

	@property
	def calls(self):
		return frappe._dict({"create": self.create_call})

	def create_call(self, **kwargs):
		pass


class TestIncident(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value("Press Settings", None, "twilio_account_sid", "test")
		frappe.db.set_value("Press Settings", None, "twilio_auth_token", "test")
		frappe.db.set_value("Press Settings", None, "twilio_phone_number", "test")

		self._create_test_incident_settings()

	def _create_test_incident_settings(self):
		user1 = create_test_press_admin_team().user
		user2 = create_test_press_admin_team().user
		self.test_phno_1 = "+911234567890"
		self.test_phno_2 = "+911234567891"
		frappe.get_doc(
			{
				"doctype": "Incident Settings",
				"users": [
					{
						"user": user1,
						"phone": self.test_phno_1,
					},
					{
						"user": user2,
						"phone": self.test_phno_2,
					},
				],
			}
		).insert()

	def test_incident_gets_created_on_multiple_alerts(self):
		# TODO: update for multiple alerts #
		pass

	@patch.object(MockTwilioClient, "create_call")
	@patch("twilio.rest.Client", new=MockTwilioClient)
	def test_incident_creation_places_phone_call_to_all_humans_in_incident_team(
		self, mock_calls_create: Mock
	):
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
			}
		).insert()
		self.assertEqual(mock_calls_create.call_count, 2)
		mock_calls_create.assert_any_call(
			from_="test",
			to=self.test_phno_1,
			url="http://demo.twilio.com/docs/voice.xml",
		)
		mock_calls_create.assert_any_call(
			from_="test",
			to=self.test_phno_2,
			url="http://demo.twilio.com/docs/voice.xml",
		)
