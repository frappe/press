# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SaasSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.erpnext_app.erpnext_app import ERPNextApp

		app: DF.Link | None
		apps: DF.Table[ERPNextApp]
		billing_type: DF.Literal["prepaid", "postpaid"]
		cluster: DF.Link | None
		default_team: DF.Link | None
		domain: DF.Link | None
		email_account: DF.Link | None
		enable_hybrid_pools: DF.Check
		enable_pooling: DF.Check
		group: DF.Link | None
		multi_subscription: DF.Check
		multiplier_pricing: DF.Check
		plan: DF.Link | None
		site_plan: DF.Link | None
		standby_pool_size: DF.Int
		standby_queue_size: DF.Int
		whitelisted_apps: DF.Table[ERPNextApp]
	# end: auto-generated types

	pass
