# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from press.press.doctype.cluster.test_cluster import create_test_cluster


def create_test_proxy_server():
	"""Create test Proxy Server doc"""
	cluster = create_test_cluster()
	return frappe.get_doc(
		{
			"doctype": "Proxy Server",
			"status": "Active",
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"name": frappe.mock("domain_name"),
			"agent_password": frappe.mock("password"),
			"hostname": "n",
			"cluster": cluster.name,
		}
	).insert(ignore_if_duplicate=True)


class TestProxyServer(unittest.TestCase):
	pass
