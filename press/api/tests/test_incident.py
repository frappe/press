import typing
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from prometheus_api_client import PrometheusConnect

from press.api.incident import get_incidents
from press.incident_management.doctype.incident_investigator.test_incident_investigator import (
	get_mock_prometheus_client,
	make_custom_query_range_side_effect,
	mock_disk_usage,
	mock_system_load,
)
from press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log import (
	AlertmanagerWebhookLog,
)
from press.press.doctype.alertmanager_webhook_log.test_alertmanager_webhook_log import (
	create_test_alertmanager_webhook_log,
)
from press.press.doctype.incident.incident import Incident
from press.press.doctype.team.test_team import create_test_team
from press.utils.test import foreground_enqueue_doc

if typing.TYPE_CHECKING:
	from press.incident_management.doctype.incident_investigator.incident_investigator import (
		IncidentInvestigator,
	)


@patch.object(AlertmanagerWebhookLog, "send_telegram_notification", new=Mock())
@patch.object(AlertmanagerWebhookLog, "react", new=Mock())
@patch(
	"press.press.doctype.alertmanager_webhook_log.alertmanager_webhook_log.enqueue_doc",
	new=foreground_enqueue_doc,
)
@patch("tenacity.nap.time", new=Mock())  # no sleep
@patch("press.press.doctype.incident.incident.frappe.db.commit", new=Mock())
@patch("press.press.doctype.incident.incident.enqueue_doc", new=foreground_enqueue_doc)
@patch.object(Incident, "sites_down", new=[])
@patch.object(Incident, "down_bench", new=[])
class TestGetIncidents(FrappeTestCase):
	@patch.object(PrometheusConnect, "get_current_metric_value", mock_disk_usage(is_high=False))
	@patch.object(PrometheusConnect, "custom_query_range", make_custom_query_range_side_effect(is_high=True))
	@patch.object(PrometheusConnect, "get_metric_range_data", mock_system_load(is_high=True))
	@patch(
		"press.incident_management.doctype.incident_investigator.incident_investigator.get_prometheus_client",
		get_mock_prometheus_client,
	)
	@patch(
		"press.incident_management.doctype.incident_investigator.incident_investigator.frappe.enqueue_doc",
		foreground_enqueue_doc,
	)
	def test_incident_retrival(self):
		create_test_alertmanager_webhook_log()
		incident_one: Incident = frappe.get_last_doc("Incident")
		investigation_one: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")
		self.assertEqual(incident_one.investigation, investigation_one.name)

		investigation_one.db_set("creation", frappe.utils.add_to_date(minutes=-10))
		create_test_alertmanager_webhook_log()
		incident_two: Incident = frappe.get_last_doc("Incident")
		investigation_two: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")

		self.assertEqual(incident_two.investigation, investigation_two.name)

		resolved_incidents = get_incidents(resolved=True)
		self.assertListEqual(resolved_incidents, [])

		active_incidents = get_incidents()
		self.assertEqual(len(active_incidents), 2)

		for incident in active_incidents:
			self.assertIn(incident["name"], [incident_one.name, incident_two.name])
			self.assertIn(incident["investigation_name"], [investigation_one.name, investigation_two.name])

		incident_one.status = "Resolved"
		incident_one.save()

		resolved_incidents = get_incidents(resolved=True)
		self.assertEqual(len(resolved_incidents), 1)
		self.assertEqual(resolved_incidents[0]["name"], incident_one.name)

		active_incidents = get_incidents()
		self.assertEqual(len(active_incidents), 1)
		self.assertEqual(active_incidents[0]["name"], incident_two.name)

		incident_two.status = "Resolved"
		incident_two.save()

		resolved_incidents = get_incidents(resolved=True)
		self.assertEqual(len(resolved_incidents), 2)
		self.assertIn(resolved_incidents[0]["name"], [incident_one.name, incident_two.name])
		self.assertIn(resolved_incidents[1]["name"], [incident_one.name, incident_two.name])

		active_incidents = get_incidents()
		self.assertEqual(len(active_incidents), 0)

	@patch.object(PrometheusConnect, "get_current_metric_value", mock_disk_usage(is_high=False))
	@patch.object(PrometheusConnect, "custom_query_range", make_custom_query_range_side_effect(is_high=True))
	@patch.object(PrometheusConnect, "get_metric_range_data", mock_system_load(is_high=True))
	@patch(
		"press.incident_management.doctype.incident_investigator.incident_investigator.get_prometheus_client",
		get_mock_prometheus_client,
	)
	@patch(
		"press.incident_management.doctype.incident_investigator.incident_investigator.frappe.enqueue_doc",
		foreground_enqueue_doc,
	)
	def test_different_team_incidents(self):
		# Create an incident for a different team
		another_team = create_test_team().name

		# Incidents for another team should not be retrieved
		create_test_alertmanager_webhook_log()
		last_incident: Incident = frappe.get_last_doc("Incident")
		frappe.db.set_value("Server", last_incident.server, "team", another_team)
		frappe.db.set_value("Site", {"server": last_incident.server}, "team", another_team)

		active_incidents, resolved_incidents = get_incidents(), get_incidents(resolved=True)
		self.assertEqual(len(active_incidents), 0)
		self.assertEqual(len(resolved_incidents), 0)

		# Incidents for user's team should be retrieved
		create_test_alertmanager_webhook_log()
		active_incidents = get_incidents()
		self.assertEqual(len(active_incidents), 1)
		self.assertEqual(active_incidents[0]["name"], frappe.get_last_doc("Incident").name)
