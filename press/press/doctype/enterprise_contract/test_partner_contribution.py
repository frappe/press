# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.utils import add_months, get_first_day, get_last_day, getdate, today

from press.api.partner import (
	get_current_month_partner_contribution,
	get_partner_contribution_list,
	get_partner_mrr,
	get_prev_month_partner_contribution,
)
from press.press.doctype.enterprise_contract.enterprise_contract import create_contract
from press.press.doctype.enterprise_contract.partner_contribution import (
	contract_shares,
	send_partner_transactions,
)
from press.press.doctype.enterprise_contract.test_enterprise_contract import (
	EnterpriseContractTestCase,
	create_team_with_billing_address,
)
from press.press.doctype.team.test_team import create_test_team

CONNECTION = "press.press.doctype.enterprise_contract.partner_contribution.get_frappe_io_connection"


class TestPartnerContribution(EnterpriseContractTestCase):
	def setUp(self):
		super().setUp()
		self.partner = create_test_team()
		frappe.db.set_value(
			"Team",
			self.partner.name,
			{"erpnext_partner": 1, "partner_email": self.partner.user},
		)
		frappe.db.set_value("Team", self.team.name, "partner_email", self.partner.user)
		frappe.db.set_single_value("Press Settings", "send_contract_partner_transactions", 1)
		self.addCleanup(frappe.set_user, "Administrator")

	def paid_contract(self, team=None, reference="pay_1"):
		contract = create_contract(team or self.team, self.make_order())
		contract.record_payment(reference=reference)
		return contract

	def sent_transactions(self) -> list[dict]:
		with patch(CONNECTION) as connection:
			connection.return_value = MagicMock(url="https://frappe.test", headers={})
			send_partner_transactions()
		post = connection.return_value.session.post
		if not post.called:
			return []
		return json.loads(post.call_args.kwargs["data"]["partner_fc_invoices"])

	def test_twelve_monthly_shares_add_up_to_the_payment_and_stop_after_a_year(self):
		team = create_team_with_billing_address("United States")
		frappe.db.set_value("Team", team.name, "partner_email", self.partner.user)
		self.paid_contract(team)
		start = get_first_day(today())

		shares = [contract_shares(add_months(start, month), [self.partner.user]) for month in range(13)]

		amounts = [rows[0].amount for rows in shares[:12]]
		self.assertEqual(amounts[0], 2083.33)
		self.assertEqual(amounts[11], 2083.37)
		self.assertEqual(round(sum(amounts), 2), 25000)
		self.assertEqual(shares[12], [])

	def test_contract_payment_creates_no_invoice_and_adds_no_credits(self):
		frappe.db.delete("Invoice", {"team": self.team.name})
		self.paid_contract()

		self.assertFalse(frappe.db.exists("Invoice", {"team": self.team.name}))
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 0)

	def test_job_sends_this_months_share_with_a_reference_for_the_contract_and_month(self):
		contract = self.paid_contract()
		month = getdate()

		self.assertEqual(
			self.sent_transactions(),
			[
				{
					"invoice_id": f"{contract.name}-{month:%Y-%m}",
					"invoice_amount": 200000,
					"currency": "INR",
					"due_date": str(get_last_day(month)),
					"partner_email": self.partner.user,
					"team": self.team.user,
					"docstatus": 1,
					"transaction_type": "Enterprise Contract",
				}
			],
		)

	def test_job_sends_nothing_while_the_press_setting_is_off(self):
		self.paid_contract()
		frappe.db.set_single_value("Press Settings", "send_contract_partner_transactions", 0)

		self.assertEqual(self.sent_transactions(), [])

	def test_job_skips_a_customer_whose_partner_email_is_not_an_enabled_partner(self):
		self.paid_contract()
		frappe.db.set_value("Team", self.partner.name, "enabled", 0)

		self.assertEqual(self.sent_transactions(), [])

	def test_job_skips_a_disabled_customer(self):
		self.paid_contract()
		frappe.db.set_value("Team", self.team.name, "enabled", 0)

		self.assertEqual(self.sent_transactions(), [])

	def test_job_skips_an_unpaid_order_and_a_cancelled_contract(self):
		contract = create_contract(self.team, self.make_order())
		self.assertEqual(self.sent_transactions(), [])

		contract.record_payment(reference="pay_1")
		frappe.db.set_value("Enterprise Contract", contract.name, "status", "Cancelled")
		self.assertEqual(self.sent_transactions(), [])

	def test_job_fails_loudly_when_frappe_io_rejects_the_request(self):
		self.paid_contract()
		with patch(CONNECTION) as connection:
			connection.return_value = MagicMock(url="https://frappe.test", headers={})
			response = connection.return_value.session.post.return_value
			response.raise_for_status.side_effect = ConnectionError("frappe.io is down")
			with self.assertRaisesRegex(ConnectionError, "frappe.io is down"):
				send_partner_transactions()

	def test_partner_pages_convert_the_contract_share_to_the_partner_currency(self):
		frappe.db.set_value("Team", self.partner.name, "currency", "USD")
		self.paid_contract()
		frappe.set_user(self.partner.user)

		rows = get_partner_contribution_list(self.partner.user)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["customer_name"], "Acme Industries")
		self.assertEqual(rows[0]["status"], "Paid")
		self.assertEqual(rows[0]["partner_total"], round(200000 / 83, 2))
		self.assertEqual(get_current_month_partner_contribution(self.partner.user), round(200000 / 83, 2))

	def test_previous_month_contribution_and_mrr_count_the_share_of_that_month(self):
		contract = self.paid_contract()
		last_month = add_months(today(), -1)
		frappe.db.set_value(
			"Enterprise Contract Payment", contract.payments[0].name, "period_start", last_month
		)
		frappe.db.set_value("Team", self.partner.name, "currency", "INR")
		frappe.set_user(self.partner.user)

		self.assertEqual(get_prev_month_partner_contribution(self.partner.user), 200000)
		self.assertEqual(
			get_partner_mrr(self.partner.user, prev_month=True),
			[{"due_date": getdate(get_last_day(last_month)), "total_amount": 200000}],
		)
