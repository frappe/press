# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
import stripe

from press.api import enterprise_contract as contract_api
from press.press.doctype.enterprise_contract.enterprise_contract import ALREADY_PAID, create_contract
from press.press.doctype.enterprise_contract.test_enterprise_contract import (
	EnterpriseContractTestCase,
	create_team_with_billing_address,
)
from press.press.doctype.team.team import process_stripe_webhook

REFUND_LOG = "Enterprise Contract payment needs a refund"
VISA_CHARGE = {"data": [{"payment_method_details": {"card": {"brand": "visa", "last4": "4242"}}}]}


def intent(id: str, status: str, **extra) -> dict:
	charges = VISA_CHARGE if status == "succeeded" else {"data": []}
	return {"id": id, "status": status, "client_secret": f"{id}_secret", "charges": charges, **extra}


# Stripe is an external gateway, so its client is replaced; everything in Press runs for real.
def patch_stripe(create=None, retrieve=None, cancel_error=None):
	client = MagicMock()
	client.PaymentIntent.create.return_value = create
	client.PaymentIntent.retrieve.return_value = retrieve
	if cancel_error:
		client.PaymentIntent.cancel.side_effect = cancel_error
	return patch("press.press.doctype.enterprise_contract.card_payment.get_stripe", return_value=client)


def send_payment_webhook(contract: str, payment_intent: str):
	event = {
		"type": "payment_intent.succeeded",
		"data": {
			"object": {
				**intent(payment_intent, "succeeded"),
				"amount": 2500000,
				"created": 1793500000,
				"metadata": {"payment_for": "enterprise_contract", "enterprise_contract": contract},
			}
		},
	}
	process_stripe_webhook(frappe._dict(event_type=event["type"], payload=frappe.as_json(event)), None)


def add_saved_card(team: str):
	frappe.get_doc(
		doctype="Stripe Payment Method",
		name=frappe.generate_hash(length=10),
		team=team,
		brand="visa",
		last_4="4242",
		stripe_payment_method_id="pm_saved",
		is_default=1,
	).db_insert()


def payment_logs(contract: str) -> list:
	return frappe.get_all("Error Log", {"method": REFUND_LOG, "reference_name": contract}, pluck="error")


