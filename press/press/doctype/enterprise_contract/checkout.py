# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Stripe Checkout for USD Enterprise contracts. The payment carries PAYMENT_FOR, so the
Stripe webhook records it on the contract and not as team credits."""

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
import stripe
from stripe.api_resources.abstract import custom_method

from press.utils.billing import get_stripe

if TYPE_CHECKING:
	from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract

PAYMENT_FOR = "enterprise_contract"

# The pinned stripe SDK (2.56) has no Session.expire, but the API has the endpoint.
custom_method("expire", http_verb="post")(stripe.checkout.Session)


def start_stripe_checkout(contract: EnterpriseContract, return_url: str) -> tuple[str, str]:
	metadata = {"payment_for": PAYMENT_FOR, "enterprise_contract": contract.name}
	session = get_stripe().checkout.Session.create(
		mode="payment",
		client_reference_id=contract.name,
		customer=frappe.db.get_value("Team", contract.team, "stripe_customer_id") or None,
		line_items=[{"price_data": price_data(contract, contract.amount_due()["total"]), "quantity": 1}],
		metadata=metadata,
		payment_intent_data={"metadata": metadata, "description": description(contract)},
		success_url=f"{return_url}?session_id={{CHECKOUT_SESSION_ID}}",
		cancel_url=f"{return_url}?payment=cancelled",
	)
	return session.id, session.url


def paid_checkout_reference(contract: EnterpriseContract, session_id: str | None) -> str | None:
	if not session_id or session_id != contract.checkout_reference:
		return None
	session = get_stripe().checkout.Session.retrieve(session_id)
	return session.payment_intent if session.payment_status == "paid" else None


# Called before the order is paid again or cancelled, in case the webhook did not arrive.
def record_paid_checkout(contract: EnterpriseContract) -> bool:
	if contract.status != "Awaiting Payment":
		return False
	reference = paid_checkout_reference(contract, contract.checkout_reference)
	if reference:
		contract.record_payment(reference=reference)
	return bool(reference)


# Called before the contract stops waiting on its session, or gets a new one, so that it
# cannot be paid later. Returns True if it was paid instead, and that payment is now recorded.
def close_checkout(contract: EnterpriseContract) -> bool:
	if record_paid_checkout(contract):
		return True
	return bool(contract.checkout_reference) and expire_session(contract)


def expire_session(contract: EnterpriseContract) -> bool:
	session = get_stripe().checkout.Session
	try:
		session.expire(contract.checkout_reference)
	except stripe.error.InvalidRequestError:
		# Stripe refuses a session that is not open. It can have been paid since the retrieve.
		if record_paid_checkout(contract):
			return True
		if session.retrieve(contract.checkout_reference).get("status") == "open":
			raise
	return False


def record_webhook_payment(payment_intent: dict):
	from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract

	name = payment_intent["metadata"]["enterprise_contract"]
	# Locked so that the webhook and the browser return record the payment once.
	contract = EnterpriseContract("Enterprise Contract", name, for_update=True)
	if contract.status == "Awaiting Payment":
		contract.record_payment(reference=payment_intent["id"])
	elif not contract.has_payment(payment_intent["id"]):
		log_unexpected_payment(contract, payment_intent["id"])


# The money was taken but the contract is not waiting for it, so staff must refund it.
def log_unexpected_payment(contract: EnterpriseContract, payment_intent: str):
	frappe.log_error(
		title="Enterprise Contract payment needs a refund",
		message=f"Payment {payment_intent} arrived for {contract.name}, which is {contract.status}.",
		reference_doctype="Enterprise Contract",
		reference_name=contract.name,
	)


def price_data(contract: EnterpriseContract, total: float) -> dict:
	return {
		"currency": contract.currency.lower(),
		"unit_amount": round(total * 100),
		"product_data": {"name": description(contract)},
	}


def description(contract: EnterpriseContract) -> str:
	return f"Frappe {contract.plan_title} plan, 1 year ({contract.name})"
