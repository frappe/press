# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.password import check_password
from press.www.signup import create_account_request, get_context


class TestSignUp(unittest.TestCase):
	def setUp(self):
		self.first_name = "First"
		self.last_name = "Last"
		self.email = "mail@example.com"
		self.password = "SomeVeryHardPassword@42"
		self.ip = "1.2.3.4"
		delete_all_requests_and_users(self.email)

	def test_signup_success(self):
		# Create Account Request and User on signup
		# Don't test for login
		frappe.session.user = "Guest"
		frappe.local.request_ip = self.ip
		request = create_account_request(
			self.first_name, self.last_name, self.email, self.password
		)
		self.assertIsNotNone(request)

		self.assertEqual(request.email, self.email)
		self.assertEqual(request.first_name, self.first_name)
		self.assertEqual(request.last_name, self.last_name)
		self.assertEqual(request.ip, self.ip)

		user = frappe.get_doc("User", self.email)
		self.assertEqual(user.email, self.email)
		self.assertEqual(user.name, self.email)
		self.assertEqual(user.first_name, self.first_name)
		self.assertEqual(user.last_name, self.last_name)
		self.assertEqual(check_password(self.email, self.password), self.email)

	def test_signup_page_redirect_when_non_guest(self):
		# Redirect to dashboard page when a logged in user visits signup page
		frappe.session.user = "Administrator"
		self.assertRaises(frappe.Redirect, get_context, {})
		self.assertEqual(frappe.local.flags.redirect_location, "dashboard/")

	def test_signup_page_redirect_when_guest(self):
		# Don't redirect
		frappe.session.user = "Guest"
		self.assertEqual(get_context({}), None)

	def tearDown(self):
		frappe.session.user = "Administrator"
		delete_all_requests_and_users(self.email)


def delete_all_requests_and_users(email):
	# Delete all Account Request and User docs for self.email
	for request in frappe.get_all("Account Request", {"email": email}):
		frappe.delete_doc("Account Request", request.name)
		frappe.delete_doc("User", email)
