# Copyright (c) 2023, Frappe and Contributors
# See license.txt
from __future__ import annotations

import math
import zoneinfo
from contextlib import suppress
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from hypothesis import given, settings
from hypothesis import strategies as st
from twilio.base.exceptions import TwilioRestException

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import (
	AlertmanagerWebhookLog,
)
from press.press.doctype.alertmanager_webhook_log.test_alertmanager_webhook_log import (
	create_test_alertmanager_webhook_log,
)
from press.press.doctype.incident.incident import (
	CALL_REPEAT_INTERVAL_NIGHT,
	CALL_THRESHOLD_SECONDS_NIGHT,
	CONFIRMATION_THRESHOLD_SECONDS_NIGHT,
	MIN_FIRING_INSTANCES,
	MIN_FIRING_INSTANCES_FRACTION,
	Incident,
	resolve_incidents,
	validate_incidents,
)
from press.press.doctype.prometheus_alert_rule.test_prometheus_alert_rule import (
	create_test_prometheus_alert_rule,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.utils.test import foreground_enqueue_doc


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


@st.composite
def get_total_and_firing_for_ongoing_incident(draw) -> tuple[int, int]:
	total = draw(st.integers(min_value=1, max_value=50))
	firing = draw(
		st.integers(
			min_value=min(
				MIN_FIRING_INSTANCES + 1, math.floor(MIN_FIRING_INSTANCES_FRACTION * total) + 1, total
			),
			max_value=total,
		)
	)
	return total, firing


@st.composite
def get_total_firing_and_resolved_for_resolved_incident(draw) -> tuple[int, int, int]:
	"""Generate a tuple of total and resolved instances such that incident is resolved."""
	total = draw(st.integers(min_value=1, max_value=50))
	firing = draw(
		st.integers(
			min_value=min(
				MIN_FIRING_INSTANCES + 1, math.floor(MIN_FIRING_INSTANCES_FRACTION * total) + 1, total
			),  # enough instances to trigger incident
			max_value=total,
		)
	)
	resolved = draw(
		st.integers(
			min_value=firing - min(MIN_FIRING_INSTANCES, math.floor(MIN_FIRING_INSTANCES_FRACTION * total)),
			max_value=firing,  # at least 1 firing and at most all firing instances should be resolved
		)
	)
	return total, firing, resolved


@patch(
	"press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log.enqueue_doc",
	new=foreground_enqueue_doc,
)
@patch.object(AlertmanagerWebhookLog, "send_telegram_notification", new=Mock())
@patch.object(AlertmanagerWebhookLog, "react", new=Mock())
@patch("press.press.doctype.incident.incident.frappe.db.commit", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
@patch("press.press.doctype.press_settings.press_settings.Client", new=MockTwilioClient)
@patch("press.press.doctype.incident.incident.enqueue_doc", new=foreground_enqueue_doc)
@patch("tenacity.nap.time", new=Mock())  # no sleep
@patch.object(Incident, "sites_down", new=[])
@patch.object(Incident, "down_bench", new=[])
class TestIncident(FrappeTestCase):
	def setUp(self):
		super().setUp()

		self.from_ = "+911234567892"
		frappe.db.set_single_value("Press Settings", "twilio_account_sid", "test")
		frappe.db.set_single_value("Press Settings", "twilio_api_key_sid", "test")
		frappe.db.set_single_value("Press Settings", "twilio_api_key_secret", "test")
		frappe.db.set_single_value("Press Settings", "twilio_phone_number", self.from_)

		self._create_test_incident_settings()

	def tearDown(self):
		frappe.db.rollback()

	def _create_test_incident_settings(self):
		user1 = create_test_press_admin_team().user
		user2 = create_test_press_admin_team().user
		self.test_phno_1 = "+911234567890"
		self.test_phno_2 = "+911234567891"

		# Purge Incident Settings if exists
		if frappe.db.exists("Incident Settings"):
			frappe.delete_doc("Incident Settings", "Incident Settings")

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
		"press.press.doctype.incident.test_incident.MockTwilioCallList.create",
		wraps=MockTwilioCallList("busy").create,
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

	@patch(
		"press.press.doctype.incident.test_incident.MockTwilioCallList.create",
		wraps=MockTwilioCallList("completed").create,
	)
	def test_incident_calls_only_one_person_if_first_person_picks_up(self, mock_calls_create: Mock):
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
			}
		).insert().call_humans()
		self.assertEqual(mock_calls_create.call_count, 1)

	@patch(
		"press.press.doctype.incident.test_incident.MockTwilioCallList.create",
		wraps=MockTwilioCallList("completed").create,
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

	@patch(
		"press.press.doctype.incident.test_incident.MockTwilioCallList.create",
		wraps=MockTwilioCallList("ringing").create,
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

	def test_call_event_creates_acknowledgement_update(self):
		with patch.object(MockTwilioCallList, "create", new=MockTwilioCallList("completed").create):
			incident = frappe.get_doc(
				{
					"doctype": "Incident",
					"alertname": "Test Alert",
				}
			).insert()
			incident.call_humans()
			incident.reload()
			self.assertEqual(incident.status, "Acknowledged")
			self.assertEqual(len(incident.updates), 1)
		with patch.object(MockTwilioCallList, "create", new=MockTwilioCallList("no-answer").create):
			incident = frappe.get_doc(
				{
					"doctype": "Incident",
					"alertname": "Test Alert",
				}
			).insert()
			incident.call_humans()
			incident.reload()
			self.assertEqual(len(incident.updates), 2)

	@patch(
		"press.press.doctype.incident.test_incident.MockTwilioCallList.create",
		wraps=MockTwilioCallList("completed").create,
	)
	def test_global_phone_call_alerts_disabled_wont_create_phone_calls(self, mock_calls_create):
		frappe.db.set_single_value("Incident Settings", "phone_call_alerts", 0)
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
			}
		).insert().call_humans()
		mock_calls_create.assert_not_called()
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
				"phone_call": False,
			}
		).insert().call_humans()
		mock_calls_create.assert_not_called()
		frappe.db.set_single_value("Incident Settings", "phone_call_alerts", 1)
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
				"phone_call": False,
			}
		).insert().call_humans()
		mock_calls_create.assert_not_called()

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

	@patch(
		"press.press.doctype.incident.test_incident.MockTwilioMessageList.create",
		wraps=MockTwilioMessageList().create,
	)
	def test_incident_creation_sends_text_message(self, mock_messages_create: Mock):
		frappe.get_doc(
			{
				"doctype": "Incident",
				"alertname": "Test Alert",
			}
		).insert()
		self.assertEqual(mock_messages_create.call_count, 2)

	def test_incident_gets_auto_resolved_when_resolved_alerts_fire(self):
		site = create_test_site()
		alert = create_test_prometheus_alert_rule()
		create_test_alertmanager_webhook_log(site=site, alert=alert, status="firing")
		incident = frappe.get_last_doc("Incident")
		self.assertEqual(incident.status, "Validating")
		create_test_alertmanager_webhook_log(site=site, alert=alert, status="resolved")
		resolve_incidents()
		incident.reload()
		self.assertEqual(incident.status, "Auto-Resolved")

	@given(get_total_and_firing_for_ongoing_incident())
	@settings(max_examples=20, deadline=timedelta(seconds=5))
	def test_is_enough_firing_is_true_for_ongoing_incident(self, total_firing):
		alert = create_test_alertmanager_webhook_log()
		total, firing = total_firing
		firing_instances = [0] * firing
		with (
			patch.object(AlertmanagerWebhookLog, "total_instances", new=total),
			patch.object(
				AlertmanagerWebhookLog,
				"past_alert_instances",
				new=lambda x, y: firing_instances,
			),
		):
			self.assertTrue(alert.is_enough_firing)

	@given(get_total_firing_and_resolved_for_resolved_incident())
	@settings(max_examples=20, deadline=timedelta(seconds=5))
	def test_is_enough_firing_is_false_for_resolved_incident(self, total_firing_resolved):
		alert = create_test_alertmanager_webhook_log(status="resolved")
		total, firing, resolved = total_firing_resolved
		firing_instances = set(range(firing))
		resolved_instances = set(range(resolved))

		with (
			patch.object(AlertmanagerWebhookLog, "total_instances", new=total),
			patch.object(
				AlertmanagerWebhookLog,
				"past_alert_instances",
				side_effect=[firing_instances, resolved_instances],
			),
		):
			self.assertFalse(alert.is_enough_firing)

	def test_incident_does_not_resolve_when_other_alerts_are_still_firing_but_does_when_less_than_required_sites_are_down(
		self,
	):
		site = create_test_site()
		site2 = create_test_site(server=site.server)
		site3 = create_test_site(server=site.server)
		alert = create_test_prometheus_alert_rule()

		create_test_alertmanager_webhook_log(site=site, alert=alert, status="firing")  # 33% sites down
		create_test_alertmanager_webhook_log(site=site2, alert=alert, status="firing")  # 66% sites down
		incident: Incident = frappe.get_last_doc("Incident")
		self.assertEqual(incident.status, "Validating")

		create_test_alertmanager_webhook_log(site=site3, status="firing")  # 3rd site down, nothing resolved
		resolve_incidents()
		incident.reload()
		self.assertEqual(incident.status, "Validating")

		create_test_alertmanager_webhook_log(site=site3, status="resolved")  # 66% sites down, 1 resolved
		resolve_incidents()
		incident.reload()
		self.assertEqual(incident.status, "Validating")

		create_test_alertmanager_webhook_log(
			site=site2, status="resolved"
		)  # 33% sites down, 2 resolved # minimum resolved
		resolve_incidents()
		incident.reload()
		self.assertEqual(incident.status, "Auto-Resolved")

	def test_threshold_field_is_checked_before_calling(self):
		create_test_alertmanager_webhook_log()
		incident = frappe.get_last_doc("Incident")
		incident.db_set("creation", frappe.utils.add_to_date(frappe.utils.now(), minutes=-1))
		validate_incidents()
		incident.reload()
		self.assertEqual(incident.status, "Validating")  # default min threshold is 5 mins
		incident.db_set("creation", frappe.utils.add_to_date(frappe.utils.now(), minutes=-17))
		validate_incidents()
		incident.reload()
		self.assertEqual(incident.status, "Confirmed")
		incident.db_set("status", "Validating")
		incident.db_set("creation", frappe.utils.add_to_date(frappe.utils.now(), minutes=-19))
		frappe.db.set_single_value("Incident Settings", "confirmation_threshold_day", str(21 * 60))
		frappe.db.set_single_value("Incident Settings", "confirmation_threshold_night", str(21 * 60))
		validate_incidents()
		incident.reload()
		self.assertEqual(incident.status, "Validating")

	@patch(
		"press.press.doctype.incident.test_incident.MockTwilioCallList.create",
		wraps=MockTwilioCallList("completed").create,
	)
	def test_calls_repeated_for_acknowledged_incidents(self, mock_calls_create):
		create_test_alertmanager_webhook_log()
		incident = frappe.get_last_doc("Incident")
		incident.db_set("status", "Acknowledged")
		resolve_incidents()
		mock_calls_create.assert_not_called()
		incident.reload()  # datetime conversion
		incident.db_set(
			"modified",
			incident.modified - timedelta(seconds=CALL_REPEAT_INTERVAL_NIGHT + 10),
			update_modified=False,
		)  # assume night interval is longer
		resolve_incidents()
		mock_calls_create.assert_called_once()

	def test_repeat_call_calls_acknowledging_person_first(self):
		create_test_alertmanager_webhook_log(
			creation=frappe.utils.add_to_date(
				frappe.utils.now(), minutes=-CONFIRMATION_THRESHOLD_SECONDS_NIGHT
			)
		)
		incident = frappe.get_last_doc("Incident")
		incident.db_set("status", "Confirmed")
		incident.db_set(
			"creation",
			incident.creation
			- timedelta(seconds=CONFIRMATION_THRESHOLD_SECONDS_NIGHT + CALL_THRESHOLD_SECONDS_NIGHT + 10),
		)

		with patch(
			"press.press.doctype.incident.test_incident.MockTwilioCallList.create",
			side_effect=[
				MockTwilioCallList("busy").create(),
				MockTwilioCallList("completed").create(),
			],
		):
			resolve_incidents()  # second guy picks up

		incident.reload()
		incident.db_set(
			"modified",
			incident.modified - timedelta(seconds=CALL_REPEAT_INTERVAL_NIGHT + 10),
			update_modified=False,
		)
		with patch(
			"press.press.doctype.incident.test_incident.MockTwilioCallList.create",
			wraps=MockTwilioCallList("completed").create,
		) as mock_calls_create:
			resolve_incidents()
			mock_calls_create.assert_called_with(
				to=self.test_phno_2, from_=self.from_, url="http://demo.twilio.com/docs/voice.xml"
			)

	@patch.object(TelegramMessage, "enqueue")
	def test_telegram_message_is_sent_when_unable_to_reach_twilio(self, mock_telegram_send):
		print(mock_telegram_send)
		create_test_alertmanager_webhook_log()
		incident = frappe.get_last_doc("Incident")
		with (
			patch.object(MockTwilioCallList, "create", side_effect=TwilioRestException("test", 500)),
			suppress(TwilioRestException),
		):
			incident.call_humans()
		mock_telegram_send.assert_called_once()

	def get_5_min_load_avg_prometheus_response(self, load_avg: float):
		return {
			"datasets": [
				{
					"name": {
						"__name__": "node_load5",
						"cluster": "Default",
						"instance": "n1.local.frappe.dev",
						"job": "node",
					},
					"values": [load_avg],
				}
			],
			"labels": [
				datetime(2025, 1, 17, 12, 40, 41, 241000, tzinfo=zoneinfo.ZoneInfo(key="Asia/Kolkata")),
			],
		}

	def test_high_load_avg_on_resource_makes_it_affected(self):
		create_test_alertmanager_webhook_log()
		incident: Incident = frappe.get_last_doc("Incident")
		with patch(
			"press.press.doctype.incident.incident.prometheus_query",
			side_effect=[
				self.get_5_min_load_avg_prometheus_response(2.0),
				self.get_5_min_load_avg_prometheus_response(32.0),
				self.get_5_min_load_avg_prometheus_response(2.0),
			],
		):
			incident.identify_affected_resource()
		self.assertEqual(incident.resource, incident.server)
		self.assertEqual(incident.resource_type, "Server")

	def test_no_response_from_monitor_on_resource_makes_it_affected(self):
		create_test_alertmanager_webhook_log()
		incident: Incident = frappe.get_last_doc("Incident")
		incident.identify_affected_resource()
		self.assertEqual(
			incident.resource, frappe.get_value("Server", incident.server, "database_server")
		)  # database is checked first because history
		self.assertEqual(incident.resource_type, "Database Server")
