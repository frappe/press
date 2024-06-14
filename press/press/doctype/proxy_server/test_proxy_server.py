# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase
from typing import Dict, List
from unittest.mock import Mock, patch

import frappe
from frappe.model.naming import make_autoname
from moto import mock_s3

from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.proxy_server.proxy_server import ProxyServer
from press.press.doctype.server.server import BaseServer
from press.utils.test import foreground_enqueue_doc


@patch.object(BaseServer, "after_insert", new=Mock())
@patch.object(ProxyServer, "validate_domains", new=Mock())
def create_test_proxy_server(
	hostname: str = "n",
	domain: str = "fc.dev",
	domains: List[Dict[str, str]] = [{"domain": "fc.dev"}],
	cluster: str = "Default",
) -> ProxyServer:
	"""Create test Proxy Server doc"""
	create_test_press_settings()
	server = frappe.get_doc(
		{
			"doctype": "Proxy Server",
			"status": "Active",
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"hostname": make_autoname(hostname + ".######"),
			"cluster": cluster,
			"domain": domain,
			"domains": domains,
		}
	).insert(ignore_if_duplicate=True)
	server.reload()
	return server


@patch(
	"press.press.doctype.proxy_server.proxy_server.frappe.enqueue_doc",
	foreground_enqueue_doc,
)
@mock_s3
@patch("press.press.doctype.proxy_server.proxy_server.Ansible", new=Mock())
class TestProxyServer(FrappeTestCase):
	@fake_agent_job("Reload NGINX Job")
	def test_sites_dns_updated_on_failover(self):
		proxy1 = create_test_proxy_server()
		proxy2 = create_test_proxy_server()
		proxy1.db_set("is_primary", 1)
		proxy2.db_set("primary", proxy1.name)
		proxy2.db_set("is_replication_setup", 1)
		proxy2.trigger_failover()
		self.assertTrue(proxy2.is_primary)
		self.assertFalse(proxy1.is_primary)
