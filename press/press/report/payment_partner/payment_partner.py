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
		{
			"label": _("Transaction ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Payment Partner Transaction",
			"width": 100,
		},
		{"label": _("Team"), "fieldname": "team", "fieldtype": "Link", "options": "Team", "width": 150},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{
			"label": _("Payment Gateway"),
			"fieldname": "payment_gateway",
			"fieldtype": "Link",
			"options": "Payment Gateway",
			"width": 150,
		},
		{
			"label": _("FC Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Actual Amount"),
			"fieldname": "actual_amount",
			"fieldtype": "Currency",
			"options": "actual_currency",
			"width": 120,
		},
		{"label": _("Exchange Rate"), "fieldname": "exchange_rate", "fieldtype": "Float", "width": 100},
		{
			"label": _("Payment Partner"),
			"fieldname": "payment_partner",
			"fieldtype": "Link",
			"options": "Team",
			"width": 150,
		},
		{
			"label": _("Submitted To Frappe"),
			"fieldname": "submitted_to_frappe",
			"fieldtype": "Check",
			"width": 150,
		},
		{
			"label": _("Actual Currency"),
			"fieldname": "actual_currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100,
			"hidden": 1,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100,
			"hidden": 1,
		},
	]


def get_data(filters):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be after To Date"))

	payment_record = frappe.qb.DocType("Payment Partner Transaction")

	query = (
		frappe.qb.from_(payment_record)
		.select(
			"name",
			"team",
			"payment_gateway",
			"payment_partner",
			"amount",
			"actual_amount",
			"submitted_to_frappe",
			"posting_date",
			"actual_currency",
			"exchange_rate",
		)
		.where(payment_record.docstatus == 1)
	)

	query = apply_filters(query, filters, payment_record)
	data = query.run(as_dict=True)
	for record in data:
		record["currency"] = "USD"

	return data


def apply_filters(query, filters, payment_record):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
	filter_map = {
		"from_date": lambda q, v: q.where(payment_record.posting_date >= v),
		"to_date": lambda q, v: q.where(payment_record.posting_date <= v),
		"team": lambda q, v: q.where(payment_record.team == v),
		"payment_partner": lambda q, v: q.where(payment_record.payment_partner == v),
		"payment_gateway": lambda q, v: q.where(payment_record.payment_gateway == v),
		"submitted_to_frappe": lambda q, v: q.where(payment_record.submitted_to_frappe == v),
		"docstatus": lambda q, v: q.where(payment_record.docstatus == doc_status.get(v, 0)),
	}

	for key, value in filters.items():
		if key in filter_map:
			query = filter_map[key](query, value)

	return query
