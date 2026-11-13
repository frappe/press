# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_years, cint, formatdate, getdate, now_datetime, today

from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.balance_transaction.balance_transaction import unallocated_credit
from press.press.doctype.enterprise_warranty_plan.enterprise_warranty_plan import (
	EnterpriseWarrantyPlan,
	amount_due,
	gst_split,
)

if TYPE_CHECKING:
	from press.press.doctype.team.team import Team

UTR_PATTERN = re.compile(r"[A-Z0-9]{12,22}")
# Credits the team paid for. Free and promotional credits do not pay for a contract.
PURCHASED_CREDIT_SOURCES = ("Prepaid Credits", "Transferred Credits")
OPEN_STATUSES = ("Pending Signature", "Active")
ALREADY_PAID = "This payment is already done. Your contract shows it now."
# A contract can be renewed this many days before its paid year ends.
RENEWAL_WINDOW_DAYS = 30
VISIBLE_STATUSES = ("Awaiting Payment", *OPEN_STATUSES)
ORDER_FIELDS = (
	"plan",
	"billing_email",
	"contact_person",
	"designation",
	"billing_partner",
	"legal_entities_covered",
	"price_lock_years",
)
DASHBOARD_FIELDS = (
	"name",
	"status",
	"payment_gateway",
	"plan_title",
	"currency",
	"yearly_price",
	"price_lock_years",
	"start_date",
	"price_locked_until",
	"billing_name",
	"billing_email",
	"billing_address",
	"legal_entities_covered",
	"agreement_date",
	"signed_contract",
	"transfer_reference",
	"contact_person",
	"designation",
	"billing_partner",
	"creation",
)


def purchased_credit(team: str) -> float:
	return unallocated_credit(team, PURCHASED_CREDIT_SOURCES)


