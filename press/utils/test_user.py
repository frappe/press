# Copyright (c) 2024, Frappe and Contributors
# See license.txt
from __future__ import annotations

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase

from press.utils.user import is_beta_tester, is_desk_user, is_system_manager


class TestUserUtils(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_is_desk_user_returns_true_for_system_user(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "System User")

		self.assertTrue(is_desk_user(email))

	def test_is_desk_user_returns_false_for_website_user(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "Website User")

		self.assertFalse(is_desk_user(email))

	def test_is_desk_user_returns_false_for_website_user_no_roles(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "Website User")

		self.assertFalse(is_desk_user(email))

	def test_is_desk_user_uses_current_user_when_none_provided(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "System User")

		frappe.set_user(email)
		self.assertTrue(is_desk_user())

	def test_is_beta_tester_returns_true_for_system_user(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "System User")

		self.assertTrue(is_beta_tester(email))

	def test_is_beta_tester_returns_false_for_website_user(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "Website User")

		self.assertFalse(is_beta_tester(email))

	def test_is_system_manager_returns_true_for_system_user(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "System User")

		self.assertTrue(is_system_manager(email))

	def test_is_system_manager_returns_true_for_user_with_system_manager_role(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_doc("User", {"email": email})
		user.user_type = "Website User"
		user.add_roles("System Manager")
		user.save()

		self.assertTrue(is_system_manager(email))

	def test_is_system_manager_returns_false_for_regular_website_user(self):
		email = frappe.mock("email")
		create_test_user(email)
		frappe.db.sql("DELETE FROM `tabHas Role` WHERE `parent` = %s", (email,))
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "Website User")

		self.assertFalse(is_system_manager(email))

	def test_is_system_manager_uses_current_user_when_none_provided(self):
		email = frappe.mock("email")
		create_test_user(email)
		user = frappe.get_value("User", {"email": email}, "name")
		frappe.db.set_value("User", user, "user_type", "System User")

		frappe.set_user(email)
		self.assertTrue(is_system_manager())
