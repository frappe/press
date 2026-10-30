# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Stripe Checkout for USD Enterprise contracts. The payment carries PAYMENT_FOR, so the
Stripe webhook does not add it to team credits."""

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


def stripe_paid_reference(contract: EnterpriseContract, params: dict) -> str | None:
	session = get_stripe().checkout.Session.retrieve(params.get("session_id"))
	if session.id != contract.checkout_reference or session.payment_status != "paid":
		return None
	return session.payment_intent


def price_data(contract: EnterpriseContract, total: float) -> dict:
	return {
		"currency": contract.currency.lower(),
		"unit_amount": round(total * 100),
		"product_data": {"name": description(contract)},
	}


def description(contract: EnterpriseContract) -> str:
	return f"Frappe {contract.plan_title} plan, 1 year ({contract.name})"
