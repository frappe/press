from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.saas import get_site_url_and_sid
from press.press.doctype.account_request.test_account_request import create_test_account_request
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site


class TestAPISaas(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.site = create_test_site()
		self.account_request = create_test_account_request(subdomain=self.site.subdomain)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def get_url(self, key):
		frappe.set_user("Guest")
		with (
			patch("press.api.saas.get_erpnext_domain", return_value=self.site.domain),
			patch.object(Site, "login_as_admin", return_value="https://site/app?sid=x"),
		):
			return get_site_url_and_sid(key)

	def test_setup_key_logs_in_once(self):
		key = self.account_request.request_key
		self.assertEqual(self.get_url(key), "https://site/app?sid=x")
		self.assertFalse(frappe.db.get_value("Account Request", self.account_request.name, "request_key"))

		with self.assertRaises(frappe.ValidationError):
			self.get_url(key)

	def test_expired_setup_key_is_rejected(self):
		self.account_request.db_set("request_key_expiration_time", frappe.utils.add_to_date(hours=-1))

		with self.assertRaises(frappe.ValidationError):
			self.get_url(self.account_request.request_key)
