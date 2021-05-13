# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from datetime import datetime

import frappe


def create_test_account_request(
	subdomain: str, erpnext: bool = True, creation=datetime.now()
):
	return frappe.get_doc(
		{
			"doctype": "Account Request",
			"subdomain": subdomain,
			"erpnext": erpnext,
			"creation": creation,
		}
	).insert(ignore_if_duplicate=True)


class TestAccountRequest(unittest.TestCase):
	pass
