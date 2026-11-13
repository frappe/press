# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import functools
from typing import Literal

import frappe

from press.guards import role_guard
from press.press.doctype.enterprise_contract.card_payment import (
	close_card_payment,
	record_paid_intent,
	saved_card,
	start_card_payment,
)
from press.press.doctype.enterprise_contract.enterprise_contract import (
	ALREADY_PAID,
	VISIBLE_STATUSES,
	EnterpriseContract,
	bank_transfer_details,
	create_contract,
	lock_team_orders,
	open_contract_name,
	purchased_credit,
	team_contracts,
)
from press.press.doctype.enterprise_warranty_plan.enterprise_warranty_plan import enabled_plans, gst_split
from press.utils import get_current_team, is_partner_user, is_user_part_of_team
from press.utils.billing import get_publishable_key

PARTNER_ORDER_BLOCKED = "Partners can't place Enterprise orders. Please ask the customer to place the order from their own account."
PARTNER_PAYMENT_BLOCKED = (
	"Partners can't pay for Enterprise contracts. Please ask the customer to pay from their own account."
)
CARD_CUSTOMER_ONLY = (
	"Only a member of this team can pay by card. Please ask the team owner to pay from their account."
)
NOTHING_DUE = (
	"Nothing is due on your contract right now. You can renew from the contract page once its renewal opens."
)


def contracts_enabled(fn):
	@functools.wraps(fn)
	def inner(*args, **kwargs):
		if not frappe.db.get_value("Team", get_current_team(), "enable_enterprise_contracts"):
			frappe.throw(
				"Enterprise contracts are not enabled for this team. Please contact support to enable them."
			)
		return fn(*args, **kwargs)

	return inner


@frappe.whitelist()
@role_guard.api("billing")
@contracts_enabled
def get():
	team = get_current_team(get_doc=True)
	return {
		"plans": enabled_plans(team.currency),
		"open_contract": open_contract_name(team.name),
		"gst_split": gst_split(team.billing_address),
		"contracts": team_contracts(team.name),
		"order_blocked": PARTNER_ORDER_BLOCKED if acts_as_partner(team) else None,
	}


@frappe.whitelist()
@role_guard.api("billing")
@contracts_enabled
def get_contract(name: str):
	team = get_current_team(get_doc=True)
	if not frappe.db.exists("Enterprise Contract", {"name": name, "team": team.name}):
		frappe.throw("We could not find this contract. Please open it from the Contracts list.")
	return {
		"contract": EnterpriseContract("Enterprise Contract", name).as_dashboard(),
		**payment_options(team),
	}


# What the dashboard can offer to pay with, for an order or a renewal.
def payment_options(team) -> dict:
	inr = team.currency == "INR"
	card = None if inr else saved_card(team.name)
	return {
		"bank_transfer": bank_transfer_details() if inr else None,
		"saved_card": {"brand": card["brand"], "last_4": card["last_4"]} if card else None,
		"credit_balance": purchased_credit(team.name),
		"payment_blocked": PARTNER_PAYMENT_BLOCKED if acts_as_partner(team) else None,
		"card_blocked": None if inr or is_customer(team) else CARD_CUSTOMER_ONLY,
		"publishable_key": None if inr else get_publishable_key(),
	}


# Places the order only. The dashboard then pays it on the contract page.
@frappe.whitelist()
@role_guard.api("billing")
@contracts_enabled
def submit(order: dict | str):
	team = get_current_team(get_doc=True)
	if acts_as_partner(team):
		frappe.throw(PARTNER_ORDER_BLOCKED)
	# Taken first, so that an order placed at the same time cannot start a payment we then miss.
	lock_team_orders(team.name)
	if close_awaiting_card_payment():
		return {"contract": open_contract_name(team.name), "message": ALREADY_PAID}
	contract = create_contract(team, frappe.parse_json(order))
	return {"contract": contract.name, "message": None}


@frappe.whitelist()
@role_guard.api("billing")
@contracts_enabled
def pay(method: Literal["saved_card", "new_card", "credits"]):
	team = get_current_team(get_doc=True)
	if acts_as_partner(team):
		frappe.throw(PARTNER_PAYMENT_BLOCKED)
	# Locked so that a double click pays once.
	contract = payable_contract()
	# Checked first, so that a refused card payment does not cancel the customer's open intent.
	if method != "credits":
		validate_card_payment(team, contract)
	if close_card_payment(contract):
		return {"payment": None, "message": ALREADY_PAID}
	if method == "credits":
		contract.pay_with_credits()
		return {"payment": None, "message": None}
	return {"payment": start_card_payment(contract, use_saved_card=method == "saved_card"), "message": None}


# Called after the dashboard confirms a card payment, in case the webhook is late.
@frappe.whitelist()
@role_guard.api("billing")
@contracts_enabled
def confirm_card_payment():
	name = open_contract_name(get_current_team())
	if not name:
		frappe.throw("No Enterprise contract found")
	# Locked so that the webhook and this record the payment once.
	contract = EnterpriseContract("Enterprise Contract", name, for_update=True)
	record_paid_intent(contract)
	return contract.as_dashboard()


@frappe.whitelist()
@role_guard.api("billing")
@contracts_enabled
def submit_transfer_reference(reference: str):
	if acts_as_partner(get_current_team(get_doc=True)):
		frappe.throw(PARTNER_PAYMENT_BLOCKED)
	contract = payable_contract()
	contract.submit_transfer_reference(reference)
	return contract.as_dashboard()


@frappe.whitelist()
@role_guard.api("billing")
@contracts_enabled
def cancel_order():
	name = awaiting_contract_name()
	if not name:
		frappe.throw("No Enterprise order is waiting for payment")
	contract = EnterpriseContract("Enterprise Contract", name, for_update=True)
	if close_card_payment(contract):
		return {"message": ALREADY_PAID}
	contract.cancel_order()
	return {"message": None}


# A partner team, or a partner's owner or member acting in a customer's team.
def acts_as_partner(team) -> bool:
	return bool(team.erpnext_partner) or is_partner_user(frappe.session.user)


# The team's owner or a member, not staff or a partner acting in it.
def is_customer(team) -> bool:
	return is_user_part_of_team(frappe.session.user, team.name)


def validate_card_payment(team, contract: EnterpriseContract):
	if contract.payment_gateway != "Stripe":
		frappe.throw(
			"This contract is paid by bank transfer. Please use the bank details on the contract page."
		)
	if not is_customer(team):
		frappe.throw(CARD_CUSTOMER_ONLY)


# The team's order, or its contract with the renewal open. A locking read, so that a
# request which waited sees the payment another one just made.
def payable_contract() -> EnterpriseContract:
	name = frappe.db.get_value(
		"Enterprise Contract",
		{"team": get_current_team(), "status": ("in", VISIBLE_STATUSES)},
		"name",
		for_update=True,
	)
	if not name:
		frappe.throw(NOTHING_DUE)
	contract = EnterpriseContract("Enterprise Contract", name, for_update=True)
	contract.validate_payment_due()
	return contract


# Recorded instead of raised, because an error rolls the recorded payment back.
def close_awaiting_card_payment() -> bool:
	name = awaiting_contract_name()
	return bool(name) and close_card_payment(EnterpriseContract("Enterprise Contract", name, for_update=True))


def awaiting_contract_name() -> str | None:
	return frappe.db.get_value(
		"Enterprise Contract",
		{"team": get_current_team(), "status": "Awaiting Payment"},
		"name",
		for_update=True,
	)
