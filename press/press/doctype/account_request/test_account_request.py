# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.account_request.account_request import AccountRequest


def create_test_account_request(
	subdomain: str,
	email: str | None = None,
	erpnext: bool = True,
	creation=None,
	saas: bool = False,
	saas_app: str | None = None,
	product_trial: str | None = None,
):
	creation = creation or frappe.utils.now_datetime()
	email = email or frappe.mock("email")
	with patch.object(AccountRequest, "send_verification_email"):
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"subdomain": subdomain,
				"email": email,
				"erpnext": erpnext,
				"saas": saas,
				"saas_app": saas_app,
				"product_trial": product_trial,
				"otp": "",
			}
		).insert(ignore_if_duplicate=True)
		account_request.db_set("creation", creation)
		account_request.reload()
		return account_request


class TestAccountRequest(FrappeTestCase):
	def test_bare(self):
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"email": "hello@example.com",
			}
		)

		self.assertIsNotNone(account_request.insert())

	def test_temporary_email_providers(self):
		hosts = [
			"yopmail.com",
			"mailinator.com",
			"temp-mail.org",
			"10minutemail.com",
			"guerrillamail.com",
			"throwawaymail.com",
			"maildrop.cc",
			"getnada.com",
			"tempmailaddress.com",
			"dispostable.com",
		]

		for host in hosts:
			account_request = frappe.get_doc(
				{
					"doctype": "Account Request",
					"email": "hello@" + host,
				}
			)

			with self.assertRaises(frappe.ValidationError):
				account_request.insert()
