# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)


def create_test_proxy_server():
	"""Create test Proxy Server doc"""
	create_test_press_settings()
	return frappe.get_doc(
		{
			"doctype": "Proxy Server",
			"status": "Active",
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"agent_password": frappe.mock("password"),
			"hostname": "n",
			"cluster": "Default",
		}
	).insert(ignore_if_duplicate=True)


class TestProxyServer(unittest.TestCase):
	pass
