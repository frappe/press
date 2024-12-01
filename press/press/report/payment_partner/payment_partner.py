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
		{"label": _("Transaction ID"), "fieldname": "name", "fieldtype": "Link","options":"Payment Partner Transaction","width": 100},
		{"label": _("Team"), "fieldname": "team", "fieldtype": "Link", "options": "Team", "width": 150},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Payment Gateway"), "fieldname": "payment_gateway", "fieldtype": "Link","options":"Payment Gateway","width": 150},
		{"label": _("FC Amount"), "fieldname": "amount", "fieldtype": "Currency","options":"currency", "width": 120},
  		{"label": _("Actual Amount"), "fieldname": "actual_amount", "fieldtype": "Currency","options":"actual_currency", "width": 120},
		{"label": _("Exchange Rate"), "fieldname": "exchange_rate", "fieldtype": "Float", "width": 100},
		{"label": _("Payment Partner"), "fieldname": "payment_partner", "fieldtype": "Link", "options": "Team", "width": 150},
  		{"label": _("Submitted To Frappe"), "fieldname": "submitted_to_frappe", "fieldtype": "Check", "width": 150},
		{"label": _("Actual Currency"), "fieldname": "actual_currency", "fieldtype": "Link","options":"Currency", "width": 100, "hidden":1},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link","options":"Currency", "width": 100, "hidden":1},
	]


def get_data(filters):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))
  
	payment_record=frappe.qb.DocType("Payment Partner Transaction")
 
	query=frappe.qb.from_(payment_record)\
 	.select("name","team","payment_gateway","payment_partner","amount","actual_amount","submitted_to_frappe","posting_date","actual_currency","exchange_rate",
	).where(payment_record.docstatus == 1)
	
	query = apply_filters(query, filters, payment_record)
	data = query.run(as_dict=True)
	# Append currency to each record
	for record in data:
		record["currency"] = "USD"
		
	return data
	
  
def apply_filters(query, filters, payment_record):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	for filter_key, filter_value in filters.items():
		if filter_key == "from_date":
			query = query.where(payment_record.posting_date >= filter_value)
		elif filter_key == "to_date":
			query = query.where(payment_record.posting_date <= filter_value)
		elif filter_key == "team":
			query = query.where(payment_record.team == filter_value)
		elif filter_key == "payment_partner":
			query = query.where(payment_record.payment_partner == filter_value)
		elif filter_key == "payment_gateway":
			query = query.where(payment_record.payment_gateway == filter_value)
		elif filter_key == "submitted_to_frappe":
			query = query.where(payment_record.submitted_to_frappe == filter_value)
		elif filter_key == "docstatus":
			query = query.where(payment_record.docstatus == doc_status.get(filter_value, 0))
	
	return query

