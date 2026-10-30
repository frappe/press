# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from urllib.parse import urlparse

import frappe
from frappe.utils import get_url

from press.guards import role_guard
from press.press.doctype.enterprise_contract.checkout import checkout_for
from press.press.doctype.enterprise_contract.enterprise_contract import (
	EnterpriseContract,
	bank_transfer_details,
	create_contract,
	open_contract_name,
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
	}


@frappe.whitelist()
@role_guard.api("billing")
def submit(order: dict | str, return_url: str, use_credits: bool = False):
	team = get_current_team(get_doc=True)
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
	return {"checkout_url": start_checkout(contract, return_url)}


@frappe.whitelist()
@role_guard.api("billing")
def pay_with_credits():
	# Locked so that a double click debits the credits once.
	contract = awaiting_payment_contract(for_update=True)
	contract.pay_with_credits()
	return contract.as_dashboard()


@frappe.whitelist()
@role_guard.api("billing")
def verify_payment(params: dict | str):
	name = open_contract_name(get_current_team())
	if not name:
		frappe.throw("No Enterprise order found")
	# Locked so that two returns from the gateway record the payment once.
	contract: EnterpriseContract = frappe.get_doc("Enterprise Contract", name, for_update=True)
	if contract.status == "Awaiting Payment":
		reference = checkout_for(contract).paid_reference(frappe.parse_json(params))
		if reference:
			contract.record_payment(reference=reference)
	return contract.as_dashboard()


@frappe.whitelist()
@role_guard.api("billing")
def submit_transfer_reference(reference: str):
	contract = awaiting_payment_contract()
	if contract.payment_gateway != "Bank Transfer":
		frappe.throw("This order is paid online")
	contract.submit_transfer_reference(reference)
	return contract.as_dashboard()


@frappe.whitelist()
@role_guard.api("billing")
def cancel_order():
	contract = awaiting_payment_contract()
	if contract.transfer_reference:
		frappe.throw("You have already sent a bank transfer for this order. Please contact support.")
	contract.status = "Cancelled"
	# Team members only have read access; billing access is checked above.
	contract.save(ignore_permissions=True)


def awaiting_payment_contract(for_update: bool = False) -> EnterpriseContract:
	name = frappe.db.get_value(
		"Enterprise Contract", {"team": get_current_team(), "status": "Awaiting Payment"}, "name"
	)
	if not name:
		frappe.throw("No Enterprise order is waiting for payment")
	return frappe.get_doc("Enterprise Contract", name, for_update=for_update)


def start_checkout(contract: EnterpriseContract, return_url: str) -> str:
	validate_return_url(return_url, frappe.request.host)
	reference, url = checkout_for(contract).start(return_url)
	contract.db_set("checkout_reference", reference)
	return url


# The gateway sends the customer back here, so it must be this site. host_name in
# site config can differ from the host the dashboard is served on, so both count.
def validate_return_url(return_url: str, request_host: str | None = None):
	hostnames = {urlparse(get_url()).hostname, (request_host or "").split(":")[0]}
	if urlparse(return_url).hostname not in hostnames:
		frappe.throw("Invalid return URL")
