# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Stripe Checkout for USD Enterprise contracts. The payment carries PAYMENT_FOR, so the
Stripe webhook records it on the contract and not as team credits."""

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

from press.utils.billing import get_stripe

if TYPE_CHECKING:
	from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract

PAYMENT_FOR = "enterprise_contract"


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


def record_webhook_payment(payment_intent: dict):
	from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract

	name = payment_intent["metadata"]["enterprise_contract"]
	# Locked so that the webhook and the browser return record the payment once.
	contract = EnterpriseContract("Enterprise Contract", name, for_update=True)
	if contract.status == "Awaiting Payment":
		contract.record_payment(reference=payment_intent["id"])


def price_data(contract: EnterpriseContract, total: float) -> dict:
	return {
		"currency": contract.currency.lower(),
		"unit_amount": round(total * 100),
		"product_data": {"name": description(contract)},
	}


def description(contract: EnterpriseContract) -> str:
	return f"Frappe {contract.plan_title} plan, 1 year ({contract.name})"
