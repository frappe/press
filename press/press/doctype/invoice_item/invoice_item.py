# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import cint


class InvoiceItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		description: DF.Data | None
		discount: DF.Currency
		discount_percentage: DF.Percent
		document_name: DF.DynamicLink | None
		document_type: DF.Link | None
		has_marketplace_payout_completed: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		plan: DF.Data | None
		quantity: DF.Float
		rate: DF.Currency
		site: DF.Link | None
	# end: auto-generated types

	pass


def get_item_description(item) -> str:
	"""Describe one invoice line. `item` is an Invoice Item row, or a dict of the same fields."""
	how_many_days = f"{cint(item.quantity)} day{'s' if item.quantity > 1 else ''}"

	if item.document_type == "Site" and item.plan:
		site_name = item.document_name.split(".archived")[0]
		plan = frappe.get_cached_value("Site Plan", item.plan, "plan_title")
		return f"{site_name} active for {how_many_days} on {plan} plan"

	if item.document_type in ["Server", "Database Server"]:
		# A server without a title would otherwise read "None active for 24 days".
		server_title = (
			frappe.get_cached_value(item.document_type, item.document_name, "title") or item.document_name
		)
		if item.plan == "Add-on Storage plan":
			return f"{server_title} Storage Add-on for {how_many_days}"
		return f"{server_title} active for {how_many_days}"

	if item.document_type == "Server Snapshot":
		return f"{item.document_name} stored for {how_many_days}"

	if item.document_type == "Marketplace App":
		app_title = (
			frappe.get_cached_value("Marketplace App", item.document_name, "title") or item.document_name
		)
		return f"Marketplace app {app_title} active for {how_many_days}"

	return "Prepaid Credits"
