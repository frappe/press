# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Hosted Stripe Checkout for USD Enterprise contracts. INR contracts are paid by bank transfer.

The yearly payment never becomes team credits. Stripe payments carry
`payment_for: enterprise_contract`, which the Stripe webhook skips.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

from press.utils.billing import get_stripe

if TYPE_CHECKING:
	from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract

PAYMENT_FOR = "enterprise_contract"


class StripeCheckout:
	def __init__(self, contract: EnterpriseContract):
		self.contract = contract

	def start(self, return_url: str) -> tuple[str, str]:
		contract = self.contract
		due = contract.amount_due()
		metadata = {"payment_for": PAYMENT_FOR, "enterprise_contract": contract.name}
		session = get_stripe().checkout.Session.create(
			mode="payment",
			client_reference_id=contract.name,
			customer=frappe.db.get_value("Team", contract.team, "stripe_customer_id") or None,
			line_items=[{"price_data": price_data(contract, due["total"]), "quantity": 1}],
			metadata=metadata,
			payment_intent_data={"metadata": metadata, "description": description(contract)},
			success_url=f"{return_url}?session_id={{CHECKOUT_SESSION_ID}}",
			cancel_url=f"{return_url}?payment=cancelled",
		)
		return session.id, session.url

	def paid_reference(self, params: dict) -> str | None:
		session = get_stripe().checkout.Session.retrieve(params.get("session_id"))
		if session.id != self.contract.checkout_reference or session.payment_status != "paid":
			return None
		return session.payment_intent


GATEWAYS = {"Stripe": StripeCheckout}


def checkout_for(contract: EnterpriseContract) -> StripeCheckout:
	if contract.payment_gateway not in GATEWAYS:
		frappe.throw(f"{contract.payment_gateway} has no online checkout")
	return GATEWAYS[contract.payment_gateway](contract)


def price_data(contract: EnterpriseContract, total: float) -> dict:
	return {
		"currency": contract.currency.lower(),
		"unit_amount": round(total * 100),
		"product_data": {"name": description(contract)},
	}


def description(contract: EnterpriseContract) -> str:
	return f"Frappe {contract.plan_title} plan, 1 year ({contract.name})"
