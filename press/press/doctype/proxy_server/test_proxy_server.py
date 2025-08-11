# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase
from moto import mock_aws

from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.proxy_server.proxy_server import ProxyServer
from press.press.doctype.root_domain.root_domain import RootDomain
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
			"virtual_machine": create_test_virtual_machine().name,
		}
	).insert(ignore_if_duplicate=True)
	server.reload()
	return server


@patch(
	"press.press.doctype.proxy_server.proxy_server.frappe.enqueue_doc",
	foreground_enqueue_doc,
)
@patch("press.press.doctype.proxy_server.proxy_server.Ansible", new=Mock())
class TestProxyServer(FrappeTestCase):
	@fake_agent_job("Reload NGINX Job")
	@mock_aws
	@patch.object(
		RootDomain,
		"update_dns_records_for_sites",
		wraps=RootDomain.update_dns_records_for_sites,
		autospec=True,
	)
	def test_sites_dns_updated_on_failover(self, update_dns_records_for_sites):
		from press.press.doctype.server.test_server import create_test_server
		from press.press.doctype.site.test_site import create_test_site

		proxy1 = create_test_proxy_server()
		proxy2 = create_test_proxy_server(is_primary=False)

		root_domain: RootDomain = frappe.get_doc("Root Domain", proxy1.domain)
		root_domain.boto3_client.create_hosted_zone(
			Name=proxy1.domain,
			CallerReference="1",
			HostedZoneConfig={"Comment": "Test", "PrivateZone": False},
		)

		server = create_test_server(proxy1.name)
		site1 = create_test_site(server=server.name)
		create_test_site()  # another proxy; unrelated

		proxy2.db_set("primary", proxy1.name)
		proxy2.db_set("is_replication_setup", 1)
		proxy2.trigger_failover()
		update_dns_records_for_sites.assert_called_once_with(root_domain, [site1.name], proxy2.name)
		proxy2.reload()
		proxy1.reload()
		self.assertTrue(proxy2.is_primary)
		self.assertFalse(proxy1.is_primary)
		self.assertEqual(proxy2.status, "Active")
		self.assertEqual(proxy1.status, "Active")
