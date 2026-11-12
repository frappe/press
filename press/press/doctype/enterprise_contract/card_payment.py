# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Card payments for USD Enterprise contracts, made on the dashboard with a Stripe PaymentIntent.

The customer pays with the team's saved card or with a card entered once. The intent carries
PAYMENT_FOR, so the Stripe webhook records it on the contract and not as team credits."""

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
import stripe

from press.utils.billing import get_publishable_key, get_stripe

if TYPE_CHECKING:
	from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract

PAYMENT_FOR = "enterprise_contract"


def saved_card(team: str) -> dict | None:
	return frappe.db.get_value(
		"Stripe Payment Method",
		{"team": team, "is_default": 1},
		["brand", "last_4", "stripe_payment_method_id"],
		as_dict=True,
	)


def card_label(card: dict) -> str:
	return f"{(card.get('brand') or 'Card').title()} •{card.get('last_4') or card.get('last4')}"


# With a saved card the intent is confirmed here, so it is paid now or needs 3-D Secure.
# Without one, the dashboard confirms it with the card the customer enters.
def start_card_payment(contract: EnterpriseContract, use_saved_card: bool) -> dict:
	card = saved_card(contract.team) if use_saved_card else None
	if use_saved_card and not card:
		frappe.throw("Your team has no saved card. Please add a card or pay once with a card.")
	params = {
		"amount": round(contract.amount_due()["total"] * 100),
		"currency": contract.currency.lower(),
		# Cards only: the payment is made on the page, so nothing redirects and no return URL is needed.
		"payment_method_types": ["card"],
		"customer": stripe_customer(contract.team),
		"description": description(contract),
		"metadata": {"payment_for": PAYMENT_FOR, "enterprise_contract": contract.name},
	}
	if card:
		params.update(payment_method=card["stripe_payment_method_id"], confirm=True)
	try:
		intent = get_stripe().PaymentIntent.create(**params)
	except stripe.error.CardError as e:
		frappe.throw(e.user_message or "Your card was declined. Please try another card.")
	contract.db_set("payment_intent", intent["id"])
	if intent["status"] == "succeeded":
		record_intent(contract, intent)
	return {
		"status": intent["status"],
		"client_secret": intent["client_secret"],
		"publishable_key": get_publishable_key(),
	}


# Indian rules for export payments need the customer's name and address on Stripe. Press keeps
# them in sync once a team has a Stripe customer; a team that never added a card gets one here.
def stripe_customer(team_name: str) -> str:
	team = frappe.get_doc("Team", team_name)
	if not team.stripe_customer_id:
		team.create_stripe_customer()
		team.update_billing_details_on_stripe()
	return team.stripe_customer_id


# Called once the dashboard has confirmed the intent, in case the webhook is late.
def record_paid_intent(contract: EnterpriseContract) -> bool:
	if not contract.payment_intent or contract.has_payment(contract.payment_intent):
		return False
	intent = get_stripe().PaymentIntent.retrieve(contract.payment_intent)
	if intent["status"] != "succeeded":
		return False
	record_intent(contract, intent)
	return True


# Called before the contract is paid another way, gets a new intent, or is cancelled, so the
# old intent cannot be paid later. Returns True if it was paid instead, and is now recorded.
def close_card_payment(contract: EnterpriseContract) -> bool:
	if not contract.payment_intent or contract.has_payment(contract.payment_intent):
		return False
	if record_paid_intent(contract):
		return True
	intents = get_stripe().PaymentIntent
	try:
		intents.cancel(contract.payment_intent)
	except stripe.error.InvalidRequestError:
		# Stripe refuses an intent that is canceled, succeeded or processing.
		if record_paid_intent(contract):
			return True
		if intents.retrieve(contract.payment_intent)["status"] != "canceled":
			raise
	return False


def record_webhook_payment(payment_intent: dict):
	from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract

	name = payment_intent["metadata"]["enterprise_contract"]
	# Locked so that the webhook and the dashboard record the payment once.
	contract = EnterpriseContract("Enterprise Contract", name, for_update=True)
	if contract.has_payment(payment_intent["id"]):
		return
	if payment_intent["id"] == contract.payment_intent and contract.payment_due():
		record_intent(contract, payment_intent)
	else:
		log_unexpected_payment(contract, payment_intent["id"])


def record_intent(contract: EnterpriseContract, intent: dict):
	contract.record_payment(reference=intent["id"], paid_with=intent_card_label(intent))


def intent_card_label(intent: dict) -> str:
	card = charge_card(intent) or payment_method_card(intent.get("payment_method"))
	return card_label(card) if card else "Card"


# Older Stripe API versions return the charges on the intent.
def charge_card(intent: dict) -> dict | None:
	charges = (intent.get("charges") or {}).get("data") or []
	return charges[0].get("payment_method_details", {}).get("card") if charges else None


# Newer ones do not, so the card is read from the payment method. The label is only for
# display, so a failed lookup shows "Card" rather than losing the recorded payment.
def payment_method_card(payment_method: str | None) -> dict | None:
	if not payment_method:
		return None
	try:
		return get_stripe().PaymentMethod.retrieve(payment_method).get("card")
	except stripe.error.StripeError:
		return None


# The money was taken but the contract is not waiting for it, so staff must refund it.
def log_unexpected_payment(contract: EnterpriseContract, payment_intent: str):
	frappe.log_error(
		title="Enterprise Contract payment needs a refund",
		message=f"Payment {payment_intent} arrived for {contract.name}, which is {contract.status}.",
		reference_doctype="Enterprise Contract",
		reference_name=contract.name,
	)


def description(contract: EnterpriseContract) -> str:
	return f"Frappe {contract.plan_title} plan, 1 year from {contract.next_period_start()} ({contract.name})"
