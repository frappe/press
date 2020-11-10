# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe


def create_test_server(proxy_server):
	"""Create test Server doc."""
	return frappe.get_doc(
		{
			"doctype": "Server",
			"status": "Active",
			"mariadb_root_password": "admin",
			"proxy_server": proxy_server,
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"name": frappe.mock("domain_name"),
			"agent_password": frappe.mock("password"),
		}
	).insert(ignore_if_duplicate=True)


class TestServer(unittest.TestCase):
	pass
