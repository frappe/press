# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.utils import add_months, get_first_day

from press.press.doctype.enterprise_contract.enterprise_contract import create_contract
from press.press.doctype.enterprise_contract.test_enterprise_contract import (
	EnterpriseContractTestCase,
	create_team_with_billing_address,
)
from press.press.doctype.invoice.invoice import Invoice


def create_invoice(team: str, months_from_now: int = 0) -> Invoice:
	start = add_months(get_first_day(frappe.utils.today()), months_from_now)
	return frappe.get_doc(doctype="Invoice", team=team, period_start=start).insert()


def add_usage(team: str, amount: float):
	usage_record = frappe.get_doc(doctype="Usage Record", team=team, amount=amount)
	usage_record.insert()
	usage_record.submit()


@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
class TestEnterpriseContractInstallments(EnterpriseContractTestCase):
	def test_payment_puts_one_twelfth_on_this_months_invoice_paid_by_the_contract(self):
		invoice = create_invoice(self.team.name)
		create_contract(self.team, self.make_order()).record_payment(reference="pay_1")

		invoice.reload()
		self.assertEqual(invoice.items[0].document_type, "Enterprise Contract")
		self.assertEqual(invoice.paid_by_contract, 200000)
		self.assertEqual(invoice.amount_due, 0)
		# Partner contribution reads total_before_discount of Subscription invoices.
		self.assertEqual(invoice.total_before_discount, 200000)

	def test_twelve_installments_add_up_to_the_payment_and_stop_after_a_year(self):
		team = create_team_with_billing_address("United States")
		create_contract(team, self.make_order()).record_payment(reference="pay_1")

		paid = [create_invoice(team.name, month).paid_by_contract for month in range(13)]

		self.assertEqual(paid[0], 2083.33)
		self.assertEqual(paid[11], 2083.37)
		self.assertEqual(round(sum(paid[:12]), 2), 25000)
		self.assertEqual(paid[12], 0)

	def test_contract_line_is_not_paid_from_team_credits(self):
		self.team.allocate_credit_amount(5000, source="Prepaid Credits")
		invoice = create_invoice(self.team.name)
		create_contract(self.team, self.make_order()).record_payment(reference="pay_1")
		add_usage(self.team.name, 1000)

		invoice.reload()
		invoice.finalize_invoice()

		self.assertEqual(invoice.status, "Paid")
		self.assertEqual(invoice.applied_credits, 1000)
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 4000)

	def test_invoice_wide_discount_leaves_the_contract_line_out(self):
		invoice = create_invoice(self.team.name)
		create_contract(self.team, self.make_order()).record_payment(reference="pay_1")
		add_usage(self.team.name, 1000)

		invoice.reload()
		invoice.append("discounts", {"discount_type": "Flat On Total", "based_on": "Percent", "percent": 10})
		invoice.save()

		self.assertEqual(invoice.total_discount_amount, 100)
		self.assertEqual(invoice.amount_due, 900)
