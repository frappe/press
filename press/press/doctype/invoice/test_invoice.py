# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from unittest.mock import patch
from frappe.utils.data import add_days, today


class TestInvoice(unittest.TestCase):
	def test_invoice_add_usage_record(self):
		team = frappe.get_doc(
			doctype="Team", name="testuser@example.com", country="India", enabled=1
		).insert()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		for amount in [10, 20, 30]:
			usage_record = frappe.get_doc(doctype="Usage Record", team=team.name, amount=amount)
			usage_record.insert()
			usage_record.submit()

		invoice.reload()

		self.assertEqual(len(invoice.items), 3)
		self.assertEqual(invoice.total, 60)

		with patch.object(invoice, "create_stripe_invoice", return_value=None):
			invoice.submit()

		self.assertEqual(invoice.amount_due, 60)

	def test_invoice_cancel_usage_record(self):
		team = frappe.get_doc(
			doctype="Team", name="testuser@example.com", country="India", enabled=1
		).insert()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		usage_records = []
		for amount in [10, 20, 30, 40]:
			usage_record = frappe.get_doc(doctype="Usage Record", team=team.name, amount=amount)
			usage_record.insert()
			usage_record.submit()
			usage_records.append(usage_record)

		invoice.reload()

		self.assertEqual(len(invoice.items), 4)
		self.assertEqual(invoice.total, 100)

		# cancel usage record
		usage_records[0].cancel()
		invoice.reload()

		self.assertEqual(len(invoice.items), 3)
		self.assertEqual(invoice.total, 90)
		self.assertEqual(usage_records[0].invoice, None)

	def test_invoice_with_credits_less_than_total(self):
		team = frappe.get_doc(
			doctype="Team", name="testuser2@example.com", country="India", enabled=1
		).insert()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		for amount in [10, 20, 30]:
			usage_record = frappe.get_doc(doctype="Usage Record", team=team.name, amount=amount)
			usage_record.insert()
			usage_record.submit()

		self.assertEqual(team.get_balance(), 0)
		team.allocate_credit_amount(10, source="Free Credits")
		self.assertEqual(team.get_balance(), 10)

		invoice.reload()

		with patch.object(invoice, "create_stripe_invoice", return_value=None):
			invoice.submit()

		self.assertEqual(team.get_balance(), 0)
		self.assertEqual(invoice.total, 60)
		self.assertEqual(invoice.amount_due, 50)
		self.assertEqual(invoice.applied_credits, 10)

	def test_invoice_with_credits_more_than_total(self):
		team = frappe.get_doc(
			doctype="Team", name="testuser3@example.com", country="India", enabled=1
		).insert()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		for amount in [10, 20, 30]:
			usage_record = frappe.get_doc(doctype="Usage Record", team=team.name, amount=amount)
			usage_record.insert()
			usage_record.submit()

		self.assertEqual(team.get_balance(), 0)
		team.allocate_credit_amount(70, source="Free Credits")
		self.assertEqual(team.get_balance(), 70)

		invoice.reload()

		with patch.object(invoice, "create_stripe_invoice", return_value=None):
			invoice.submit()

		self.assertEqual(team.get_balance(), 10)
		self.assertEqual(invoice.total, 60)
		self.assertEqual(invoice.amount_due, 0)
		self.assertEqual(invoice.applied_credits, 60)

	def test_intersecting_invoices(self):
		team = frappe.get_doc(
			doctype="Team", name="testuser4@example.com", country="India", enabled=1
		).insert()

		invoice1 = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=frappe.utils.today(),
			period_end=frappe.utils.add_days(frappe.utils.today(), 5),
		).insert()

		invoice2 = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), 1),
			period_end=frappe.utils.add_days(frappe.utils.today(), 6),
		)

		invoice3 = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=frappe.utils.today(),
			period_end=frappe.utils.add_days(frappe.utils.today(), 5),
		)

		invoice4 = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), -2),
			period_end=frappe.utils.add_days(frappe.utils.today(), 3),
		)

		invoice5 = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=frappe.utils.add_days(invoice1.period_end, 1),
		)

		self.assertRaises(frappe.DuplicateEntryError, invoice2.insert)
		self.assertRaises(frappe.DuplicateEntryError, invoice3.insert)
		self.assertRaises(frappe.DuplicateEntryError, invoice4.insert)

		invoice5.insert()

	def tearDown(self):
		frappe.db.rollback()