class CardPaymentTestCase(EnterpriseContractTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_team_with_billing_address("United States")
		frappe.db.set_value("Team", self.team.name, "stripe_customer_id", "cus_test")
		self.contract = create_contract(self.team, self.make_order())
		frappe.set_user(self.team.user)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.db.delete("Error Log", {"method": REFUND_LOG})


class TestCardPayment(CardPaymentTestCase):
	def test_saved_card_is_charged_on_the_page_and_the_payment_shows_the_card(self):
		add_saved_card(self.team.name)

		with patch_stripe(create=intent("pi_saved", "succeeded")) as get_stripe:
			response = contract_api.pay("saved_card")

		params = get_stripe.return_value.PaymentIntent.create.call_args.kwargs
		self.assertEqual(
			(params["payment_method"], params["confirm"], params["amount"], params["customer"]),
			("pm_saved", True, 2500000, "cus_test"),
		)
		# Only cards, so Stripe never needs a return URL for a redirect.
		self.assertEqual(params["payment_method_types"], ["card"])
		self.assertEqual(response["payment"]["status"], "succeeded")
		self.contract.reload()
		self.assertEqual(self.contract.status, "Pending Signature")
		self.assertEqual(self.contract.payments[0].paid_with, "Visa •4242")

	def test_saved_card_that_needs_3d_secure_is_recorded_once_after_the_page_confirms_it(self):
		add_saved_card(self.team.name)
		with patch_stripe(create=intent("pi_3ds", "requires_action")):
			response = contract_api.pay("saved_card")
		self.assertEqual(response["payment"]["client_secret"], "pi_3ds_secret")
		self.assertFalse(self.contract.reload().payments)

		with patch_stripe(retrieve=intent("pi_3ds", "succeeded")):
			contract_api.confirm_card_payment()
		send_payment_webhook(self.contract.name, "pi_3ds")

		self.assertEqual([p.payment_reference for p in self.contract.reload().payments], ["pi_3ds"])
		self.assertEqual(payment_logs(self.contract.name), [])

	def test_payment_shows_the_card_on_api_versions_that_return_no_charges(self):
		paid = {**intent("pi_new_api", "succeeded"), "charges": None, "payment_method": "pm_once"}
		with patch_stripe(retrieve=paid) as get_stripe:
			get_stripe.return_value.PaymentMethod.retrieve.return_value = {
				"card": {"brand": "mastercard", "last4": "4444"}
			}
			self.contract.db_set("payment_intent", "pi_new_api")
			contract_api.confirm_card_payment()

		self.assertEqual(self.contract.reload().payments[0].paid_with, "Mastercard •4444")

	def test_pay_once_leaves_the_card_to_the_page_and_saves_nothing(self):
		with patch_stripe(create=intent("pi_once", "requires_payment_method")) as get_stripe:
			response = contract_api.pay("new_card")

		params = get_stripe.return_value.PaymentIntent.create.call_args.kwargs
		self.assertNotIn("payment_method", params)
		self.assertNotIn("setup_future_usage", params)
		self.assertEqual(response["payment"]["client_secret"], "pi_once_secret")
		self.assertEqual(self.contract.reload().payment_intent, "pi_once")

	def test_pay_once_for_a_team_without_a_stripe_customer_creates_one_with_the_billing_address(self):
		# Indian rules for export payments need the customer's name and address on Stripe.
		frappe.db.set_value("Team", self.team.name, "stripe_customer_id", None)
		with (
			patch_stripe(create=intent("pi_once", "requires_payment_method")) as get_stripe,
			patch("press.press.doctype.team.team.get_stripe", return_value=get_stripe.return_value),
		):
			get_stripe.return_value.Customer.create.return_value = frappe._dict(id="cus_new")
			contract_api.pay("new_card")

		client = get_stripe.return_value
		self.assertEqual(client.PaymentIntent.create.call_args.kwargs["customer"], "cus_new")
		address = client.Customer.modify.call_args.kwargs["address"]
		self.assertEqual((address["line1"], address["country"]), ("12 MG Road", "US"))

	def test_declined_saved_card_shows_the_bank_message_and_the_order_keeps_waiting(self):
		add_saved_card(self.team.name)
		declined = stripe.error.CardError("Your card was declined.", None, "card_declined")

		with patch_stripe() as get_stripe:
			get_stripe.return_value.PaymentIntent.create.side_effect = declined
			with self.assertRaisesRegex(frappe.ValidationError, "Your card was declined"):
				contract_api.pay("saved_card")

		self.assertEqual(self.contract.reload().status, "Awaiting Payment")

	def test_saved_card_payment_without_a_saved_card_asks_to_add_one(self):
		with patch_stripe(), self.assertRaisesRegex(frappe.ValidationError, "no saved card"):
			contract_api.pay("saved_card")

	def test_staff_acting_in_the_team_cannot_charge_the_customers_card(self):
		add_saved_card(self.team.name)
		frappe.set_user("Administrator")
		team = self.team.name

		with (
			patch(
				"press.api.enterprise_contract.get_current_team",
				side_effect=lambda get_doc=False: frappe.get_doc("Team", team) if get_doc else team,
			),
			patch_stripe() as get_stripe,
			self.assertRaisesRegex(frappe.ValidationError, contract_api.CARD_CUSTOMER_ONLY),
		):
			contract_api.pay("saved_card")
		get_stripe.return_value.PaymentIntent.create.assert_not_called()

	def test_bank_transfer_contract_cannot_be_paid_by_card(self):
		indian_team = create_team_with_billing_address("India")
		create_contract(indian_team, self.make_order())
		frappe.set_user(indian_team.user)

		with patch_stripe(), self.assertRaisesRegex(frappe.ValidationError, "paid by bank transfer"):
			contract_api.pay("new_card")

	def test_payment_options_show_the_saved_card_to_a_customer(self):
		add_saved_card(self.team.name)

		options = contract_api.get_contract(self.contract.name)

		self.assertEqual(options["saved_card"], {"brand": "visa", "last_4": "4242"})
		self.assertIsNone(options["card_blocked"])
		self.assertIsNone(options["bank_transfer"])


class TestClosingCardPayment(CardPaymentTestCase):
	def setUp(self):
		super().setUp()
		self.contract.db_set("payment_intent", "pi_open")

	def test_cancelling_the_order_cancels_its_open_intent(self):
		with patch_stripe(retrieve=intent("pi_open", "requires_payment_method")) as get_stripe:
			self.assertEqual(contract_api.cancel_order(), {"message": None})

		get_stripe.return_value.PaymentIntent.cancel.assert_called_once_with("pi_open")
		self.assertEqual(self.contract.reload().status, "Cancelled")

	def test_cancelling_an_order_whose_intent_is_paid_records_it_instead(self):
		with patch_stripe(retrieve=intent("pi_open", "succeeded")) as get_stripe:
			self.assertEqual(contract_api.cancel_order(), {"message": ALREADY_PAID})

		get_stripe.return_value.PaymentIntent.cancel.assert_not_called()
		self.assertEqual(self.contract.reload().status, "Pending Signature")

	def test_intent_paid_between_retrieve_and_cancel_is_recorded_instead_of_cancelled(self):
		refused = stripe.error.InvalidRequestError("This PaymentIntent has already succeeded.", None)
		with patch_stripe(retrieve=intent("pi_open", "requires_action"), cancel_error=refused) as get_stripe:
			get_stripe.return_value.PaymentIntent.retrieve.side_effect = [
				intent("pi_open", "requires_action"),
				intent("pi_open", "succeeded"),
			]
			self.assertEqual(contract_api.cancel_order(), {"message": ALREADY_PAID})

		self.assertEqual(self.contract.reload().payments[0].payment_reference, "pi_open")

	def test_cancel_error_on_an_intent_that_is_still_open_fails_the_cancel(self):
		refused = stripe.error.InvalidRequestError("Stripe is down", None)
		with (
			patch_stripe(retrieve=intent("pi_open", "requires_action"), cancel_error=refused),
			self.assertRaises(stripe.error.InvalidRequestError),
		):
			contract_api.cancel_order()

	def test_paying_with_credits_cancels_the_open_intent_first(self):
		self.team.allocate_credit_amount(30000, source="Prepaid Credits")

		with patch_stripe(retrieve=intent("pi_open", "requires_payment_method")) as get_stripe:
			contract_api.pay("credits")

		get_stripe.return_value.PaymentIntent.cancel.assert_called_once_with("pi_open")
		self.assertEqual(self.contract.reload().payments[0].paid_with, "Credits")

	def test_new_order_cancels_the_intent_of_the_order_it_replaces(self):
		with patch_stripe(retrieve=intent("pi_open", "requires_payment_method")) as get_stripe:
			response = contract_api.submit(self.make_order())

		get_stripe.return_value.PaymentIntent.cancel.assert_called_once_with("pi_open")
		self.assertNotEqual(response["contract"], self.contract.name)
		self.assertEqual(self.contract.reload().status, "Cancelled")

	def test_cancel_goes_through_the_installed_stripe_sdk_to_the_cancel_endpoint(self):
		responses = [
			('{"object": "payment_intent", "id": "pi_open", "status": "requires_action"}', 200, {}),
			('{"object": "payment_intent", "id": "pi_open", "status": "canceled"}', 200, {}),
		]
		http_client = MagicMock()
		http_client.name = "test"
		http_client.request_with_retries.side_effect = responses
		with (
			patch.object(stripe, "default_http_client", http_client),
			patch.object(stripe, "api_key", "sk_test_key"),
			patch("press.press.doctype.enterprise_contract.card_payment.get_stripe", return_value=stripe),
		):
			contract_api.cancel_order()

		method, url = http_client.request_with_retries.call_args_list[1].args[:2]
		self.assertEqual((method, url.split("stripe.com")[1]), ("post", "/v1/payment_intents/pi_open/cancel"))
		self.assertEqual(self.contract.reload().status, "Cancelled")


class TestCardPaymentWebhook(CardPaymentTestCase):
	def test_webhook_records_the_contracts_intent_once_and_adds_no_team_credits(self):
		self.contract.db_set("payment_intent", "pi_hook")

		send_payment_webhook(self.contract.name, "pi_hook")
		send_payment_webhook(self.contract.name, "pi_hook")

		self.contract.reload()
		self.assertEqual([p.payment_reference for p in self.contract.payments], ["pi_hook"])
		self.assertEqual(self.contract.payments[0].paid_with, "Visa •4242")
		self.assertFalse(frappe.db.exists("Balance Transaction", {"team": self.team.name}))

	def test_payment_for_an_intent_the_contract_is_not_waiting_on_is_logged_for_a_refund(self):
		self.contract.db_set("payment_intent", "pi_current")

		send_payment_webhook(self.contract.name, "pi_stray")

		self.assertIn("pi_stray", payment_logs(self.contract.name)[0])
		self.assertFalse(self.contract.reload().payments)

	def test_payment_for_a_cancelled_contract_is_logged_for_a_refund(self):
		self.contract.db_set("payment_intent", "pi_late")
		self.contract.cancel_order()

		send_payment_webhook(self.contract.name, "pi_late")

		self.assertIn(self.contract.name, payment_logs(self.contract.name)[0])
		self.assertEqual(self.contract.reload().status, "Cancelled")
