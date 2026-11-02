# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
import stripe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_years, getdate, today

from press.api import enterprise_contract as contract_api
from press.api.enterprise_contract import pay, validate_return_url
from press.press.doctype.enterprise_contract.checkout import record_paid_checkout
from press.press.doctype.enterprise_contract.enterprise_contract import (
	ALREADY_PAID,
	EnterpriseContract,
	create_contract,
)
from press.press.doctype.enterprise_warranty_plan.test_enterprise_warranty_plan import (
	create_test_enterprise_plan,
)
from press.press.doctype.team.team import process_stripe_webhook
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


def send_payment_webhook(contract: str, payment_intent: str):
	event = {
		"type": "payment_intent.succeeded",
		"data": {
			"object": {
				"id": payment_intent,
				"amount": 2500000,
				"created": 1793500000,
				"metadata": {"payment_for": "enterprise_contract", "enterprise_contract": contract},
			}
		},
	}
	process_stripe_webhook(frappe._dict(event_type=event["type"], payload=frappe.as_json(event)), None)


def patch_stripe_session(**session):
	client = MagicMock()
	client.checkout.Session.retrieve.return_value = frappe._dict(session)
	client.checkout.Session.create.return_value = frappe._dict(id="cs_new", url="https://stripe.test/cs_new")
	return patch("press.press.doctype.enterprise_contract.checkout.get_stripe", return_value=client)


def session_not_open_error():
	return stripe.error.InvalidRequestError("Only open sessions can be expired.", None)


REFUND_LOG = "Enterprise Contract payment needs a refund"


def payment_logs(contract: str) -> list:
	return frappe.get_all("Error Log", {"method": REFUND_LOG, "reference_name": contract}, pluck="error")


def delete_refund_logs():
	frappe.db.delete("Error Log", {"method": REFUND_LOG})


class EnterpriseContractTestCase(FrappeTestCase):
	def setUp(self):
		self.team = create_team_with_billing_address("India")
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

	def test_order_locks_the_team_row_so_two_orders_at_once_run_one_after_the_other(self):
		with patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as get_value:
			create_contract(self.team, self.make_order())

		get_value.assert_any_call("Team", self.team.name, "name", for_update=True)

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

	def test_stripe_webhook_records_the_contract_payment_once_and_adds_no_team_credits(self):
		team = create_team_with_billing_address("United States")
		contract = create_contract(team, self.make_order())

		send_payment_webhook(contract.name, "pi_enterprise_test")
		send_payment_webhook(contract.name, "pi_enterprise_test")

		contract.reload()
		self.assertEqual(contract.status, "Pending Signature")
		self.assertEqual([p.payment_reference for p in contract.payments], ["pi_enterprise_test"])
		self.assertFalse(frappe.db.exists("Balance Transaction", {"team": team.name}))

	def test_paid_checkout_and_its_webhook_record_one_payment(self):
		contract = create_contract(create_team_with_billing_address("United States"), self.make_order())
		contract.db_set("checkout_reference", "cs_enterprise_test")

		with patch_stripe_session(payment_status="paid", payment_intent="pi_enterprise_test"):
			self.assertTrue(record_paid_checkout(contract))
		send_payment_webhook(contract.name, "pi_enterprise_test")

		contract.reload()
		self.assertEqual(contract.status, "Pending Signature")
		self.assertEqual([p.payment_reference for p in contract.payments], ["pi_enterprise_test"])

	def test_pay_on_an_order_whose_last_checkout_is_paid_records_it_and_says_so(self):
		team = create_team_with_billing_address("United States")
		contract = create_contract(team, self.make_order())
		contract.db_set("checkout_reference", "cs_enterprise_test")

		frappe.set_user(team.user)
		self.addCleanup(frappe.set_user, "Administrator")
		with patch_stripe_session(payment_status="paid", payment_intent="pi_enterprise_test"):
			response = pay(return_url="http://press.local/dashboard/contracts")

		self.assertEqual(response, {"checkout_url": None, "message": ALREADY_PAID})
		self.assertEqual(contract.reload().status, "Pending Signature")

	def test_unpaid_checkout_is_not_recorded_and_the_order_keeps_waiting(self):
		contract = create_contract(create_team_with_billing_address("United States"), self.make_order())
		contract.db_set("checkout_reference", "cs_enterprise_test")

		with patch_stripe_session(payment_status="unpaid", payment_intent=None):
			self.assertFalse(record_paid_checkout(contract))

		self.assertEqual(contract.reload().status, "Awaiting Payment")
		self.assertFalse(contract.payments)

	def test_return_url_on_another_host_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Invalid return URL"):
			validate_return_url("https://attacker.example/dashboard/contracts")

	def test_return_url_on_the_host_the_request_came_in_on_is_accepted(self):
		validate_return_url("http://press.local:8080/dashboard/contracts", "press.local:8080")


