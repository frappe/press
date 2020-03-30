# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe.utils import nowdate
from datetime import datetime
from press.utils.dateutils import get_formated_date
from press.press.doctype.stripe_webhook_log.stripe_webhook_log import set_status

class Payment(Document):
	def after_insert(self):
		self.update_team_status()
		self.create_ledger_entry()

	def create_ledger_entry(self):
		if self.status=='Paid':
			frappe.get_doc(
				{
					"doctype": "Credit Ledger Entry",
					"date": nowdate(),
					"team": self.team,
					"credit": self.amount,
					"debit": 0,
					"payment": self.name,
				}
			).insert()

	def update_team_status(self):
		if self.status=='Failed':
			frappe.db.set_value("Team", self.team, "status", "Suspended")

		if self.status=='Paid':
			frappe.db.set_value("Team", self.team, "status", "Active")

def handle_payment_logs():
	'''
		This function handles stripe payment events. It pull all Queued state webhook logs having event type
		`invoice.payment_failed` and `invoice.payment_succeeded`.

		If event type is payment failed,
			then it create a payment record stripe invoice payment link to it for manual payments.

		If event type is payment success,
			then first system checks for Failed state payment record against stripe invoice id
			if stripe invoice id matches it updates the payment status of existing record
			else it creates new payment record.
	'''
	for log in frappe.get_all("Stripe Webhook Log", {
			'event_type': ['in', ['invoice.payment_failed', 'invoice.payment_succeeded']],
			'status': 'Queued'
		}, ["data", "name", "event_type"]):

		set_status(log.name, 'In Progress')

		webhook_data = json.loads(log.data)
		invoice_data = webhook_data['data']['object']
		team = frappe.db.get_value("Team", {"profile_id": invoice_data['customer']})

		if log.event_type == 'invoice.payment_failed':
			create_payment_record("Failed", team, invoice_data)

		if log.event_type == 'invoice.payment_succeeded':
			existing_payment_record = frappe.db.get_value("Payment", {
					"stripe_invoice_id": invoice_data['id'], "status": "Failed"})

			if existing_payment_record:
				doc = frappe.get_doc("Payment", existing_payment_record)
				doc.status = 'Paid'
				doc.save()
				doc.load_from_db()

				doc.update_team_status()
				doc.create_ledger_entry()

			else:
				create_payment_record("Paid", team, invoice_data)

		set_status(log.name, 'Completed')

def create_payment_record(status, team, invoice_data):
	frappe.get_doc({
		"doctype": "Payment",
		"team": team,
		"amount" : invoice_data['total'],
		"currency": invoice_data['currency'].upper(),
		"date": get_formated_date(invoice_data['date']),
		"status": status,
		"stripe_invoice_id": invoice_data['id'],
		"payment_link": invoice_data['hosted_invoice_url'],
	}).insert()
