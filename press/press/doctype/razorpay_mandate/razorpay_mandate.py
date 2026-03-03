# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from datetime import datetime

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date

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
		authorization_fee: DF.Currency
		authorization_fee_tax: DF.Currency
		contact: DF.Data | None
		error_code: DF.Data | None
		expires_on: DF.Date | None
		failure_reason: DF.SmallText | None
		is_default: DF.Check
		mandate_id: DF.Data | None
		max_amount: DF.Currency
		method: DF.Literal["emandate", "card", "nach"]
		payment_id: DF.Data | None
		razorpay_customer_id: DF.Data | None
		razorpay_signature: DF.SmallText | None
		rrn: DF.Data | None
		status: DF.Literal["Pending", "Authorized", "Active", "Paused", "Cancelled", "Expired", "Failed"]
		team: DF.Link
		token_id: DF.Data | None
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

	def activate(
		self,
		token_id: str,
		upi_vpa: str | None = None,
		authorization_payment_id: str | None = None,
		contact: str | None = None,
		rrn: str | None = None,
		authorization_fee: int | None = None,
		authorization_fee_tax: int | None = None,
		razorpay_signature: str | None = None,
	):
		"""Activate the mandate after successful authorization"""
		self.status = "Active"
		self.token_id = token_id
		self.upi_vpa = upi_vpa
		self.authorization_payment_id = authorization_payment_id
		self.contact = contact
		self.rrn = rrn
		self.razorpay_signature = razorpay_signature
		# Convert from paise to rupees
		self.authorization_fee = authorization_fee / 100 if authorization_fee else None
		self.authorization_fee_tax = authorization_fee_tax / 100 if authorization_fee_tax else None
		self.save(ignore_permissions=True)

	def mark_failed(
		self,
		error_code: str | None = None,
		error_description: str | None = None,
		error_source: str | None = None,
		error_step: str | None = None,
		error_reason: str | None = None,
	):
		"""Mark mandate as failed with error details"""
		self.status = "Failed"
		self.error_code = error_code
		# Combine all error details into failure_reason
		error_parts = [
			f"Description: {error_description}" if error_description else None,
			f"Source: {error_source}" if error_source else None,
			f"Step: {error_step}" if error_step else None,
			f"Reason: {error_reason}" if error_reason else None,
		]
		self.failure_reason = "\n".join(filter(None, error_parts)) or None
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
		print(f"DEBUG: team from get_current_team() = {team}")
		print(f"DEBUG: team exists? = {frappe.db.exists('Team', team)}")
		team_doc = frappe.get_doc("Team", team)
		customer = team_doc.create_razorpay_customer()
		print("Razorpay customer:", customer)
		client = get_razorpay_client()
		now = datetime.now()
		expire_by = add_to_date(now, years=15)
		current_timestamp = int(now.timestamp())
		expire_by_timestamp = int(expire_by.timestamp())
		# start_at should be
		order_response = client.order.create(
			{
				"amount": 100,
				"currency": "INR",
				"method": "upi",
				"customer_id": customer,
				"receipt": "Authorize UPI Autopay",
				"notes": {
					"notes_key_1": team,
					"notes_key_2": current_timestamp,
				},
				"token": {
					# "auth_type":"netbanking",
					"max_amount": max_amount * 100,  # Send amount in paisa
					"frequency": "monthly",
					"expire_at": expire_by_timestamp,
					"recurring_value": 18,
					"recurring_type": "before",
				},
			}
		)
		print("Razorpay order response:", order_response)
		order_id = order_response.get("id")
		# Create mandate record
		mandate = frappe.get_doc(
			{
				"doctype": "Razorpay Mandate",
				"team": team,
				"razorpay_customer_id": team_doc.razorpay_customer_id,
				"mandate_id": order_id,
				"status": "Pending",
				"method": "emandate",
				"auth_type": "upi",
				"max_amount": max_amount,
				"expires_on": expire_by,
			}
		).insert(ignore_permissions=True)

		return {
			"mandate_name": mandate.name,
			"customer_id": customer,
			"order_id": order_id,
			"key_id": client.auth[0],  # Razorpay key for checkout
		}

	except Exception:
		log_error(
			"Razorpay Mandate Creation Failed",
			team=team,
			max_amount=max_amount,
			auth_type=auth_type,
		)
		raise