class EnterpriseContract(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.enterprise_contract_payment.enterprise_contract_payment import (
			EnterpriseContractPayment,
		)

		agreement_date: DF.Date | None
		billing_address: DF.Link | None
		billing_email: DF.Data
		billing_name: DF.Data | None
		billing_partner: DF.Data | None
		contact_person: DF.Data | None
		currency: DF.Link
		designation: DF.Data | None
		exclude_from_partner_contribution: DF.Check
		legal_entities_covered: DF.SmallText | None
		payment_gateway: DF.Literal["Stripe", "Bank Transfer"]
		payment_intent: DF.Data | None
		payments: DF.Table[EnterpriseContractPayment]
		plan: DF.Link
		plan_title: DF.Data | None
		price_lock_years: DF.Int
		price_locked_until: DF.Date | None
		signed_contract: DF.Attach | None
		start_date: DF.Date
		status: DF.Literal["Awaiting Payment", "Pending Signature", "Active", "Cancelled"]
		team: DF.Link
		transfer_reference: DF.Data | None
		yearly_price: DF.Currency
	# end: auto-generated types

	def before_insert(self):
		self.validate_no_open_contract()
		self.validate_no_awaiting_order()
		if not self.plan_doc.enabled:
			frappe.throw("This plan is no longer available. Please choose another plan.")
		self.set_billing_details()
		# Set here, not by fetch: the site's default currency fills the field first.
		self.currency = frappe.db.get_value("Team", self.team, "currency")
		self.yearly_price = self.plan_doc.get_price(self.currency)
		self.payment_gateway = "Bank Transfer" if self.currency == "INR" else "Stripe"

	def after_insert(self):
		# A contract staff create in Desk must be visible to the team on the dashboard.
		frappe.db.set_value("Team", self.team, "enable_enterprise_contracts", 1)

	def onload(self):
		# Desk shows the bank transfer buttons from these.
		self.set_onload("payment_due", self.payment_due())
		self.set_onload("pending_transfer_reference", self.pending_transfer_reference())

	def validate(self):
		self.validate_price_lock_years()
		self.price_locked_until = add_days(add_years(self.start_date, self.price_lock_years), -1)
		self.set_status()

	@property
	def plan_doc(self) -> EnterpriseWarrantyPlan:
		return frappe.get_cached_doc("Enterprise Warranty Plan", self.plan)

	# Billing details are kept on the team; the contract records the ones it was ordered with.
	def set_billing_details(self):
		billing_name, billing_address = frappe.db.get_value(
			"Team", self.team, ["billing_name", "billing_address"]
		)
		if not billing_address:
			frappe.throw("Add your billing details before placing an Enterprise order")
		self.billing_name = billing_name
		self.billing_address = billing_address

	def validate_no_open_contract(self):
		# A locking read, because the InnoDB snapshot can miss a contract committed while we waited.
		filters = {"team": self.team, "status": ("in", OPEN_STATUSES)}
		if frappe.db.get_value("Enterprise Contract", filters, "name", for_update=True):
			frappe.throw("This team already has an Enterprise contract")

	# A dashboard order has cancelled the old one by now. In Desk, staff must settle it first,
	# because it can hold a UTR or a card payment that is still open.
	def validate_no_awaiting_order(self):
		filters = {"team": self.team, "status": "Awaiting Payment"}
		if name := frappe.db.get_value("Enterprise Contract", filters, "name"):
			frappe.throw(
				f"This team has order {name} waiting for payment. Confirm its bank transfer, or ask the customer to cancel it on the dashboard, then create the contract."
			)

	def validate_price_lock_years(self):
		self.price_lock_years = cint(self.price_lock_years)
		if self.price_lock_years not in self.plan_doc.price_lock_years:
			frappe.throw(f"Price lock period must be 1 to {self.plan_doc.max_price_lock_years} years")

	def set_status(self):
		if self.status == "Pending Signature" and self.agreement_date and self.signed_contract:
			self.status = "Active"

	def amount_due(self, with_gst: bool = True) -> dict:
		return amount_due(self.renewal_price(), self.currency, with_gst)

	def renewal_opens_on(self):
		return add_days(self.next_period_start(), -RENEWAL_WINDOW_DAYS)

	# A renewal is never charged by itself; the customer or staff start it once this is open.
	def renewal_open(self) -> bool:
		return self.status in OPEN_STATUSES and getdate(today()) >= getdate(self.renewal_opens_on())

	def payment_due(self) -> bool:
		return self.status == "Awaiting Payment" or self.renewal_open()

	# A card payment was started but not finished, for example when its window was closed.
	def payment_unfinished(self) -> bool:
		return bool(self.payment_due() and self.payment_intent and not self.has_payment(self.payment_intent))

	def validate_payment_due(self):
		if not self.payment_due():
			frappe.throw(f"Nothing is due on this contract now. Renewal opens on {self.renewal_opens_on()}.")

	def pay_with_credits(self):
		self.validate_payment_due()
		amount = self.amount_due(with_gst=False)["amount"]
		if purchased_credit(self.team) < amount:
			frappe.throw(
				"Not enough credits to pay for the full year. Please buy more credits or choose another payment method."
			)
		transaction = frappe.get_doc(
			doctype="Balance Transaction",
			team=self.team,
			type="Adjustment",
			currency=self.currency,
			amount=-amount,
			description=f"Paid for Enterprise Contract {self.name}",
		)
		transaction.flags.consume_sources = PURCHASED_CREDIT_SOURCES
		# Team members cannot create balance transactions; callers check billing access.
		transaction.insert(ignore_permissions=True)
		transaction.submit()
		self.record_payment(reference=transaction.name, paid_with="Credits", with_gst=False)

	# The UTR waiting to be confirmed. One that is already on a payment was left by a
	# contract paid before the UTR was cleared on payment, so it waits for nothing.
	def pending_transfer_reference(self) -> str | None:
		if self.transfer_reference and not self.has_payment(self.transfer_reference):
			return self.transfer_reference
		return None

	def has_payment(self, reference: str) -> bool:
		return any(row.payment_reference == reference for row in self.payments)

	def record_payment(self, reference: str, paid_with: str, with_gst: bool = True):
		if self.has_payment(reference):
			return
		if not self.payments:
			# The contract starts on the day the first payment lands, not the order day.
			self.start_date = today()
		start = self.next_period_start()
		due = self.amount_due(with_gst)
		self.append(
			"payments",
			{
				"period_start": start,
				"period_end": add_days(add_years(start, 1), -1),
				"amount": due["amount"],
				"gst": due["gst"],
				# Kept with the payment, so a later address edit does not relabel it.
				"gst_split": gst_split(self.billing_address),
				"amount_paid": due["total"],
				"paid_with": paid_with,
				"payment_reference": reference,
				"paid_on": now_datetime(),
			},
		)
		if self.status == "Awaiting Payment":
			self.status = "Pending Signature"
		if reference == self.transfer_reference:
			# The UTR is on the payment now; a renewal transfer gets a new one.
			self.transfer_reference = None
		# Team members only have read access; callers check billing access.
		self.save(ignore_permissions=True)

	def submit_transfer_reference(self, reference: str):
		if self.payment_gateway != "Bank Transfer":
			frappe.throw("This contract is paid by card or credits. Please use the Pay button.")
		self.validate_payment_due()
		reference = (reference or "").strip().upper()
		if not UTR_PATTERN.fullmatch(reference):
			frappe.throw("Enter the 12 to 22 character UTR number from your bank")
		self.transfer_reference = reference
		# Team members only have read access; callers check billing access.
		self.save(ignore_permissions=True)

	def cancel_order(self):
		if self.status != "Awaiting Payment":
			frappe.throw(
				"Only an order waiting for payment can be cancelled. A paid contract stays until its year ends."
			)
		if self.transfer_reference:
			frappe.throw("You have already sent a bank transfer for this order. Please contact support.")
		self.status = "Cancelled"
		# Team members only have read access; callers check billing access.
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def confirm_bank_transfer(self, reference: str | None = None):
		# Staff with write access (System Manager, Press Billing Manager); customers only read.
		self.check_permission("write")
		self.validate_payment_due()
		if reference:
			self.submit_transfer_reference(reference)
		if utr := self.pending_transfer_reference():
			self.record_payment(reference=utr, paid_with="Bank transfer")
			return
		frappe.throw("Enter the UTR from the bank statement to record this transfer")

	def next_period_start(self):
		if not self.payments:
			return getdate(self.start_date)
		return add_days(getdate(self.payments[-1].period_end), 1)

	def renewal_price(self):
		if getdate(self.next_period_start()) <= getdate(self.price_locked_until):
			return self.yearly_price
		return self.plan_doc.get_price(self.currency)

	def as_dashboard(self) -> dict:
		return {
			**{field: self.get(field) for field in DASHBOARD_FIELDS},
			"transfer_reference": self.pending_transfer_reference(),
			"payments": [payment_for_dashboard(row) for row in reversed(self.payments)],
			"next_renewal": {"date": self.next_period_start(), "amount": self.renewal_price()},
			"amount_due": self.amount_due(),
			"amount_due_with_credits": self.amount_due(with_gst=False),
			"gst_split": gst_split(self.billing_address),
			"payment_due": self.payment_due(),
			"payment_unfinished": self.payment_unfinished(),
			"renewal_opens_on": self.renewal_opens_on(),
			"coverage": (self.plan_doc.coverage or "").strip().splitlines(),
			"activity": contract_activity(self),
		}


def step(title: str, status: str, date=None, description: str = "") -> dict:
	return {"title": title, "status": status, "date": date, "description": description}


def period_text(row) -> str:
	return f"{formatdate(row.period_start, 'd MMM yyyy')} to {formatdate(row.period_end, 'd MMM yyyy')}"


# What has happened to the contract and what comes next, oldest first. Status values are
# the ones the dashboard's pipeline icons use.
def contract_activity(contract: EnterpriseContract) -> list[dict]:
	steps = [step("Order placed", "Success", contract.creation, f"by {contract.owner}")]
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
	if contract.renewal_open():
		return step("Next renewal", "Pending", None, f"Renewal is open. Renew before {start}.")
	opens = formatdate(contract.renewal_opens_on(), "d MMM yyyy")
	return step("Next renewal", "Pending", None, f"Next year starts {start}. Renewal opens on {opens}.")


def payment_for_dashboard(row) -> dict:
	fields = (
		"period_start",
		"period_end",
		"amount",
		"gst",
		"gst_split",
		"amount_paid",
		"paid_with",
		"payment_reference",
		"paid_on",
		"frappe_invoice",
		"invoice_pdf",
	)
	return {field: row.get(field) for field in fields}


def team_contracts(team: str) -> list[dict]:
	return frappe.get_all(
		"Enterprise Contract",
		{"team": team},
		[
			"name",
			"plan_title",
			"status",
			"currency",
			"yearly_price",
			"start_date",
			"price_locked_until",
		],
		order_by="creation desc",
	)


def open_contract_name(team: str) -> str | None:
	return frappe.db.get_value(
		"Enterprise Contract",
		{"team": team, "status": ("in", VISIBLE_STATUSES)},
		"name",
		order_by="creation desc",
	)


# Serializes orders for a team, so two at once cannot both pass the open-contract check.
def lock_team_orders(team: str):
	frappe.db.get_value("Team", team, "name", for_update=True)


def create_contract(team: Team, order: dict) -> EnterpriseContract:
	lock_team_orders(team.name)
	if team.currency == "INR" and not bank_transfer_details():
		frappe.throw("Bank transfer details are not set up yet. Please contact support.")
	cancel_unpaid_orders(team.name)
	contract = frappe.get_doc(
		{
			"doctype": "Enterprise Contract",
			"team": team.name,
			**{field: order.get(field) for field in ORDER_FIELDS},
		}
	)
	# Team members have no create permission; the API checks billing access.
	contract.insert(ignore_permissions=True)
	return contract


# An order the customer left unpaid is replaced by the new one.
# The API has closed its card payment by now, because a paid one must not raise here.
def cancel_unpaid_orders(team: str):
	frappe.db.set_value(
		"Enterprise Contract", {"team": team, "status": "Awaiting Payment"}, "status", "Cancelled"
	)


def bank_transfer_details() -> dict | None:
	settings = frappe.get_cached_doc("Press Settings")
	if not settings.bank_account_number:
		return None
	fields = ("bank_account_name", "bank_name", "bank_branch", "bank_account_number", "bank_ifsc_code")
	return {field: settings.get(field) for field in fields}


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Enterprise Contract")
