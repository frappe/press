# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.team.suspend_sites import execute, suspend_sites_and_send_email
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_team
from press.tests.before_test import freeze_time

BILLING_EMAIL = "billing-contact@example.com"
GRACE_PERIOD_DAY = "2026-11-15"
AFTER_GRACE_PERIOD_DAY = "2026-11-16"


# suspend_sites_and_send_email commits, which would leak this team past the rollback
@patch("press.press.doctype.team.suspend_sites.frappe.db.commit", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestSuspendSites(FrappeTestCase):
	def setUp(self):
		# Recipients are cached, and teams reuse emails across tests
		get_communication_info.clear_cache()
		self.team = create_test_team()
		self.site = create_test_site(team=self.team.name)

	def tearDown(self):
		frappe.db.rollback()
		get_communication_info.clear_cache()

	def add_billing_email(self):
		self.team.append(
			"communication_infos", {"channel": "Email", "type": "Billing", "value": BILLING_EMAIL}
		)
		self.team.save()
		get_communication_info.clear_cache()

	def suspend(self) -> list[str]:
		with patch.object(frappe, "sendmail") as sendmail:
			suspend_sites_and_send_email(Team("Team", self.team.name))
		return sendmail.call_args.kwargs["recipients"]

	def test_suspension_email_goes_to_the_billing_contact_when_one_is_set(self):
		self.add_billing_email()

		self.assertEqual(self.suspend(), [BILLING_EMAIL])

	def test_suspension_email_goes_to_the_team_owner_without_a_billing_contact(self):
		self.assertEqual(self.suspend(), [self.team.user])

	def create_unpaid_invoice(self, period_start: str, period_end: str):
		self.team.db_set("payment_mode", "Prepaid Credits")
		invoice = frappe.get_doc(
			doctype="Invoice", team=self.team.name, period_start=period_start, period_end=period_end
		)
		invoice.append("items", {"quantity": 1, "rate": 500, "amount": 500})
		invoice.insert()
		invoice.finalize_invoice()
		self.assertEqual(invoice.status, "Unpaid")

	def run_daily_suspension_job(self, day: str, invoice_period=("2026-10-01", "2026-10-31")):
		self.site.db_set("plan", create_test_plan("Site").name)
		self.create_unpaid_invoice(*invoice_period)
		with freeze_time(day), patch.object(frappe, "sendmail"):
			execute()

	def site_status(self) -> str:
		return frappe.db.get_value("Site", self.site.name, "status")

	def test_daily_job_suspends_sites_of_a_team_with_last_months_invoice_unpaid_after_the_15th(self):
		self.run_daily_suspension_job(AFTER_GRACE_PERIOD_DAY)

		self.assertEqual(self.site_status(), "Suspended")

	def test_daily_job_does_not_suspend_anything_until_the_15th_of_the_month(self):
		self.run_daily_suspension_job(GRACE_PERIOD_DAY)

		self.assertEqual(self.site_status(), "Active")

	def test_daily_job_does_not_suspend_sites_of_a_free_account(self):
		self.team.db_set("free_account", 1)

		self.run_daily_suspension_job(AFTER_GRACE_PERIOD_DAY)

		self.assertEqual(self.site_status(), "Active")

	def test_daily_job_does_not_suspend_sites_of_a_team_with_an_extended_payment_due_date(self):
		self.team.db_set("extend_payment_due_suspension", 1)

		self.run_daily_suspension_job(AFTER_GRACE_PERIOD_DAY)

		self.assertEqual(self.site_status(), "Active")

	def test_daily_job_does_not_suspend_a_free_site_of_a_paying_team(self):
		self.site.db_set("free", 1)

		self.run_daily_suspension_job(AFTER_GRACE_PERIOD_DAY)

		self.assertEqual(self.site_status(), "Active")

	def test_daily_job_ignores_an_unpaid_invoice_of_the_current_month(self):
		self.run_daily_suspension_job(AFTER_GRACE_PERIOD_DAY, invoice_period=("2026-11-01", "2026-11-10"))

		self.assertEqual(self.site_status(), "Active")
