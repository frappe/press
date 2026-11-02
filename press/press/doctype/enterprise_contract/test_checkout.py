# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
import stripe

from press.api import enterprise_contract as contract_api
from press.api.enterprise_contract import get_contract, pay, validate_return_url
from press.press.doctype.enterprise_contract.checkout import record_paid_checkout
from press.press.doctype.enterprise_contract.enterprise_contract import ALREADY_PAID, create_contract
from press.press.doctype.enterprise_contract.test_enterprise_contract import (
	EnterpriseContractTestCase,
	create_team_with_billing_address,
)
from press.press.doctype.team.team import process_stripe_webhook


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


class TestStripeCheckoutPayment(EnterpriseContractTestCase):
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

	def test_contract_of_another_team_cannot_be_opened(self):
		contract = create_contract(create_team_with_billing_address("India"), self.make_order())
		other_team = create_team_with_billing_address("India")

		frappe.set_user(other_team.user)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaisesRegex(frappe.ValidationError, "could not find this contract"):
			get_contract(contract.name)

	def test_return_url_on_another_host_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "not on this site"):
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
