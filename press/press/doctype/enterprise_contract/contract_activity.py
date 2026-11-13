# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""The contract's timeline on the dashboard's Activity tab. Display only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from frappe.utils import formatdate

from press.utils import is_user_part_of_team

if TYPE_CHECKING:
	from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract


def step(title: str, status: str, date=None, description: str = "") -> dict:
	return {"title": title, "status": status, "date": date, "description": description}


def period_text(row) -> str:
	return f"{formatdate(row.period_start, 'd MMM yyyy')} to {formatdate(row.period_end, 'd MMM yyyy')}"


# What has happened to the contract and what comes next, oldest first. Status values are
# the ones the dashboard's pipeline icons use.
def contract_activity(contract: EnterpriseContract) -> list[dict]:
	steps = [step("Order placed", "Success", contract.creation, placed_by(contract))]
	if contract.status == "Cancelled":
		return [*steps, step("Order cancelled", "Failed", contract.modified)]
	first, *renewals = contract.payments or [None]
	steps.append(payment_step(contract, first, "Payment"))
	steps.append(signature_step(contract))
	active = contract.status == "Active"
	steps.append(
		step(
			"Contract active", "Success" if active else "Pending", contract.agreement_date if active else None
		)
	)
	steps.extend(payment_step(contract, row, "Renewal") for row in renewals)
	if contract.payments:
		steps.append(renewal_step(contract))
	return steps


# Staff who created the contract in Desk are not named to the customer.
def placed_by(contract: EnterpriseContract) -> str:
	return f"by {contract.owner}" if is_user_part_of_team(contract.owner, contract.team) else ""


def payment_step(contract: EnterpriseContract, row, title: str) -> dict:
	if row:
		return step(f"{title} received", "Success", row.paid_on, f"{row.paid_with} · {period_text(row)}")
	if utr := contract.pending_transfer_reference():
		return step(title, "Running", None, f"Verifying bank transfer, UTR {utr}")
	return step(title, "Pending", None, "Waiting for your payment")


def signature_step(contract: EnterpriseContract) -> dict:
	if contract.signed_contract and contract.agreement_date:
		return step("Agreement signed by Frappe", "Success", contract.agreement_date)
	if contract.payments:
		return step("Agreement signed by Frappe", "Running", None, "Frappe is signing your agreement")
	return step("Agreement signed by Frappe", "Pending", None, "Frappe signs after payment")


def renewal_step(contract: EnterpriseContract) -> dict:
	start = formatdate(contract.next_period_start(), "d MMM yyyy")
	if utr := contract.pending_transfer_reference():
		return step("Next renewal", "Running", None, f"Verifying bank transfer, UTR {utr}")
	if contract.lapsed():
		ended = formatdate(contract.paid_until(), "d MMM yyyy")
		return step(
			"Next renewal",
			"Pending",
			None,
			f"Your warranty ended on {ended}. Renew to restart it from the day you pay.",
		)
	if contract.renewal_open():
		return step("Next renewal", "Pending", None, f"Renewal is open. Renew before {start}.")
	opens = formatdate(contract.renewal_opens_on(), "d MMM yyyy")
	return step("Next renewal", "Pending", None, f"Next year starts {start}. Renewal opens on {opens}.")
