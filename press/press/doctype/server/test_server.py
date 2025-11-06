# Copyright (c) 2019, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from unittest.mock import Mock, patch

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase
from moto import mock_aws

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.server import BaseServer
from press.press.doctype.server_plan.test_server_plan import create_test_server_plan
from press.press.doctype.site.test_site import create_test_bench
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.virtual_machine.test_virtual_machine import create_test_virtual_machine

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server
	from press.press.doctype.server_plan.server_plan import ServerPlan
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


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
	auto_increase_storage: bool = False,
	provider: str | None = None,
	has_data_volume: bool = False,
) -> "Server":
	"""Create test Server doc."""
	if not proxy_server:
		proxy_server = create_test_proxy_server().name
	if not database_server:
		database_server = create_test_database_server().name
	if not team:
		team = create_test_team().name

	plan_doc: "ServerPlan" | None = frappe.get_doc("Server Plan", plan) if plan else None

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
			"virtual_machine": create_test_virtual_machine(
				platform=plan_doc.platform if plan_doc else "x86_64",
				disk_size=plan_doc.disk if plan_doc else 25,
				has_data_volume=has_data_volume,
				series="f",
			).name,
			"platform": platform,
			"use_for_build": use_for_build,
			"is_self_hosted": is_self_hosted,
			"auto_increase_storage": auto_increase_storage,
			"provider": provider,
			"has_data_volume": has_data_volume,
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
		self.assertEqual(server.team, server.subscription.team)
		self.assertEqual(server.plan, server.subscription.plan)

	@mock_aws
	@patch.object(BaseServer, "enqueue_extend_ec2_volume", new=Mock())
	@patch("boto3.client")
	def test_subscription_creation_on_addon_storage(self, _):
		"""Test subscription creation with a fixed increment"""
		increment = 10
		create_test_press_settings()
		server_plan = create_test_server_plan()
		server: "Server" = create_test_server(plan=server_plan.name, provider="AWS EC2")
		plan_disk_size = server_plan.disk
		actual_disk_size = frappe.db.get_value("Virtual Machine", server.virtual_machine, "disk_size")
		self.assertEqual(plan_disk_size, actual_disk_size)

		vm: "VirtualMachine" = frappe.get_doc("Virtual Machine", server.virtual_machine)
		root_volume = vm.volumes[0]
		self.assertEqual(plan_disk_size, root_volume.size)

		server.increase_disk_size_for_server(server.name, increment=increment)
		new_actual_disk_size = frappe.db.get_value("Virtual Machine", server.virtual_machine, "disk_size")
		self.assertEqual(plan_disk_size + increment, new_actual_disk_size)

		subscription_doc = frappe.get_doc(
			"Subscription",
			{
				"team": server.team,
				"plan_type": "Server Storage Plan",
				"plan": "Add-on Storage Plan",
				"document_type": server.doctype,
				"document_name": server.name,
			},
		)

		self.assertEqual(subscription_doc.enabled, 1)

		self.assertEqual(int(subscription_doc.additional_storage), increment)

		# Increase by another 10
		server.increase_disk_size_for_server(server.name, increment=increment)
		new_actual_disk_size = frappe.db.get_value("Virtual Machine", server.virtual_machine, "disk_size")

		self.assertEqual(plan_disk_size + increment + increment, new_actual_disk_size)

		subscription_doc = frappe.get_doc(
			"Subscription",
			{
				"team": server.team,
				"plan_type": "Server Storage Plan",
				"plan": "Add-on Storage Plan",
				"document_type": server.doctype,
				"document_name": server.name,
			},
		)

		self.assertEqual(subscription_doc.enabled, 1)

		self.assertEqual(int(subscription_doc.additional_storage), increment + increment)

	def test_subscription_team_update_on_server_team_update(self):
		create_test_press_settings()
		server_plan = create_test_server_plan()
		server = create_test_server(plan=server_plan.name)

		self.assertEqual(server.team, server.subscription.team)
		self.assertEqual(server.plan, server.subscription.plan)

		# update server team
		team2 = create_test_team()
		server.team = team2.name
		server.save()
		self.assertEqual(server.team, server.subscription.team)

	def test_db_server_team_update_on_server_team_update(self):
		create_test_press_settings()
		server_plan = create_test_server_plan()
		db_server_plan = create_test_server_plan("Database Server")
		server = create_test_server(plan=server_plan.name)
		db_server = frappe.get_doc("Database Server", server.database_server)
		db_server.plan = db_server_plan.name
		db_server.save()

		self.assertEqual(server.team, db_server.team)

		# update server team
		team2 = create_test_team()
		server.team = team2.name
		server.save()
		server.reload()
		db_server.reload()
		self.assertEqual(server.team, db_server.team)
		self.assertEqual(server.subscription.team, server.team)
		self.assertEqual(server.subscription.team, db_server.subscription.team)

	def test_remove_from_public_groups_removes_server_from_release_groups_child_table(self):
		# Create three public release groups, add server to all
		server = create_test_server(public=True)
		apps = [create_test_app()]
		group1 = create_test_release_group(apps, public=True, servers=[server.name])
		group2 = create_test_release_group(apps, public=True, servers=[server.name])
		group3 = create_test_release_group(apps, public=True, servers=[server.name])

		# Add an active bench to group2 on the server
		bench = create_test_bench(group=group2, server=server.name)
		frappe.db.set_value("Bench", bench.name, "status", "Active")

		self.assertTrue(any(s.server == server.name for s in group2.servers))
		self.assertTrue(any(s.server == server.name for s in group3.servers))
		self.assertTrue(any(s.server == server.name for s in group1.servers))

		server.remove_from_public_groups()

		# Reload groups
		group1.reload()
		group2.reload()
		group3.reload()

		# Assert server removed from groups without active benches
		self.assertFalse(any(s.server == server.name for s in group1.servers))
		self.assertFalse(any(s.server == server.name for s in group3.servers))
		# Assert server still present in group2 (has active bench)
		self.assertTrue(any(s.server == server.name for s in group2.servers))

		server.remove_from_public_groups(force=True)
		group2.reload()
		# Assert server removed from group2
		self.assertFalse(any(s.server == server.name for s in group2.servers))
