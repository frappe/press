# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.proxy_server.proxy_server import ProxyServer
from press.press.doctype.server.server import BaseServer
from press.press.doctype.virtual_machine.test_virtual_machine import create_test_virtual_machine
from press.utils.test import foreground_enqueue_doc


@patch.object(BaseServer, "after_insert", new=Mock())
@patch.object(ProxyServer, "validate_domains", new=Mock())
def create_test_proxy_server(
	hostname: str = "n",
	domain: str = "fc.dev",
	domains: list[dict[str, str]] | None = None,
	cluster: str = "Default",
	is_primary: bool = True,
	is_static_ip: bool = False,
) -> ProxyServer:
	"""Create test Proxy Server doc"""
	if domains is None:
		domains = [{"domain": "fc.dev"}]
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
			"is_primary": is_primary,
			"is_static_ip": is_static_ip,
			"virtual_machine": create_test_virtual_machine().name,
		}
	).insert(ignore_if_duplicate=True)
	server.reload()
	return server


@patch("frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("press.press.doctype.proxy_failover.proxy_failover.Ansible", new=Mock)
class TestProxyServer(FrappeTestCase):
	def test_failover_document_creation(self):
		proxy1 = create_test_proxy_server(is_static_ip=True)
		proxy2 = create_test_proxy_server(is_primary=False)

		proxy2.db_set("primary", proxy1.name)
		proxy2.db_set("is_replication_setup", 1)
		proxy2.trigger_failover()

		self.assertTrue(
			frappe.db.exists("Proxy Failover", {"primary": proxy1.name, "secondary": proxy2.name})
		)
