# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import patch, Mock
import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import (
	AlertmanagerWebhookLog,
)
from press.press.doctype.alertmanager_webhook_log.test_alertmanager_webhook_log import (
	create_test_alertmanager_webhook_log,
)
from press.press.doctype.site.test_site import create_test_site
from press.utils.test import foreground_enqueue_doc


from press.press.doctype.team.test_team import create_test_press_admin_team


class MockTwilioCallInstance:
	def __init__(self, sid="test", status="queued"):
		self.sid = sid
		self.status = status

	def fetch(self):
		return self


class MockTwilioCallList:
	def __init__(self, status="queued", *args, **kwargs):
		self.status = status

	def create(self, *args, **kwargs):
		return MockTwilioCallInstance(status=self.status)


class MockTwilioMessageInstance:
	def __init__(self, *args, **kwargs):
		pass


class MockTwilioMessageList:
	def __init__(self, *args, **kwargs):
		pass

	def create(self, *args, **kwargs):
		return MockTwilioMessageInstance()


class MockTwilioClient:
	def __init__(self, *args, **kwargs):
		pass

	@property
	def calls(self):
		return MockTwilioCallList()

	@property
	def messages(self):
		return MockTwilioMessageList()


@patch(
	"press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log.enqueue_doc",
	new=foreground_enqueue_doc,
)
@patch.object(AlertmanagerWebhookLog, "send_telegram_notification", new=Mock())
@patch("press.press.doctype.incident.incident.frappe.db.commit", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestIncident(FrappeTestCase):
	def setUp(self):
		self.from_ = "+911234567892"
		frappe.db.set_value("Press Settings", None, "twilio_account_sid", "test")
		frappe.db.set_value("Press Settings", None, "twilio_api_key_sid", "test")
		frappe.db.set_value("Press Settings", None, "twilio_api_key_secret", "test")
		frappe.db.set_value("Press Settings", None, "twilio_phone_number", self.from_)

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

	@patch("press.press.doctype.incident.incident.enqueue_doc", new=foreground_enqueue_doc)
	@patch("tenacity.nap.time", new=Mock())  # no sleep
	@patch.object(
		MockTwilioCallList,
		"create",
		wraps=MockTwilioCallList("busy").create,
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
		).insert().call_humans()
		self.assertEqual(mock_calls_create.call_count, 2)
		mock_calls_create.assert_any_call(
			from_=self.from_,
			to=self.test_phno_1,
			url="http://demo.twilio.com/docs/voice.xml",
		)
		mock_calls_create.assert_any_call(
			from_=self.from_,
			to=self.test_phno_2,
			url="http://demo.twilio.com/docs/voice.xml",
		)

	@patch("press.press.doctype.incident.incident.enqueue_doc", new=foreground_enqueue_doc)
	@patch("tenacity.nap.time", new=Mock())  # no sleep
	@patch.object(
		MockTwilioCallList, "create", wraps=MockTwilioCallList("completed").create
	)
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_incident_calls_only_one_person_if_first_person_picks_up(
		self, mock_calls_create: Mock
	):
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
			}
		).insert().call_humans()
		self.assertEqual(mock_calls_create.call_count, 1)

	@patch("press.press.doctype.incident.incident.enqueue_doc", new=foreground_enqueue_doc)
	@patch("tenacity.nap.time", new=Mock())  # no sleep
	@patch.object(
		MockTwilioCallList, "create", wraps=MockTwilioCallList("completed").create
	)
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_incident_calls_stop_for_in_progress_state(self, mock_calls_create):
		incident = frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
			}
		).insert()
		incident.call_humans()
		self.assertEqual(mock_calls_create.call_count, 1)
		incident.reload()
		self.assertEqual(len(incident.updates), 1)

	@patch("press.press.doctype.incident.incident.enqueue_doc", new=foreground_enqueue_doc)
	@patch("tenacity.nap.time", new=Mock())  # no sleep
	@patch.object(MockTwilioCallList, "create", wraps=MockTwilioCallList("ringing").create)
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_incident_calls_next_person_after_retry_limit(self, mock_calls_create):
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
			}
		).insert().call_humans()
		self.assertEqual(mock_calls_create.call_count, 2)

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

	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
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

	@patch("press.press.doctype.incident.incident.enqueue_doc", new=foreground_enqueue_doc)
	@patch("tenacity.nap.time", new=Mock())  # no sleep
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_call_event_creates_acknowledgement_update(self):
		with patch.object(
			MockTwilioCallList, "create", new=MockTwilioCallList("completed").create
		):
			incident = frappe.get_doc(
				{
					"doctype": "Incident",
					"alertname": "Test Alert",
				}
			).insert()
			incident.call_humans()
			incident.reload()
			self.assertEqual(len(incident.updates), 1)
		with patch.object(
			MockTwilioCallList, "create", new=MockTwilioCallList("no-answer").create
		):
			incident = frappe.get_doc(
				{
					"doctype": "Incident",
					"alertname": "Test Alert",
				}
			).insert()
			incident.call_humans()
			incident.reload()
			self.assertEqual(len(incident.updates), 2)

	@patch("press.press.doctype.incident.incident.enqueue_doc", new=foreground_enqueue_doc)
	@patch("tenacity.nap.time", new=Mock())  # no sleep
	@patch.object(
		MockTwilioCallList, "create", wraps=MockTwilioCallList("completed").create
	)
	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_global_phone_call_alerts_disabled_wont_create_phone_calls(
		self, mock_calls_create
	):
		frappe.db.set_value("Incident Settings", None, "phone_call_alerts", 0)
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
			}
		).insert()
		mock_calls_create.assert_not_called()

	@patch(
		"press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient
	)
	def test_duplicate_incidents_arent_created_for_same_alert(self):
		incident_count_before = frappe.db.count("Incident")
		site = create_test_site()
		site2 = create_test_site(server=site.server)
		create_test_alertmanager_webhook_log(site=site)
		create_test_alertmanager_webhook_log(site=site2)
		self.assertEqual(frappe.db.count("Incident") - 1, incident_count_before)
		site3 = create_test_site()  # new server
		create_test_alertmanager_webhook_log(site=site3)
		self.assertEqual(frappe.db.count("Incident") - 2, incident_count_before)
