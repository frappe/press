# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"label": _("name"), "fieldname": "name", "fieldtype": "Link","options":"Mpesa Payment Record","width": 100},
		{"label": _("Team"), "fieldname": "team", "fieldtype": "Link", "options": "Team", "width": 150},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Transaction Type"), "fieldname": "transaction_type", "fieldtype": "Select", "width": 150},
		{"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency","options":"default_currency", "width": 120},
		{"label": _("FC Amount"), "fieldname": "trans_amount", "fieldtype": "Currency","options":"default_currency", "width": 120},
		{"label": _("FC Amount"), "fieldname": "amount_usd", "fieldtype": "Currency","options":"currency", "width": 120},
		{"label": _("Exchange Rate"), "fieldname": "exchange_rate", "fieldtype": "Float", "width": 100},
		{"label": _("MSISDN"), "fieldname": "msisdn", "fieldtype": "Data", "width": 120},
		{"label": _("Payment Partner"), "fieldname": "payment_partner", "fieldtype": "Link", "options": "Team", "width": 150},
		{"label": _("Default Currency"), "fieldname": "default_currency", "fieldtype": "Link","options":"Currency", "width": 100, "hidden":1},
		{"label": _("Balance Transaction"), "fieldname": "balance_transaction", "fieldtype": "Link","options":"Balance Transaction", "width": 150},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link","options":"Currency", "width": 100, "hidden":1},
	]


def get_data(filters):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))
  
	mpesa_record=frappe.qb.DocType("Mpesa Payment Record")
 
	query=frappe.qb.from_(mpesa_record)\
 	.select("name","team","transaction_type","merchant_request_id","trans_id","grand_total","exchange_rate","trans_amount","amount_usd","msisdn","payment_partner","invoice_number","posting_date","default_currency","balance_transaction",
	).where(mpesa_record.docstatus == 1)
	
	query = apply_filters(query, filters, mpesa_record)
	data = query.run(as_dict=True)
	# Append currency to each record
	for record in data:
		record["currency"] = "USD"
		
	return data
	
  
def apply_filters(query, filters, mpesa_record):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	for filter_key, filter_value in filters.items():
		if filter_key == "from_date":
			query = query.where(mpesa_record.posting_date >= filter_value)
		elif filter_key == "to_date":
			query = query.where(mpesa_record.posting_date <= filter_value)
		elif filter_key == "team":
			query = query.where(mpesa_record.team == filter_value)
		elif filter_key == "payment_partner":
			query = query.where(mpesa_record.payment_partner == filter_value)
		elif filter_key == "transaction_type":
			query = query.where(mpesa_record.transaction_type == filter_value)
		elif filter_key == "docstatus":
			query = query.where(mpesa_record.docstatus == doc_status.get(filter_value, 0))
	
	return query

