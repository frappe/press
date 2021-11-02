# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals
from press.press.doctype.proxy_server.proxy_server import ProxyServer

import unittest
from typing import Dict, List
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)


@patch.object(ProxyServer, "validate", new=Mock())
def create_test_proxy_server(
	hostname: str = "n", domain: str = "fc.dev", domains: List[Dict[str, str]] = []
):
	"""Create test Proxy Server doc"""
	create_test_press_settings()
	return frappe.get_doc(
		{
			"doctype": "Proxy Server",
			"status": "Active",
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"hostname": hostname,
			"cluster": "Default",
			"domain": domain,
			"domains": domains,
		}
	).insert(ignore_if_duplicate=True)


class TestProxyServer(unittest.TestCase):
	pass
