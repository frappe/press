# Copyright (c) 2019, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from unittest.mock import Mock, patch

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.server.server import BaseServer
from press.press.doctype.server_plan.test_server_plan import create_test_server_plan
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.virtual_machine.test_virtual_machine import create_test_virtual_machine

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server


@patch.object(BaseServer, "after_insert", new=Mock())
def create_test_server(
	proxy_server: str | None = None,
	database_server: str | None = None,
	cluster: str = "Default",
	plan: str | None = None,
	team: str | None = None,
	public: bool = False,
	platform: str = "x86_64",
	use_for_build: bool = False,
	is_self_hosted: bool = False,
) -> "Server":
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
			"plan": plan,
			"public": public,
			"virtual_machine": create_test_virtual_machine().name,
			"platform": platform,
			"use_for_build": use_for_build,
			"is_self_hosted": is_self_hosted,
		}
	).insert()
	server.reload()
	return server


@patch.object(BaseServer, "after_insert", new=Mock())
class TestServer(FrappeTestCase):
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

	def test_subscription_creation_on_server_creation(self):
		create_test_press_settings()
		server_plan = create_test_server_plan()
		server = create_test_server(plan=server_plan.name)
		server.create_subscription(server.plan)
		subscription = frappe.get_doc(
			"Subscription",
			{"document_type": "Server", "document_name": server.name, "enabled": 1},
		)
		self.assertEqual(server.team, subscription.team)
		self.assertEqual(server.plan, subscription.plan)

	def test_new_subscription_on_server_team_update(self):
		create_test_press_settings()
		server_plan = create_test_server_plan()
		server = create_test_server(plan=server_plan.name)
		server.create_subscription(server.plan)
		subscription = frappe.get_doc(
			"Subscription",
			{"document_type": "Server", "document_name": server.name, "enabled": 1},
		)
		self.assertEqual(server.team, subscription.team)
		self.assertEqual(server.plan, subscription.plan)

		# update server team
		team2 = create_test_team()
		server.team = team2.name
		server.save()
		subscription = frappe.get_doc(
			"Subscription",
			{"document_type": "Server", "document_name": server.name, "enabled": 1},
		)
		self.assertEqual(server.team, subscription.team)
		self.assertEqual(server.plan, subscription.plan)

	def tearDown(self):
		frappe.db.rollback()
