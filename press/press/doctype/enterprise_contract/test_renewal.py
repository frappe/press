# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, add_years, formatdate, getdate, today

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
		opens = formatdate(self.contract.renewal_opens_on(), "d MMM yyyy")
		with self.assertRaisesRegex(frappe.ValidationError, f"Nothing is due.*Renewal opens on {opens}\\."):
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

	def test_renewal_after_the_paid_year_ended_starts_on_the_day_it_is_paid(self):
		self.end_paid_year_in(-100)
		self.team.allocate_credit_amount(3000000, source="Prepaid Credits")
		dashboard = contract_api.get_contract(self.contract.name)["contract"]
		self.assertTrue(dashboard["lapsed"])
		self.assertIn("Your warranty ended on", dashboard["activity"][-1]["description"])

		contract_api.pay("credits")

		renewal = self.contract.reload().payments[-1]
		self.assertEqual(getdate(renewal.period_start), getdate(today()))
		self.assertEqual(getdate(renewal.period_end), getdate(add_days(add_years(today(), 1), -1)))
		self.assertFalse(contract_api.get_contract(self.contract.name)["contract"]["lapsed"])

	def test_credits_cannot_pay_a_renewal_whose_bank_transfer_is_being_verified(self):
		self.end_paid_year_in(10)
		contract_api.submit_transfer_reference("UTR000000000108")
		self.team.allocate_credit_amount(3000000, source="Prepaid Credits")

		with self.assertRaisesRegex(frappe.ValidationError, "already sent a bank transfer.*UTR000000000108"):
			contract_api.pay("credits")

		self.contract.reload()
		self.assertEqual(len(self.contract.payments), 1)
		self.assertEqual(self.contract.pending_transfer_reference(), "UTR000000000108")
		self.assertEqual(contract_api.get_contract(self.contract.name)["payment_methods"], [])

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

	def set_utr_submitted_on(self, date):
		frappe.db.set_value("Enterprise Contract", self.contract.name, "transfer_submitted_on", date)

	# The list price goes up after `date`; the contract keeps its price until then.
	def lock_price_until(self, date):
		frappe.db.set_value("Enterprise Contract", self.contract.name, "price_locked_until", date)
		frappe.db.set_value("Enterprise Warranty Plan", self.plan.name, "price_inr", 2600000)
		frappe.clear_document_cache("Enterprise Warranty Plan", self.plan.name)

	def confirm_utr_as_staff(self):
		frappe.set_user("Administrator")
		EnterpriseContract("Enterprise Contract", self.contract.name).confirm_bank_transfer()
		return self.contract.reload().payments[-1]

	def test_utr_sent_before_the_paid_year_ended_continues_the_year_when_confirmed_after_it(self):
		self.end_paid_year_in(1)
		contract_api.submit_transfer_reference("UTR000000000109")
		self.assertEqual(str(self.contract.reload().transfer_submitted_on), today())
		# Five days pass before staff confirm it: the UTR came one day before the year ended.
		self.end_paid_year_in(-4)
		self.set_utr_submitted_on(add_days(today(), -5))
		self.lock_price_until(add_days(today(), -3))

		renewal = self.confirm_utr_as_staff()

		self.assertEqual(getdate(renewal.period_start), getdate(add_days(today(), -3)))
		self.assertEqual(renewal.amount, 2400000)
		self.assertIsNone(self.contract.transfer_submitted_on)

	def test_utr_sent_after_the_paid_year_ended_starts_on_the_day_it_was_sent_not_when_confirmed(self):
		self.end_paid_year_in(-10)
		contract_api.submit_transfer_reference("UTR000000000110")
		self.set_utr_submitted_on(add_days(today(), -3))
		self.lock_price_until(add_days(today(), -3))

		renewal = self.confirm_utr_as_staff()

		self.assertEqual(getdate(renewal.period_start), getdate(add_days(today(), -3)))
		self.assertEqual(renewal.amount, 2400000)

	def test_utr_without_a_submitted_date_from_old_contracts_starts_on_the_confirm_day(self):
		self.end_paid_year_in(-10)
		contract_api.submit_transfer_reference("UTR000000000111")
		self.set_utr_submitted_on(None)

		renewal = self.confirm_utr_as_staff()

		self.assertEqual(getdate(renewal.period_start), getdate(today()))

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

	def test_order_placed_names_a_team_member_but_not_staff_who_created_it_in_desk(self):
		desk_contract = create_contract(self.team, self.make_order())
		self.assertEqual(desk_contract.as_dashboard()["activity"][0]["description"], "")
		desk_contract.cancel_order()

		frappe.set_user(self.team.user)
		self.addCleanup(frappe.set_user, "Administrator")
		dashboard_contract = create_contract(self.team, self.make_order())
		self.assertEqual(
			dashboard_contract.as_dashboard()["activity"][0]["description"], f"by {self.team.user}"
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
