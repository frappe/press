# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_years, cint, getdate, now_datetime, today

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
ALREADY_PAID = "This order is already paid. You can find your contract in the Contracts list."
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
		checkout_reference: DF.Data | None
		contact_person: DF.Data | None
		currency: DF.Link
		designation: DF.Data | None
		legal_entities_covered: DF.SmallText | None
		payment_gateway: DF.Literal["Stripe", "Bank Transfer"]
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
		if not self.plan_doc.enabled:
			frappe.throw("This plan is no longer available. Please choose another plan.")
		if self.currency == "INR" and not bank_transfer_details():
			frappe.throw("Bank transfer details are not set up yet. Please contact support.")
		self.cancel_unpaid_contracts()
		self.set_billing_details()
		self.start_date = today()
		self.yearly_price = self.plan_doc.get_price(self.currency)
		self.payment_gateway = "Bank Transfer" if self.currency == "INR" else "Stripe"

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

	# An order the customer abandoned at checkout is replaced by the new one.
	# The API has closed its Stripe session by now, because a paid one must not raise here.
	def cancel_unpaid_contracts(self):
		frappe.db.set_value(
			"Enterprise Contract",
			{"team": self.team, "status": "Awaiting Payment"},
			"status",
			"Cancelled",
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

	def pay_with_credits(self):
		if self.status != "Awaiting Payment":
			frappe.throw(ALREADY_PAID)
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
		self.record_payment(reference=transaction.name, with_gst=False)

	def has_payment(self, reference: str) -> bool:
		return any(row.payment_reference == reference for row in self.payments)

	def record_payment(self, reference: str, with_gst: bool = True):
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
				"payment_reference": reference,
				"paid_on": now_datetime(),
			},
		)
		if self.status == "Awaiting Payment":
			self.status = "Pending Signature"
		# Team members only have read access; callers check billing access.
		self.save(ignore_permissions=True)

	def submit_transfer_reference(self, reference: str):
		if self.payment_gateway != "Bank Transfer":
			frappe.throw("This order is paid online. Please use the Pay button on the Contracts page.")
		reference = (reference or "").strip().upper()
		if not UTR_PATTERN.fullmatch(reference):
			frappe.throw("Enter the 12 to 22 character UTR number from your bank")
		self.transfer_reference = reference
		# Team members only have read access; callers check billing access.
		self.save(ignore_permissions=True)

	def cancel_order(self):
		if self.transfer_reference:
			frappe.throw("You have already sent a bank transfer for this order. Please contact support.")
		self.status = "Cancelled"
		# Team members only have read access; callers check billing access.
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def confirm_bank_transfer(self):
		frappe.only_for("System Manager")
		if not self.transfer_reference:
			frappe.throw("The customer has not entered a UTR yet")
		self.record_payment(reference=self.transfer_reference)

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
			"payments": [payment_for_dashboard(row) for row in reversed(self.payments)],
			"next_renewal": {"date": self.next_period_start(), "amount": self.renewal_price()},
			"amount_due": self.amount_due(),
			"amount_due_with_credits": self.amount_due(with_gst=False),
			"gst_split": gst_split(self.billing_address),
		}


def payment_for_dashboard(row) -> dict:
	fields = (
		"period_start",
		"period_end",
		"amount",
		"gst",
		"gst_split",
		"amount_paid",
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
	contract = frappe.get_doc(
		{
			"doctype": "Enterprise Contract",
			"team": team.name,
			"currency": team.currency,
			**{field: order.get(field) for field in ORDER_FIELDS},
		}
	)
	# Team members have no create permission; the API checks billing access.
	contract.insert(ignore_permissions=True)
	return contract


def bank_transfer_details() -> dict | None:
	settings = frappe.get_cached_doc("Press Settings")
	if not settings.bank_account_number:
		return None
	fields = ("bank_account_name", "bank_name", "bank_branch", "bank_account_number", "bank_ifsc_code")
	return {field: settings.get(field) for field in fields}


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Enterprise Contract")
