# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest


def create_test_database_server():
	"""Create test Database Server doc"""
	return frappe.get_doc(
		{
			"doctype": "Database Server",
			"status": "Active",
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"agent_password": frappe.mock("password"),
			"hostname": "m",
			"cluster": "Default",
		}
	).insert(ignore_if_duplicate=True)


class TestDatabaseServer(unittest.TestCase):
	pass
