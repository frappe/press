# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class EnterpriseContractPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		amount_paid: DF.Currency
		frappe_invoice: DF.Data | None
		gst: DF.Currency
		invoice_pdf: DF.Attach | None
		paid_on: DF.Datetime | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_reference: DF.Data | None
		period_end: DF.Date
		period_start: DF.Date
	# end: auto-generated types

	pass
