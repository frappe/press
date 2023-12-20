# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import patch, Mock
import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.alertmanager_webhook_log.test_alertmanager_webhook_log import (
	create_test_alertmanager_webhook_log,
)
from press.press.doctype.site.test_site import create_test_site
from press.utils.test import foreground_enqueue_doc


from press.press.doctype.team.test_team import create_test_press_admin_team


class MockTwilioCallList:
	def __init__(self):
		pass

	def create(self, **kwargs):
		return frappe._dict({"sid": "test", "status": self.get_status(), "fetch": self.fetch})

	def fetch(self, **kwargs):
		return frappe._dict({"status": self.get_status()})

	@staticmethod
	def get_status(**kwargs):
		return "queued"


class MockTwilioClient:
	def __init__(self, *args, **kwargs):
		pass

	@property
	def calls(self):
		return MockTwilioCallList()


@patch("press.press.doctype.incident.incident.frappe.db.commit", new=Mock())
class TestIncident(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value("Press Settings", None, "twilio_account_sid", "test")
		frappe.db.set_value("Press Settings", None, "twilio_api_key_sid", "test")
		frappe.db.set_value("Press Settings", None, "twilio_api_key_secret", "test")
		frappe.db.set_value("Press Settings", None, "twilio_phone_number", "test")

		self._create_test_incident_settings()

	def tearDown(self):
		frappe.db.rollback()

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

	@patch(
		"press.press.doctype.incident.incident.frappe.enqueue_doc", new=foreground_enqueue_doc
	)
	@patch("press.press.doctype.incident.incident.Incident.wait_for_pickup", new=Mock())
	@patch.object(
		MockTwilioCallList,
		"create",
	)
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_incident_creation_places_phone_call_to_all_humans_in_incident_team_if_no_one_picks_up(
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

	@patch(
		"press.press.doctype.incident.incident.frappe.enqueue_doc", new=foreground_enqueue_doc
	)
	@patch("tenacity.nap.time", new=Mock())  # no sleep
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_incident_creation_calls_only_one_person_if_first_person_picks_up(self):
		with patch.object(
			MockTwilioCallList, "get_status", return_value="completed"
		) as mock_get_status:
			frappe.get_doc(
				{
					"doctype": "Incident",
					"alertname": "Test Alert",
				}
			).insert()
			self.assertEqual(mock_get_status.call_count, 2)  # during creation and fetch

	@patch("press.press.doctype.incident.incident.Incident.wait_for_pickup", new=Mock())
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_incident_gets_created_on_alert_that_meets_conditions(self):
		incident_count = frappe.db.count("Incident")
		create_test_alertmanager_webhook_log()
		self.assertEqual(frappe.db.count("Incident") - incident_count, 1)

	def test_incident_not_created_when_sites_very_less_than_scope_is_down(self):
		"""1 out of 3 sites on server down"""
		incident_count_before = frappe.db.count("Incident")
		site = create_test_site()
		create_test_site(server=site.server)
		create_test_site(server=site.server)
		create_test_alertmanager_webhook_log(site=site)
		self.assertEqual(frappe.db.count("Incident"), incident_count_before)

	def test_incident_created_when_sites_within_scope_is_down(self):
		"""3 out of 3 sites on server down"""
		incident_count_before = frappe.db.count("Incident")
		site = create_test_site()
		site2 = create_test_site(server=site.server)
		site3 = create_test_site(server=site.server)
		create_test_alertmanager_webhook_log(site=site)
		create_test_alertmanager_webhook_log(site=site2)
		create_test_alertmanager_webhook_log(site=site3)
		self.assertEqual(frappe.db.count("Incident") - incident_count_before, 1)

	@patch(
		"press.press.doctype.incident.incident.frappe.enqueue_doc", new=foreground_enqueue_doc
	)
	@patch("tenacity.nap.time", new=Mock())  # no sleep
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_call_event_creates_acknowledgement_update(self):
		with patch.object(MockTwilioCallList, "get_status", new=lambda self: "completed"):
			incident = frappe.get_doc(
				{
					"doctype": "Incident",
					"alertname": "Test Alert",
				}
			).insert()
			incident.reload()
			self.assertEqual(len(incident.updates), 1)
		with patch.object(MockTwilioCallList, "get_status", new=lambda self: "no-answer"):
			incident = frappe.get_doc(
				{
					"doctype": "Incident",
					"alertname": "Test Alert",
				}
			).insert()
			incident.reload()
			self.assertEqual(len(incident.updates), 2)
