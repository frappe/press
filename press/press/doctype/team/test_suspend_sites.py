# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.suspend_sites import suspend_sites_and_send_email
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_team


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestSuspendSites(FrappeTestCase):
	def setUp(self):
		# Recipients are cached, and teams reuse emails across tests
		get_communication_info.clear_cache()
		self.team = create_test_team()
		create_test_site(team=self.team.name)

	def tearDown(self):
		frappe.db.rollback()
		get_communication_info.clear_cache()

	def add_billing_email(self, email: str):
		self.team.append("communication_infos", {"channel": "Email", "type": "Billing", "value": email})
		self.team.save()
		get_communication_info.clear_cache()

	def suspend(self) -> list[str]:
		with patch.object(frappe, "sendmail") as sendmail:
			suspend_sites_and_send_email(Team("Team", self.team.name))
		return sendmail.call_args.kwargs["recipients"]

	def test_suspension_email_goes_to_the_billing_contact_when_one_is_set(self):
		self.add_billing_email("billing@example.com")

		self.assertEqual(self.suspend(), ["billing@example.com"])

	def test_suspension_email_goes_to_the_team_owner_without_a_billing_contact(self):
		self.assertEqual(self.suspend(), [self.team.user])