class TestCheckoutSessionIsClosed(EnterpriseContractTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_team_with_billing_address("United States")
		self.contract = create_contract(self.team, self.make_order())
		self.contract.db_set("checkout_reference", "cs_old")
		frappe.local.request = frappe._dict(host="press.local", headers={})
		self.addCleanup(delattr, frappe.local, "request")
		frappe.set_user(self.team.user)
		self.addCleanup(frappe.set_user, "Administrator")

	def status(self) -> str:
		return frappe.db.get_value("Enterprise Contract", self.contract.name, "status")

	def test_cancelling_expires_the_open_session(self):
		with patch_stripe_session(payment_status="unpaid", payment_intent=None) as get_stripe:
			response = contract_api.cancel_order()

		get_stripe.return_value.checkout.Session.expire.assert_called_once_with("cs_old")
		self.assertEqual(response, {"message": None})
		self.assertEqual(self.status(), "Cancelled")

	def test_cancelling_a_paid_session_records_it_without_expiring(self):
		with patch_stripe_session(payment_status="paid", payment_intent="pi_paid") as get_stripe:
			response = contract_api.cancel_order()

		get_stripe.return_value.checkout.Session.expire.assert_not_called()
		self.assertEqual(response, {"message": ALREADY_PAID})
		self.assertEqual(self.status(), "Pending Signature")

	def test_session_paid_between_retrieve_and_expire_is_recorded_instead_of_cancelled(self):
		with patch_stripe_session() as get_stripe:
			session = get_stripe.return_value.checkout.Session
			session.retrieve.side_effect = [
				frappe._dict(payment_status="unpaid", payment_intent=None),
				frappe._dict(payment_status="paid", payment_intent="pi_raced"),
			]
			session.expire.side_effect = session_not_open_error()
			response = contract_api.cancel_order()

		self.assertEqual(response, {"message": ALREADY_PAID})
		self.assertEqual(self.status(), "Pending Signature")
		self.assertEqual(self.contract.reload().payments[0].payment_reference, "pi_raced")

	def test_session_that_already_expired_does_not_stop_the_cancel(self):
		with patch_stripe_session(
			payment_status="unpaid", payment_intent=None, status="expired"
		) as get_stripe:
			get_stripe.return_value.checkout.Session.expire.side_effect = session_not_open_error()
			contract_api.cancel_order()

		self.assertEqual(self.status(), "Cancelled")

	def test_expire_error_on_a_session_still_open_fails_the_cancel(self):
		with patch_stripe_session(payment_status="unpaid", payment_intent=None, status="open") as get_stripe:
			get_stripe.return_value.checkout.Session.expire.side_effect = session_not_open_error()
			with self.assertRaises(stripe.error.InvalidRequestError):
				contract_api.cancel_order()

		self.assertEqual(self.status(), "Awaiting Payment")

	def test_race_through_the_installed_stripe_sdk_posts_to_expire_and_records_the_payment(self):
		responses = [
			('{"object": "checkout.session", "payment_status": "unpaid", "status": "open"}', 200, {}),
			('{"error": {"type": "invalid_request_error", "message": "Not open"}}', 400, {}),
			('{"object": "checkout.session", "payment_status": "paid", "payment_intent": "pi_sdk"}', 200, {}),
		]
		http_client = MagicMock()
		http_client.name = "test"
		http_client.request_with_retries.side_effect = responses
		with (
			patch.object(stripe, "default_http_client", http_client),
			patch.object(stripe, "api_key", "sk_test_key"),
			patch("press.press.doctype.enterprise_contract.checkout.get_stripe", return_value=stripe),
		):
			response = contract_api.cancel_order()

		method, url = http_client.request_with_retries.call_args_list[1].args[:2]
		self.assertEqual(
			(method, url.split("stripe.com")[1]), ("post", "/v1/checkout/sessions/cs_old/expire")
		)
		self.assertEqual(response, {"message": ALREADY_PAID})
		self.assertEqual(self.contract.reload().payments[0].payment_reference, "pi_sdk")

	def test_new_pay_expires_the_previous_session_and_keeps_the_new_one(self):
		with patch_stripe_session(payment_status="unpaid", payment_intent=None) as get_stripe:
			response = pay(return_url="http://press.local/dashboard/contracts")

		get_stripe.return_value.checkout.Session.expire.assert_called_once_with("cs_old")
		self.assertEqual(response["checkout_url"], "https://stripe.test/cs_new")
		self.assertEqual(self.contract.reload().checkout_reference, "cs_new")

	def test_new_order_expires_the_session_of_the_order_it_replaces(self):
		with patch_stripe_session(payment_status="unpaid", payment_intent=None) as get_stripe:
			response = contract_api.submit(self.make_order(), "http://press.local/dashboard/contracts")

		get_stripe.return_value.checkout.Session.expire.assert_called_once_with("cs_old")
		self.assertEqual(response["checkout_url"], "https://stripe.test/cs_new")
		self.assertEqual(self.status(), "Cancelled")

	def test_new_order_paid_with_credits_expires_the_session_of_the_order_it_replaces(self):
		self.team.allocate_credit_amount(30000, source="Prepaid Credits")

		with patch_stripe_session(payment_status="unpaid", payment_intent=None) as get_stripe:
			contract_api.submit(self.make_order(), "http://press.local/dashboard/contracts", use_credits=True)

		get_stripe.return_value.checkout.Session.expire.assert_called_once_with("cs_old")
		self.assertEqual(self.status(), "Cancelled")
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 5000)

	def test_new_order_with_credits_when_the_old_session_is_paid_keeps_it_and_debits_nothing(self):
		self.team.allocate_credit_amount(30000, source="Prepaid Credits")

		with patch_stripe_session(payment_status="paid", payment_intent="pi_paid"):
			response = contract_api.submit(
				self.make_order(), "http://press.local/dashboard/contracts", use_credits=True
			)

		self.assertEqual(response["message"], ALREADY_PAID)
		self.assertEqual(self.status(), "Pending Signature")
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 30000)

	def test_paying_with_credits_expires_the_open_session(self):
		self.team.allocate_credit_amount(30000, source="Prepaid Credits")

		with patch_stripe_session(payment_status="unpaid", payment_intent=None) as get_stripe:
			contract_api.pay_with_credits()

		get_stripe.return_value.checkout.Session.expire.assert_called_once_with("cs_old")
		self.assertEqual(self.status(), "Pending Signature")
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 5000)

	def test_paying_with_credits_when_the_session_is_paid_records_it_and_debits_nothing(self):
		self.team.allocate_credit_amount(30000, source="Prepaid Credits")

		with patch_stripe_session(payment_status="paid", payment_intent="pi_paid"):
			response = contract_api.pay_with_credits()

		self.assertEqual(response["message"], ALREADY_PAID)
		self.assertEqual(self.contract.reload().payments[0].payment_reference, "pi_paid")
		self.assertEqual(frappe.get_doc("Team", self.team.name).get_balance(), 30000)

	def test_order_without_a_session_does_not_call_stripe(self):
		self.contract.db_set("checkout_reference", None)

		with patch_stripe_session() as get_stripe:
			contract_api.cancel_order()

		get_stripe.assert_not_called()
		self.assertEqual(self.status(), "Cancelled")


