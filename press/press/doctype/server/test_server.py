# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import Mock, patch

import frappe
import typing
from frappe.model.naming import make_autoname

from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.server.server import BaseServer
from press.press.doctype.team.test_team import create_test_team

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server


@patch.object(BaseServer, "after_insert", new=Mock())
def create_test_server(
	proxy_server=None,
	database_server=None,
	cluster: str = "Default",
	team: str = None,
) -> Server:
	"""Create test Server doc."""
	if not proxy_server:
		proxy_server = create_test_proxy_server().name
	if not database_server:
		database_server = create_test_database_server().name
	if not team:
		team = create_test_team().name
	server = frappe.get_doc(
		{
			"doctype": "Server",
			"status": "Active",
			"proxy_server": proxy_server,
			"database_server": database_server,
			"ip": frappe.mock("ipv4"),
			"private_ip": frappe.mock("ipv4_private"),
			"domain": "fc.dev",
			"hostname": make_autoname("f-.####"),
			"cluster": cluster,
			"new_worker_allocation": True,
			"ram": 16000,
			"team": team,
		}
	).insert()
	server.reload()
	return server


@patch.object(BaseServer, "after_insert", new=Mock())
class TestServer(unittest.TestCase):
	def test_create_generic_server(self):
		create_test_press_settings()
		proxy_server = create_test_proxy_server()
		database_server = create_test_database_server()

		server = frappe.get_doc(
			{
				"doctype": "Server",
				"hostname": frappe.mock("domain_word"),
				"domain": "fc.dev",
				"ip": frappe.mock("ipv4"),
				"private_ip": frappe.mock("ipv4_private"),
				"agent_password": frappe.mock("password"),
				"proxy_server": proxy_server.name,
				"database_server": database_server.name,
			}
		)
		server.insert()
		self.assertEqual(server.cluster, "Default")
		self.assertEqual(server.name, f"{server.hostname}.{server.domain}")

	def test_set_agent_password(self):
		create_test_press_settings()
		proxy_server = create_test_proxy_server()
		database_server = create_test_database_server()

		server = frappe.get_doc(
			{
				"doctype": "Server",
				"hostname": frappe.mock("domain_word"),
				"domain": "fc.dev",
				"ip": frappe.mock("ipv4"),
				"private_ip": frappe.mock("ipv4_private"),
				"proxy_server": proxy_server.name,
				"database_server": database_server.name,
			}
		)
		server.insert()
		self.assertEqual(len(server.get_password("agent_password")), 32)

	def tearDown(self):
		frappe.db.rollback()
