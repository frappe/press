# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.saas import account_request


class TestAccountRequest(FrappeTestCase):
	@patch("press.api.saas.check_subdomain_availability", return_value=True)
	def test_invalid_country_is_escaped_in_the_error(self, _):
		country = "<img src=x onerror=alert(1)>"

		with self.assertRaises(frappe.ValidationError) as context:
			account_request("subdomain", "guest@example.com", "Guest", "User", country, "frappe")

		message = str(context.exception)
		self.assertNotIn(country, message)
		self.assertIn(frappe.utils.escape_html(country), message)
