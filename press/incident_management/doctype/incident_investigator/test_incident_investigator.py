# Copyright (c) 2025, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.incident_management.doctype.incident_investigator.incident_investigator import (
	IncidentInvestigator,
)
from press.press.doctype.incident.incident import Incident


def create_test_incident() -> Incident:
	return frappe.get_doc(
		{"doctype": "Incident", "alertname": "Test Alert"},
	).insert()


class TestIncidentInvestigator(FrappeTestCase):
	@patch.object(IncidentInvestigator, "after_insert", Mock())
	@patch.object(Incident, "identify_affected_resource", Mock())
	@patch.object(Incident, "identify_problem", Mock())
	@patch.object(Incident, "take_grafana_screenshots", Mock())
	def test_investigation_creation_on_incident_confirmation(self):
		test_incident = create_test_incident()
		test_incident.confirm()
		investigator: IncidentInvestigator = frappe.get_last_doc("Incident Investigator")
		self.assertEqual(investigator.incident, test_incident.name)
