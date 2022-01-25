# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest


class TestBalanceTransaction(unittest.TestCase):
	def test_team_balance(self):
		email = "testuser@example.com"
		team = frappe.get_doc(doctype="Team", name=email, country="India", enabled=1).insert()

		team.allocate_credit_amount(50, source="")
		self.assertEqual(team.get_balance(), 50)

		team.allocate_credit_amount(-10, source="")
		self.assertEqual(team.get_balance(), 40)

		team.allocate_credit_amount(100, source="")
		self.assertEqual(team.get_balance(), 140)

		self.assertEqual(frappe.db.count("Balance Transaction", {"team": team.name}), 3)

	def tearDown(self):
		frappe.db.rollback()
