# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt


import unittest
import frappe

from typing import Optional
from datetime import datetime
from unittest.mock import patch

from press.press.doctype.account_request.account_request import AccountRequest


def create_test_account_request(
	subdomain: str,
	email: str = frappe.mock("email"),
	erpnext: bool = True,
	creation=datetime.now(),
	saas: bool = False,
	saas_app: Optional[str] = None,
):
	with patch.object(AccountRequest, "send_verification_email"):
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"subdomain": subdomain,
				"email": email,
				"erpnext": erpnext,
				"saas": saas,
				"saas_app": saas_app,
			}
		).insert(ignore_if_duplicate=True)
		account_request.db_set("creation", creation)
		account_request.reload()
		return account_request


class TestAccountRequest(unittest.TestCase):
	pass
