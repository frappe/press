# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import Mock, patch

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.database_server.test_database_server import create_test_database_server
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
	def tearDown(self):
		frappe.db.rollback()

	@patch("press.press.doctype.proxy_server.proxy_server.Ansible")
	def test_proxysql_monitor_uses_the_cluster_password_and_connects_to_the_database_server_directly(
		self, Mock_Ansible: Mock
	):
		cluster = create_test_cluster(name="Monitor Test")
		database_server = create_test_database_server(cluster="Monitor Test")
		proxy_server = create_test_proxy_server(cluster="Monitor Test")

		proxy_server.setup_proxysql_monitor()

		variables = Mock_Ansible.call_args.kwargs["variables"]
		monitor_password = cluster.get_password("mariadb_monitor_password")
		self.assertNotEqual(monitor_password, "monitor")
		self.assertEqual(variables["mariadb_monitor_password"], monitor_password)
		self.assertEqual(variables["database_server_private_ip"], database_server.private_ip)
		self.assertEqual(variables["database_server_port"], 3306)

	def test_proxysql_setup_skips_the_exporter_when_the_cluster_has_no_database_server(self):
		create_test_cluster(name="Empty Monitor Test")
		proxy_server = create_test_proxy_server(cluster="Empty Monitor Test")

		variables = proxy_server.get_proxysql_monitor_variables()

		self.assertNotIn("database_server_private_ip", variables)
		self.assertTrue(variables["mariadb_monitor_password"])

	def test_playbooks_do_not_set_the_default_monitor_password(self):
		playbooks = Path(frappe.get_app_path("press", "playbooks"))
		default_password = re.compile(r"password\W{1,3}monitor\b|'monitor',\s*'monitor'")
		offenders = [
			str(path.relative_to(playbooks))
			for path in playbooks.rglob("*")
			if path.is_file() and default_password.search(path.read_text(errors="ignore"))
		]
		self.assertEqual(offenders, [])

	def test_failover_document_creation(self):
		proxy1 = create_test_proxy_server(is_static_ip=True)
		proxy2 = create_test_proxy_server(is_primary=False)

		proxy2.db_set("primary", proxy1.name)
		proxy2.db_set("is_replication_setup", 1)
		proxy2.trigger_failover()

		self.assertTrue(
			frappe.db.exists("Proxy Failover", {"primary": proxy1.name, "secondary": proxy2.name})
		)
