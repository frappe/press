# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, today

from press.api import enterprise_contract as contract_api
from press.press.doctype.enterprise_contract.enterprise_contract import (
	RENEWAL_WINDOW_DAYS,
	EnterpriseContract,
	create_contract,
)
from press.press.doctype.enterprise_contract.test_enterprise_contract import EnterpriseContractTestCase


class TestRenewal(EnterpriseContractTestCase):
	def setUp(self):
		super().setUp()
		self.contract = create_contract(self.team, self.make_order())
		self.contract.confirm_bank_transfer(reference="UTR000000000101")
		frappe.set_user(self.team.user)
		self.addCleanup(frappe.set_user, "Administrator")

	# Moves the paid year so it ends in `days`, as if the contract had been running.
	def end_paid_year_in(self, days: int):
		row = self.contract.payments[-1]
		frappe.db.set_value("Enterprise Contract Payment", row.name, "period_end", add_days(today(), days))
		self.contract = EnterpriseContract("Enterprise Contract", self.contract.name)

	def test_nothing_is_due_until_the_renewal_window_opens(self):
		self.end_paid_year_in(RENEWAL_WINDOW_DAYS + 1)

		self.assertFalse(self.contract.payment_due())
		with self.assertRaisesRegex(frappe.ValidationError, "Nothing is due.*Renewal opens on"):
			contract_api.submit_transfer_reference("UTR000000000102")

	def test_customer_renews_with_credits_for_the_next_year_once_the_window_opens(self):
		self.end_paid_year_in(RENEWAL_WINDOW_DAYS - 1)
		self.team.allocate_credit_amount(3000000, source="Prepaid Credits")

		contract_api.pay("credits")

		self.contract.reload()
		renewal = self.contract.payments[-1]
		self.assertEqual(len(self.contract.payments), 2)
		self.assertEqual(getdate(renewal.period_start), getdate(add_days(today(), RENEWAL_WINDOW_DAYS)))
		self.assertEqual((renewal.amount, renewal.paid_with), (2400000, "Credits"))
		self.assertFalse(self.contract.payment_due())

	def test_credits_cannot_pay_a_renewal_whose_bank_transfer_is_being_verified(self):
		self.end_paid_year_in(10)
		contract_api.submit_transfer_reference("UTR000000000108")
		self.team.allocate_credit_amount(3000000, source="Prepaid Credits")

		with self.assertRaisesRegex(frappe.ValidationError, "already sent a bank transfer.*UTR000000000108"):
			contract_api.pay("credits")

		self.contract.reload()
		self.assertEqual(len(self.contract.payments), 1)
		self.assertEqual(self.contract.pending_transfer_reference(), "UTR000000000108")

	def test_staff_record_a_renewal_bank_transfer_the_customer_sent(self):
		self.end_paid_year_in(10)
		contract_api.submit_transfer_reference("utr000000000103")

		frappe.set_user("Administrator")
		contract = frappe.get_doc("Enterprise Contract", self.contract.name)
		contract.run_method("onload")
		self.assertTrue(contract.get_onload().payment_due)
		contract.confirm_bank_transfer()

		contract.reload()
		self.assertEqual(
			[p.payment_reference for p in contract.payments], ["UTR000000000101", "UTR000000000103"]
		)
		self.assertIsNone(contract.transfer_reference)

	def test_utr_left_on_a_contract_paid_before_it_was_cleared_does_not_block_the_renewal(self):
		# Contracts paid before the UTR was cleared on payment still hold it.
		frappe.db.set_value(
			"Enterprise Contract", self.contract.name, "transfer_reference", "UTR000000000101"
		)
		self.end_paid_year_in(10)

		self.assertIsNone(self.contract.as_dashboard()["transfer_reference"])
		contract_api.submit_transfer_reference("UTR000000000107")
		frappe.set_user("Administrator")
		EnterpriseContract("Enterprise Contract", self.contract.name).confirm_bank_transfer()

		self.assertEqual(self.contract.reload().payments[-1].payment_reference, "UTR000000000107")

	def test_staff_cannot_record_a_transfer_before_the_renewal_window(self):
		frappe.set_user("Administrator")

		with self.assertRaisesRegex(frappe.ValidationError, "Renewal opens on"):
			self.contract.confirm_bank_transfer(reference="UTR000000000104")


class TestContractActivity(EnterpriseContractTestCase):
	def steps(self, contract) -> list[tuple[str, str]]:
		return [(s["title"], s["status"]) for s in contract.as_dashboard()["activity"]]

	def test_new_order_shows_payment_waiting_and_the_rest_pending(self):
		contract = create_contract(self.team, self.make_order())

		self.assertEqual(
			self.steps(contract),
			[
				("Order placed", "Success"),
				("Payment", "Pending"),
				("Agreement signed by Frappe", "Pending"),
				("Contract active", "Pending"),
			],
		)

	def test_utr_under_verification_shows_as_in_progress(self):
		contract = create_contract(self.team, self.make_order())
		contract.submit_transfer_reference("UTR000000000105")

		self.assertEqual(self.steps(contract)[1], ("Payment", "Running"))

	def test_active_contract_shows_each_step_done_and_the_next_renewal(self):
		contract = create_contract(self.team, self.make_order())
		contract.confirm_bank_transfer(reference="UTR000000000106")
		contract.update({"agreement_date": today(), "signed_contract": "/files/signed.pdf"}).save()

		activity = contract.as_dashboard()["activity"]

		self.assertEqual(
			[(s["title"], s["status"]) for s in activity],
			[
				("Order placed", "Success"),
				("Payment received", "Success"),
				("Agreement signed by Frappe", "Success"),
				("Contract active", "Success"),
				("Next renewal", "Pending"),
			],
		)
		self.assertIn("Bank transfer", activity[1]["description"])
		self.assertIn("Renewal opens on", activity[-1]["description"])

	def test_cancelled_order_ends_with_the_cancellation(self):
		contract = create_contract(self.team, self.make_order())
		contract.cancel_order()

		self.assertEqual(self.steps(contract), [("Order placed", "Success"), ("Order cancelled", "Failed")])