class TestLatePaymentIsLogged(EnterpriseContractTestCase):
	def setUp(self):
		super().setUp()
		self.contract = create_contract(create_team_with_billing_address("United States"), self.make_order())
		# Error Log is MyISAM, so rows stay after the rollback; contract names repeat after it.
		delete_refund_logs()
		self.addCleanup(delete_refund_logs)

	def test_payment_for_a_cancelled_contract_logs_contract_and_intent_for_a_refund(self):
		self.contract.cancel_order()

		send_payment_webhook(self.contract.name, "pi_late")

		self.assertEqual(len(payment_logs(self.contract.name)), 1)
		self.assertIn("pi_late", payment_logs(self.contract.name)[0])
		self.assertIn(self.contract.name, payment_logs(self.contract.name)[0])
		self.assertEqual(self.contract.reload().status, "Cancelled")
		self.assertFalse(self.contract.payments)

	def test_second_payment_for_a_paid_contract_is_logged_and_not_recorded(self):
		self.contract.record_payment(reference="pi_first")

		send_payment_webhook(self.contract.name, "pi_second")

		self.assertIn("pi_second", payment_logs(self.contract.name)[0])
		self.assertEqual([p.payment_reference for p in self.contract.reload().payments], ["pi_first"])

	def test_duplicate_delivery_of_the_recorded_payment_logs_nothing(self):
		send_payment_webhook(self.contract.name, "pi_first")
		send_payment_webhook(self.contract.name, "pi_first")

		self.assertEqual(payment_logs(self.contract.name), [])
