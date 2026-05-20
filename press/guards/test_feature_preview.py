# Copyright (c) 2024, Frappe and Contributors
# See license.txt
from __future__ import annotations

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase

from press.guards.feature_preview import beta_testing


class TestFeaturePreview(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_beta_function_executes_for_system_user(self):
		email = frappe.mock("email")
		create_test_user(email)
		frappe.db.sql("DELETE FROM `tabHas Role` WHERE `parent` = %s", (email,))
		frappe.db.set_value("User", email, "user_type", "System User")

		frappe.set_user(email)

		@beta_testing()
		def dummy_function():
			return "executed"

		result = dummy_function()
		self.assertEqual(result, "executed")

	def test_beta_function_throws_for_website_user(self):
		email = frappe.mock("email")
		create_test_user(email)
		frappe.db.sql("DELETE FROM `tabHas Role` WHERE `parent` = %s", (email,))
		frappe.db.set_value("User", email, "user_type", "Website User")

		frappe.set_user(email)

		frappe.cache.delete_value(f"user:{email}")

		@beta_testing()
		def dummy_function():
			return "executed"

		with self.assertRaises(frappe.ValidationError) as context:
			dummy_function()

		self.assertIn("beta testers", str(context.exception))

	def test_beta_function_preserves_function_name(self):
		@beta_testing()
		def my_test_function():
			pass

		self.assertEqual(my_test_function.__name__, "my_test_function")

	def test_beta_function_preserves_function_docstring(self):
		@beta_testing()
		def my_test_function():
			"""This is the docstring."""
			pass

		self.assertEqual(my_test_function.__doc__, "This is the docstring.")

	def test_beta_function_passes_arguments_correctly(self):
		frappe.set_user("Administrator")

		@beta_testing()
		def func_with_args(a, b, keyword=None):
			return f"{a}-{b}-{keyword}"

		result = func_with_args("x", "y", keyword="z")
		self.assertEqual(result, "x-y-z")
