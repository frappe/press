# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest

from press.press.doctype.team.test_team import create_test_team


class TestBalanceTransaction(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_team_balance(self):
		team = create_test_team()

		team.allocate_credit_amount(50, source="")
		self.assertEqual(team.get_balance(), 50)

		team.allocate_credit_amount(-10, source="")
		self.assertEqual(team.get_balance(), 40)

		team.allocate_credit_amount(100, source="")
		self.assertEqual(team.get_balance(), 140)

		self.assertEqual(frappe.db.count("Balance Transaction", {"team": team.name}), 3)
