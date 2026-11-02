# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_years, getdate, today

from press.press.doctype.enterprise_contract.enterprise_contract import (
	EnterpriseContract,
	create_contract,
)
from press.press.doctype.enterprise_warranty_plan.test_enterprise_warranty_plan import (
	create_test_enterprise_plan,
)
from press.press.doctype.team.test_team import create_test_team


def create_team_with_billing_address(country: str):
	team = create_test_team(country=country)
	address = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": "Acme Industries",
			"address_line1": "12 MG Road",
			"city": "Mumbai",
			"state": "Maharashtra",
			"pincode": "400001",
			"country": country,
			"gstin": "Not Applicable",
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value(
		"Team", team.name, {"billing_name": "Acme Industries", "billing_address": address.name}
	)
	return team


class EnterpriseContractTestCase(FrappeTestCase):
	def setUp(self):
		self.team = create_team_with_billing_address("India")
		self.set_up_plan_and_bank_details()

	def set_up_plan_and_bank_details(self):
		self.plan = create_test_enterprise_plan()
		frappe.db.set_single_value(
			"Press Settings",
			{
				"gst_percentage": 0.18,
				"bank_account_number": "50200012345678",
				"bank_ifsc_code": "HDFC0000001",
			},
		)
		frappe.clear_document_cache("Press Settings", "Press Settings")

	def tearDown(self):
		frappe.db.rollback()

	def make_order(self, **overrides) -> dict:
		return {
			"plan": self.plan.name,
			"billing_email": "billing@acme.test",
			"price_lock_years": 3,
			**overrides,
		}


