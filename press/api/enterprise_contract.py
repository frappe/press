# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from urllib.parse import urlparse

import frappe
from frappe.utils import get_url

from press.guards import role_guard
from press.press.doctype.enterprise_contract.checkout import (
	close_checkout,
	paid_checkout_reference,
	start_stripe_checkout,
)
from press.press.doctype.enterprise_contract.enterprise_contract import (
	ALREADY_PAID,
	EnterpriseContract,
	bank_transfer_details,
	create_contract,
	lock_team_orders,
	open_contract_name,
	purchased_credit,
)
from press.press.doctype.enterprise_warranty_plan.enterprise_warranty_plan import enabled_plans
from press.utils import get_current_team


@frappe.whitelist()
@role_guard.api("billing")
def get():
	team = get_current_team(get_doc=True)
	name = open_contract_name(team.name)
	return {
		"plans": enabled_plans(team.currency),
		"contract": EnterpriseContract("Enterprise Contract", name).as_dashboard() if name else None,
		"bank_transfer": bank_transfer_details() if team.currency == "INR" else None,
		"credit_balance": purchased_credit(team.name),
	}


@frappe.whitelist()
@role_guard.api("billing")
def submit(order: dict | str, return_url: str, use_credits: bool = False):
	team = get_current_team(get_doc=True)
	# Taken first, so that an order placed at the same time cannot start a session we then miss.
	lock_team_orders(team.name)
	if close_awaiting_checkout():
		return {"checkout_url": None, "message": ALREADY_PAID}
	contract = create_contract(team, frappe.parse_json(order))
	if frappe.utils.sbool(use_credits):
		contract.pay_with_credits()
		return {"checkout_url": None}
	if contract.payment_gateway == "Bank Transfer":
		return {"checkout_url": None}
	return {"checkout_url": start_checkout(contract, return_url)}


@frappe.whitelist()
@role_guard.api("billing")
def pay(return_url: str):
	contract = awaiting_payment_contract()
	if close_checkout(contract):
		return {"checkout_url": None, "message": ALREADY_PAID}
	return {"checkout_url": start_checkout(contract, return_url)}


@frappe.whitelist()
@role_guard.api("billing")
def pay_with_credits():
	# Locked so that a double click debits the credits once.
	contract = awaiting_payment_contract()
	if close_checkout(contract):
		return {**contract.as_dashboard(), "message": ALREADY_PAID}
	contract.pay_with_credits()
	return contract.as_dashboard()


@frappe.whitelist()
@role_guard.api("billing")
def verify_payment(params: dict | str):
	name = open_contract_name(get_current_team())
	if not name:
		frappe.throw("No Enterprise order found")
	# Locked so that two returns from the gateway record the payment once.
	contract = EnterpriseContract("Enterprise Contract", name, for_update=True)
	if contract.status == "Awaiting Payment":
		validate_online_checkout(contract)
		reference = paid_checkout_reference(contract, frappe.parse_json(params).get("session_id"))
		if reference:
			contract.record_payment(reference=reference)
	return contract.as_dashboard()


@frappe.whitelist()
@role_guard.api("billing")
def submit_transfer_reference(reference: str):
	contract = awaiting_payment_contract()
	contract.submit_transfer_reference(reference)
	return contract.as_dashboard()


@frappe.whitelist()
@role_guard.api("billing")
def cancel_order():
	contract = awaiting_payment_contract()
	if close_checkout(contract):
		return {"message": ALREADY_PAID}
	contract.cancel_order()
	return {"message": None}


def awaiting_payment_contract() -> EnterpriseContract:
	name = awaiting_contract_name()
	if not name:
		frappe.throw("No Enterprise order is waiting for payment")
	return EnterpriseContract("Enterprise Contract", name, for_update=True)


# Recorded instead of raised, because an error rolls the recorded payment back.
def close_awaiting_checkout() -> bool:
	name = awaiting_contract_name()
	return bool(name) and close_checkout(EnterpriseContract("Enterprise Contract", name, for_update=True))


# A locking read, so that a request which waited sees the order another one just cancelled or paid.
def awaiting_contract_name() -> str | None:
	return frappe.db.get_value(
		"Enterprise Contract",
		{"team": get_current_team(), "status": "Awaiting Payment"},
		"name",
		for_update=True,
	)


def start_checkout(contract: EnterpriseContract, return_url: str) -> str:
	validate_return_url(return_url, frappe.request.host)
	validate_online_checkout(contract)
	reference, url = start_stripe_checkout(contract, return_url)
	contract.db_set("checkout_reference", reference)
	return url


def validate_online_checkout(contract: EnterpriseContract):
	if contract.payment_gateway != "Stripe":
		frappe.throw(f"{contract.payment_gateway} has no online checkout")


# The gateway sends the customer back here, so it must be this site. host_name in
# site config can differ from the host the dashboard is served on, so both count.
def validate_return_url(return_url: str, request_host: str | None = None):
	hostnames = {urlparse(get_url()).hostname, (request_host or "").split(":")[0]}
	if urlparse(return_url).hostname not in hostnames:
		frappe.throw("Invalid return URL")
