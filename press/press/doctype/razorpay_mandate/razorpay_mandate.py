# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils.billing import get_razorpay_client


class RazorpayMandate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auth_type: DF.Literal["upi", "netbanking", "debitcard"]
		expires_on: DF.Date | None
		failure_reason: DF.SmallText | None
		is_default: DF.Check
		mandate_id: DF.Data | None
		max_amount: DF.Currency
		method: DF.Literal["emandate", "card", "nach"]
		razorpay_customer_id: DF.Data | None
		status: DF.Literal["Pending", "Authorized", "Active", "Paused", "Cancelled", "Expired"]
		team: DF.Link
		token_id: DF.Data | None
		umn: DF.Data | None
		upi_vpa: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		# Ensure team has razorpay_customer_id
		team = frappe.get_doc("Team", self.team)
		if not team.razorpay_customer_id:
			team.create_razorpay_customer()
		self.razorpay_customer_id = team.razorpay_customer_id

	def after_insert(self):
		# If this is set as default, unset other defaults for the team
		if self.is_default:
			self.unset_other_defaults()

	def on_update(self):
		if self.has_value_changed("is_default") and self.is_default:
			self.unset_other_defaults()

	def unset_other_defaults(self):
		frappe.db.sql(
			"""
			UPDATE `tabRazorpay Mandate`
			SET is_default = 0
			WHERE team = %s AND name != %s AND is_default = 1
			""",
			(self.team, self.name),
		)

	def activate(self, token_id: str, umn: str | None = None, upi_vpa: str | None = None):
		"""Activate the mandate after successful authorization"""
		self.token_id = token_id
		self.status = "Active"
		if umn:
			self.umn = umn
		if upi_vpa:
			self.upi_vpa = upi_vpa
		self.save(ignore_permissions=True)

	def cancel(self, reason: str | None = None):
		"""Cancel the mandate"""
		self.status = "Cancelled"
		if reason:
			self.failure_reason = reason
		self.save(ignore_permissions=True)

	def pause(self):
		"""Pause the mandate"""
		self.status = "Paused"
		self.save(ignore_permissions=True)

	def resume(self):
		"""Resume a paused mandate"""
		if self.status == "Paused":
			self.status = "Active"
			self.save(ignore_permissions=True)

	def is_valid(self) -> bool:
		"""Check if mandate is valid for charging"""
		if self.status != "Active":
			return False
		if self.expires_on and frappe.utils.getdate(self.expires_on) < frappe.utils.getdate():
			return False
		return True

	@dashboard_whitelist()
	def set_default(self):
		"""Set this mandate as default for the team"""
		if self.status != "Active":
			frappe.throw("Only active mandates can be set as default")

		# Unset other defaults
		self.unset_other_defaults()

		# Set this as default
		self.is_default = 1
		self.save()

		# Update team's default razorpay mandate and payment mode
		frappe.db.set_value("Team", self.team, "default_razorpay_mandate", self.name)

		# Set payment mode if not already set
		current_payment_mode = frappe.db.get_value("Team", self.team, "payment_mode")
		if not current_payment_mode or current_payment_mode == "Prepaid Credits":
			frappe.db.set_value("Team", self.team, "payment_mode", "UPI Autopay")

	@dashboard_whitelist()
	def check_mandate_status(self):
		"""Check mandate status from Razorpay"""
		if not self.mandate_id:
			return None

		client = get_razorpay_client()
		try:
			invoice = client.invoice.fetch(self.mandate_id)
			return invoice.get("status")
		except Exception:
			return None

	def on_trash(self):
		"""Handle cleanup when mandate is deleted"""
		if self.is_default:
			frappe.db.set_value("Team", self.team, "default_razorpay_mandate", None)
			# Reset payment mode if it was UPI Autopay
			if frappe.db.get_value("Team", self.team, "payment_mode") == "UPI Autopay":
				frappe.db.set_value("Team", self.team, "payment_mode", "")

	def after_delete(self):
		"""Cancel mandate on Razorpay when deleted locally"""
		if self.mandate_id and self.status == "Active":
			try:
				client = get_razorpay_client()
				client.invoice.cancel(self.mandate_id)
			except Exception:
				pass  # Ignore errors during cleanup


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Razorpay Mandate")


def create_razorpay_mandate(
	team: str,
	max_amount: int,
	auth_type: str = "upi",
	expire_by: int | None = None,
) -> dict:
	"""
	Create a Razorpay mandate registration and return authorization link.

	Args:
		team: Team name
		max_amount: Maximum amount in INR
		auth_type: 'upi' or 'netbanking'
		expire_by: Unix timestamp for authorization link expiry (optional)

	Returns:
		dict with mandate_name and authorization_link
	"""
	from press.utils import log_error

	try:
		team_doc = frappe.get_doc("Team", team)

		# Ensure customer exists
		if not team_doc.razorpay_customer_id:
			team_doc.create_razorpay_customer()

		client = get_razorpay_client()

		# Default expire_by to 7 days from now if not provided
		if not expire_by:
			expire_by = int(frappe.utils.add_days(None, 7).timestamp())

		# Create subscription registration (mandate)
		registration_data = {
			"type": "link",
			"amount": 0,  # 0 for registration, actual amount during charge
			"currency": "INR",
			"description": "Frappe Cloud Recurring Payment Authorization",
			"subscription_registration": {
				"method": "emandate",
				"auth_type": auth_type,
				"bank_account": {
					"beneficiary_name": team_doc.billing_name or team_doc.user,
					"account_type": "savings",
				},
			},
			"receipt": f"mandate_{team}_{frappe.utils.now_datetime().timestamp()}",
			"customer_id": team_doc.razorpay_customer_id,
			"max_amount": max_amount * 100,  # Convert to paise
			"expire_by": expire_by,
			"notify": {"sms": True, "email": True},
			"notes": {"team": team, "purpose": "Frappe Cloud Billing"},
		}

		invoice = client.invoice.create(data=registration_data)

		# Calculate expires_on date from expire_by timestamp
		expires_on = frappe.utils.get_datetime_str(
			frappe.utils.datetime.datetime.fromtimestamp(expire_by)
		).split(" ")[0]

		# Create mandate record
		mandate = frappe.get_doc(
			{
				"doctype": "Razorpay Mandate",
				"team": team,
				"razorpay_customer_id": team_doc.razorpay_customer_id,
				"mandate_id": invoice.get("id"),
				"status": "Pending",
				"method": "emandate",
				"auth_type": auth_type,
				"max_amount": max_amount,
				"expires_on": expires_on,
			}
		).insert(ignore_permissions=True)

		return {
			"mandate_name": mandate.name,
			"mandate_id": invoice.get("id"),
			"authorization_link": invoice.get("short_url"),
			"expires_on": expires_on,
		}

	except Exception:
		log_error(
			"Razorpay Mandate Creation Failed",
			team=team,
			max_amount=max_amount,
			auth_type=auth_type,
		)
		raise