class TestEnterpriseContract(EnterpriseContractTestCase):
	def test_payment_keeps_its_gst_split_when_the_billing_state_changes(self):
		frappe.db.set_single_value("Press Settings", "gst_home_state", "Maharashtra")
		contract = create_contract(self.team, self.make_order())
		contract.record_payment(reference="UTR000000000001")

		frappe.db.set_value("Address", contract.billing_address, "state", "Karnataka")
		frappe.db.set_single_value("Press Settings", "gst_home_state", None)

		contract.reload()
		view = contract.as_dashboard()
		self.assertEqual(view["payments"][0]["gst_split"], "intra_state")
		self.assertIsNone(view["gst_split"])

	def test_order_takes_billing_name_and_address_from_the_team(self):
		contract = create_contract(self.team, self.make_order())

		team = frappe.db.get_value("Team", self.team.name, ["billing_name", "billing_address"], as_dict=True)
		self.assertEqual(contract.billing_name, "Acme Industries")
		self.assertEqual(contract.billing_address, team.billing_address)
		self.assertEqual(contract.plan_title, "Enterprise")

	def test_order_is_rejected_until_the_team_adds_billing_details(self):
		team = create_test_team(country="India")

		with self.assertRaisesRegex(frappe.ValidationError, "Add your billing details"):
			create_contract(team, self.make_order())

	def test_order_for_a_disabled_plan_is_rejected(self):
		self.plan.db_set("enabled", 0)

		with self.assertRaisesRegex(frappe.ValidationError, "no longer available"):
			create_contract(self.team, self.make_order())

	def test_indian_team_order_is_priced_in_inr_paid_by_bank_transfer_and_waits_for_payment(self):
		contract = create_contract(self.team, self.make_order())

		self.assertEqual(contract.currency, "INR")
		self.assertEqual(contract.yearly_price, 2400000)
		self.assertEqual(contract.payment_gateway, "Bank Transfer")
		self.assertEqual(contract.status, "Awaiting Payment")
		self.assertEqual(getdate(contract.start_date), getdate(today()))
		self.assertEqual(getdate(contract.price_locked_until), getdate(add_days(add_years(today(), 3), -1)))

	def test_us_team_order_is_priced_in_usd_without_gst_and_paid_via_stripe(self):
		team = create_team_with_billing_address("United States")
		contract = create_contract(team, self.make_order())

		self.assertEqual(contract.payment_gateway, "Stripe")
		self.assertEqual(contract.amount_due(), {"amount": 25000, "gst": 0, "total": 25000})

	def test_inr_amount_due_adds_gst_from_press_settings(self):
		contract = create_contract(self.team, self.make_order())

		self.assertEqual(contract.amount_due(), {"amount": 2400000, "gst": 432000, "total": 2832000})

	def test_utr_that_is_not_12_to_22_letters_or_digits_is_rejected(self):
		contract = create_contract(self.team, self.make_order())

		with self.assertRaisesRegex(frappe.ValidationError, "12 to 22 character UTR"):
			contract.submit_transfer_reference("UTR-123")

	def test_confirming_bank_transfer_records_the_utr_as_the_first_payment(self):
		contract = create_contract(self.team, self.make_order())
		contract.submit_transfer_reference(" hdfcr52026102912345678 ")

		self.assertEqual(contract.status, "Awaiting Payment")
		contract.confirm_bank_transfer()

		self.assertEqual(contract.status, "Pending Signature")
		self.assertEqual(contract.payments[0].payment_reference, "HDFCR52026102912345678")
		self.assertEqual(contract.payments[0].amount_paid, 2832000)

	def test_stripe_order_rejects_a_bank_transfer_utr(self):
		contract = create_contract(create_team_with_billing_address("United States"), self.make_order())

		with self.assertRaisesRegex(frappe.ValidationError, "This order is paid online"):
			contract.submit_transfer_reference("HDFCR52026102912345678")

	def test_order_with_a_utr_cannot_be_cancelled_by_the_customer(self):
		contract = create_contract(self.team, self.make_order())
		contract.submit_transfer_reference("HDFCR52026102912345678")

		with self.assertRaisesRegex(frappe.ValidationError, "already sent a bank transfer"):
			contract.cancel_order()
		self.assertEqual(contract.reload().status, "Awaiting Payment")

	def test_unpaid_order_without_a_utr_is_cancelled(self):
		contract = create_contract(self.team, self.make_order())
		contract.cancel_order()

		self.assertEqual(frappe.db.get_value("Enterprise Contract", contract.name, "status"), "Cancelled")

	def test_bank_transfer_cannot_be_confirmed_before_the_customer_enters_a_utr(self):
		contract = create_contract(self.team, self.make_order())

		with self.assertRaisesRegex(frappe.ValidationError, "has not entered a UTR"):
			contract.confirm_bank_transfer()

	def test_inr_order_is_rejected_when_bank_details_are_not_set_up(self):
		frappe.db.set_single_value("Press Settings", "bank_account_number", "")
		frappe.clear_document_cache("Press Settings", "Press Settings")

		with self.assertRaisesRegex(frappe.ValidationError, "Bank transfer details are not set up"):
			create_contract(self.team, self.make_order())

	def test_payment_moves_order_to_pending_signature_and_covers_one_year(self):
		contract = create_contract(self.team, self.make_order())
		contract.record_payment(reference="pay_1")

		payment = contract.payments[0]
		self.assertEqual(contract.status, "Pending Signature")
		self.assertEqual(getdate(payment.period_start), getdate(today()))
		self.assertEqual(getdate(payment.period_end), getdate(add_days(add_years(today(), 1), -1)))
		self.assertEqual(payment.amount_paid, 2832000)
		self.assertEqual(contract.next_period_start(), getdate(add_years(today(), 1)))

	def test_paying_with_credits_debits_the_plan_price_without_gst_and_starts_the_contract(self):
		self.team.allocate_credit_amount(3000000, source="Prepaid Credits")
		contract = create_contract(self.team, self.make_order())

		contract.pay_with_credits()

		self.assertEqual(contract.status, "Pending Signature")
		self.assertEqual((contract.payments[0].gst, contract.payments[0].amount_paid), (0, 2400000))
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 600000)

	def test_free_credits_alone_do_not_pay_for_a_contract(self):
		self.team.allocate_credit_amount(3000000, source="Free Credits")
		contract = create_contract(self.team, self.make_order())

		with self.assertRaisesRegex(frappe.ValidationError, "Not enough credits to pay for the full year"):
			contract.pay_with_credits()
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 3000000)
		self.assertFalse(contract.payments)

	def test_paying_with_credits_draws_on_prepaid_credits_and_leaves_free_credits_untouched(self):
		free = self.team.allocate_credit_amount(1000000, source="Free Credits")
		prepaid = self.team.allocate_credit_amount(3000000, source="Prepaid Credits")
		contract = create_contract(self.team, self.make_order())

		contract.pay_with_credits()

		self.assertEqual(frappe.db.get_value("Balance Transaction", free.name, "unallocated_amount"), 1000000)
		self.assertEqual(
			frappe.db.get_value("Balance Transaction", prepaid.name, "unallocated_amount"), 600000
		)

	def test_paying_with_credits_is_rejected_when_they_do_not_cover_the_full_year(self):
		self.team.allocate_credit_amount(1000000, source="Prepaid Credits")
		contract = create_contract(self.team, self.make_order())

		with self.assertRaisesRegex(frappe.ValidationError, "Not enough credits"):
			contract.pay_with_credits()
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 1000000)
		self.assertFalse(contract.payments)

	def test_same_gateway_payment_returned_twice_is_recorded_once(self):
		contract = create_contract(self.team, self.make_order())
		contract.record_payment(reference="pay_1")
		contract.record_payment(reference="pay_1")

		self.assertEqual(len(contract.payments), 1)

	def test_renewal_keeps_locked_price_inside_lock_period_and_uses_list_price_after(self):
		contract = create_contract(self.team, self.make_order(price_lock_years=2))
		self.plan.price_inr = 2600000  # List price goes up after the order.
		self.plan.save()

		contract.record_payment(reference="pay_1")
		self.assertEqual(contract.renewal_price(), 2400000)

		contract.record_payment(reference="pay_2")
		self.assertEqual(contract.renewal_price(), 2600000)

	def test_contract_turns_active_once_frappe_attaches_signed_pdf_and_agreement_date(self):
		contract = create_contract(self.team, self.make_order())
		contract.record_payment(reference="pay_1")

		contract.agreement_date = "2026-11-03"
		contract.save()
		self.assertEqual(contract.status, "Pending Signature")

		contract.signed_contract = "/private/files/signed-contract.pdf"
		contract.save()
		self.assertEqual(contract.status, "Active")

	def test_new_order_cancels_an_order_abandoned_at_checkout(self):
		abandoned = create_contract(self.team, self.make_order())
		create_contract(self.team, self.make_order())

		self.assertEqual(frappe.db.get_value("Enterprise Contract", abandoned.name, "status"), "Cancelled")

	def test_new_order_is_rejected_when_team_has_a_paid_contract(self):
		create_contract(self.team, self.make_order()).record_payment(reference="pay_1")

		with self.assertRaisesRegex(frappe.ValidationError, "already has an Enterprise contract"):
			create_contract(self.team, self.make_order())

	def test_price_lock_longer_than_three_years_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "must be 1 to 3 years"):
			create_contract(self.team, self.make_order(price_lock_years=5))

	def test_contract_starts_on_the_day_the_first_payment_is_recorded(self):
		contract = create_contract(self.team, self.make_order())
		contract.db_set("start_date", add_days(today(), -3))  # Ordered three days ago.

		contract.reload()
		contract.record_payment(reference="pay_1")

		self.assertEqual(getdate(contract.start_date), getdate(today()))
		self.assertEqual(getdate(contract.price_locked_until), getdate(add_days(add_years(today(), 3), -1)))

	def test_dashboard_view_lists_latest_payment_first_with_next_renewal(self):
		contract = create_contract(self.team, self.make_order())
		contract.record_payment(reference="pay_1")
		contract.record_payment(reference="pay_2")

		view = EnterpriseContract("Enterprise Contract", contract.name).as_dashboard()

		self.assertEqual([p["payment_reference"] for p in view["payments"]], ["pay_2", "pay_1"])
		self.assertEqual(view["next_renewal"]["date"], getdate(add_years(today(), 2)))
