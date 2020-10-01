# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest


def create_test_proxy_server() -> 'ProxyServer':
    """Create test Proxy Server doc"""
    return frappe.get_doc({
        "doctype": "Proxy Server",
        "status": "Active",
        "ip": frappe.mock("ipv4"),
        "private_ip": frappe.mock("ipv4_private"),
        "name": frappe.mock("domain_name"),
    }).insert(ignore_if_duplicate=True)


class TestProxyServer(unittest.TestCase):
    pass
