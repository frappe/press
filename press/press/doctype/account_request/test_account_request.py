# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.permissions import get_roles
from frappe.utils.password import check_password


class TestAccountRequest(unittest.TestCase):
	def setUp(self):
		frappe.delete_doc("User", "mail@example.com")
		self.request = None

	def test_account_request_creation(self):
		first_name = "First"
		last_name = "Last"
		email = "mail@example.com"
		password = "SomeVeryHardPassword@42"

		request_dict = {
			"doctype": "Account Request",
			"first_name": first_name,
			"last_name": last_name,
			"email": email,
			"password": password,
			"ip": "1.2.3.4",
		}

		self.request = frappe.get_doc(request_dict)
		self.request.insert()
		self.assertIsNotNone(self.request.user)
		self.assertEqual(self.request.user, email)

		# Properties should transfer from Account Request to User
		user = frappe.get_doc("User", self.request.user)
		self.assertEqual(user.first_name, first_name)
		self.assertEqual(user.last_name, last_name)
		self.assertEqual(user.name, email)
		self.assertEqual(user.email, email)
		self.assertEqual(check_password(user.name, password), email)

		# Newly created user must have only "Press User" role
		roles = ["All", "Guest", "Press User"]
		self.assertEqual(sorted(get_roles(email)), roles)

	def tearDown(self):
		if self.request:
			frappe.delete_doc("Account Request", self.request.name)
		frappe.delete_doc("User", "mail@example.com")
