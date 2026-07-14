# Copyright (c) 2019, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from unittest.mock import Mock, patch

import frappe
from frappe.core.utils import find
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase
from moto import mock_aws

from press.agent import Agent
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.server import BaseServer, sync_wazuh_agent_status
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
			"use_for_new_sites": 1 if public else 0,
			"use_for_new_benches": 1 if public else 0,
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

	@patch.object(BaseServer, "_archive", new=Mock())
	@patch.object(BaseServer, "disable_subscription", new=Mock())
	def test_release_group_modifications_on_archival(self):
		server = create_test_server()
		other_servers = create_test_server()
		one_more_server = create_test_server()
		apps = [create_test_app()]
		group1 = create_test_release_group(apps, public=True, servers=[server.name])
		group2 = create_test_release_group(apps, public=True, servers=[server.name, other_servers.name])
		group3 = create_test_release_group(
			apps, public=True, servers=[server.name, other_servers.name, one_more_server.name]
		)

		# Test the archival of this server
		server.archive()

		# Reload groups
		group1.reload()
		group2.reload()
		group3.reload()

		# Test only group with that one server is disbled, others remain enabled
		self.assertEqual(group1.enabled, 0)
		self.assertEqual(group2.enabled, 1)
		self.assertEqual(group3.enabled, 1)

		# Test the server is removed from all groups that had more than one server
		self.assertListEqual([s.server for s in group2.servers], [other_servers.name])
		self.assertListEqual([s.server for s in group3.servers], [other_servers.name, one_more_server.name])

	@patch.object(Agent, "get", return_value={"benches": ["bench1", "bench2"]})
	def test_process_running_benches_on_server(self, mock_get):
		from press.press.doctype.server.server import _process_running_benches_on_server

		server = create_test_server()
		bench_1 = create_test_bench(server=server.name)
		bench_2 = create_test_bench(server=server.name)

		frappe.db.set_value("Bench", bench_1.name, "name", "bench1")
		frappe.db.set_value("Bench", bench_2.name, "name", "bench2")

		_process_running_benches_on_server(server.name)
		mock_get.assert_called_once_with("/server/running-benches")

		agent_job_created = frappe.get_all(
			"Agent Job", {"server": server.name, "job_type": "Force Remove Zombie Benches"}, pluck="name"
		)
		self.assertEqual(
			len(agent_job_created), 0
		)  # Benches not marked as archived, so no agent job should be created

		frappe.db.set_value("Bench", "bench1", "status", "Archived")
		frappe.db.set_value("Bench", "bench2", "status", "Archived")

		_process_running_benches_on_server(server.name)
		mock_get.assert_called_with("/server/running-benches")

		agent_job_created = frappe.get_all(
			"Agent Job", {"server": server.name, "job_type": "Force Remove Zombie Benches"}, ["name", "data"]
		)
		self.assertEqual(
			len(agent_job_created), 1
		)  # Benches marked as archived, so agent job should be created to force remove zombie benches

	def test_server_with_more_memory_is_shortlisted_for_new_benches_and_incident_created_against_shortlisted_server_with_insufficient_memory(
		self,
	):
		"""The server with higher available memory must be selected (use_for_new_benches=1)."""
		from press.press.doctype.cluster.test_cluster import create_test_cluster
		from press.press.doctype.incident.incident import Incident
		from press.press.doctype.server.server import _refresh_bench_pool_and_raise_capacity_incidents

		self.cluster = create_test_cluster("Default", public=True)
		# Two servers in the same cluster with different memory levels
		self.low_mem_server = create_test_server(cluster=self.cluster.name, public=True)
		self.high_mem_server = create_test_server(cluster=self.cluster.name, public=True)

		memory_map = {
			self.low_mem_server.name: 200 * 1024 * 1024,  # 200 MiB
			self.high_mem_server.name: 500 * 1024 * 1024,  # 500 MiB
		}

		_refresh_bench_pool_and_raise_capacity_incidents(
			server_names=[self.low_mem_server.name, self.high_mem_server.name],
			servers_by_cluster={self.cluster.name: [self.low_mem_server.name, self.high_mem_server.name]},
			memory_map=memory_map,
		)

		self.assertEqual(frappe.db.get_value("Server", self.high_mem_server.name, "use_for_new_benches"), 1)
		self.assertEqual(frappe.db.get_value("Server", self.low_mem_server.name, "use_for_new_benches"), 0)

		# Set both servers below threshold; high_mem_server is still the best candidate
		memory_map = {
			self.low_mem_server.name: 50 * 1024 * 1024,  # 50 MiB
			self.high_mem_server.name: 100 * 1024 * 1024,  # 100 MiB — best, but still < 300 MiB
		}

		with patch.object(Incident, "after_insert", new=Mock()):
			_refresh_bench_pool_and_raise_capacity_incidents(
				server_names=[self.low_mem_server.name, self.high_mem_server.name],
				servers_by_cluster={self.cluster.name: [self.low_mem_server.name, self.high_mem_server.name]},
				memory_map=memory_map,
			)

		incidents = frappe.get_all(
			"Incident",
			{
				"cluster": self.cluster.name,
				"subject": f"Insufficient bench capacity in cluster {self.cluster.name}",
			},
			["name", "server"],
		)
		self.assertEqual(len(incidents), 1)
		self.assertEqual(incidents[0].server, self.high_mem_server.name)

	def test_validate_mounts_seeds_snapshot_volume_not_doomed_default_volume(self):
		"""A server built from a data disk snapshot first boots with the VMI's default data
		volume, which is then deleted and replaced by the volume created from the snapshot.
		validate_mounts must not seed mounts off the doomed default volume — otherwise the
		mount keeps a deleted volume id and its by-id device path, and the Mount Volumes
		playbook fails. It should seed only after the snapshot volume is attached."""
		database_server = create_test_database_server()
		virtual_machine = database_server.virtual_machine
		default_volume_id = f"vol-{frappe.generate_hash(11)}"
		snapshot_volume_id = f"vol-{frappe.generate_hash(11)}"

		# VM has booted with root + the VMI's default data volume, snapshot swap still pending
		self._set_virtual_machine_volumes(
			virtual_machine,
			[
				{"device": "/dev/sda1", "size": 8, "volume_id": f"vol-{frappe.generate_hash(11)}"},
				{"device": "/dev/sdf", "size": 600, "volume_id": default_volume_id},
			],
		)
		frappe.db.set_value(
			"Virtual Machine",
			virtual_machine,
			{
				"has_data_volume": True,
				"data_disk_snapshot": "dummy-snapshot",
				"data_disk_snapshot_attached": False,
			},
		)

		database_server.validate_mounts()
		self.assertEqual(
			len(database_server.mounts),
			0,
			"Mounts must not be seeded off the default volume while the snapshot swap is pending",
		)

		# Default volume deleted, snapshot volume created and attached
		self._set_virtual_machine_volumes(
			virtual_machine,
			[
				{"device": "/dev/sda1", "size": 8, "volume_id": f"vol-{frappe.generate_hash(11)}"},
				{"device": "/dev/sdf", "size": 600, "volume_id": snapshot_volume_id},
			],
		)
		frappe.db.set_value("Virtual Machine", virtual_machine, "data_disk_snapshot_attached", True)

		database_server.validate_mounts()

		volume_mount = find(database_server.mounts, lambda m: m.mount_type == "Volume")
		self.assertIsNotNone(volume_mount, "A volume mount should be seeded after the snapshot is attached")
		self.assertEqual(volume_mount.volume_id, snapshot_volume_id)
		self.assertNotEqual(volume_mount.volume_id, default_volume_id)
		self.assertIn(snapshot_volume_id.replace("-", ""), volume_mount.source)

	def _set_virtual_machine_volumes(self, virtual_machine: str, volumes: list[dict]):
		frappe.db.delete("Virtual Machine Volume", {"parent": virtual_machine})
		for volume in volumes:
			frappe.get_doc(
				{
					"doctype": "Virtual Machine Volume",
					"parenttype": "Virtual Machine",
					"parent": virtual_machine,
					"parentfield": "volumes",
					"volume_type": "gp3",
					"throughput": 125,
					"device": volume["device"],
					"size": volume["size"],
					"volume_id": volume["volume_id"],
				}
			).insert()

	def test_disable_auto_storage_on_database_server_clears_db_flag_not_app_flag(self):
		database_server = create_test_database_server()
		frappe.db.set_value("Database Server", database_server.name, "auto_increase_storage", True)
		server = create_test_server(database_server=database_server.name, auto_increase_storage=True)

		# Dashboard always dispatches on the app server, passing the real target as `server`.
		server.configure_auto_add_storage(server=database_server.name, enabled=False)

		self.assertFalse(
			frappe.db.get_value("Database Server", database_server.name, "auto_increase_storage")
		)
		self.assertTrue(frappe.db.get_value("Server", server.name, "auto_increase_storage"))

	def test_disable_auto_storage_on_app_server_clears_app_flag(self):
		server = create_test_server(auto_increase_storage=True)

		server.configure_auto_add_storage(server=server.name, enabled=False)

		self.assertFalse(frappe.db.get_value("Server", server.name, "auto_increase_storage"))

	def test_configure_auto_storage_rejects_another_teams_database_server(self):
		"""The dashboard API only team-checks the app server. A Press User must not be able to
		flip auto_increase_storage on another team's Database Server by passing its name as the
		`server` argument — the disable path writes via set_value, which skips permission hooks."""
		from frappe.tests.ui_test_helpers import create_test_user

		attacker_email = frappe.mock("email")
		create_test_user(attacker_email)
		attacker = frappe.get_doc("User", {"email": attacker_email})
		attacker.remove_roles(*frappe.get_all("Role", pluck="name"))
		attacker.add_roles("Press User")
		attacker_team = create_test_team(attacker_email)

		own_database_server = create_test_database_server()
		frappe.db.set_value("Database Server", own_database_server.name, "team", attacker_team.name)
		server = create_test_server(database_server=own_database_server.name, team=attacker_team.name)

		victim_database_server = create_test_database_server()
		frappe.db.set_value(
			"Database Server",
			victim_database_server.name,
			{"team": create_test_team().name, "auto_increase_storage": True},
		)

		with self.set_user(attacker_team.user), self.assertRaises(frappe.PermissionError):
			server.configure_auto_add_storage(server=victim_database_server.name, enabled=False)

		self.assertTrue(
			frappe.db.get_value("Database Server", victim_database_server.name, "auto_increase_storage")
		)

	def _one_server_of_each_type(self):
		"""App, database and proxy servers all inherit the Wazuh methods from BaseServer."""
		return [
			create_test_server(),
			create_test_database_server(),
			create_test_proxy_server(),
		]

	def test_wazuh_agent_installed_during_setup_when_manager_configured(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_server", "wazuh.example.com")

		for server in self._one_server_of_each_type():
			with self.subTest(server_type=server.doctype):
				with patch.object(BaseServer, "install_wazuh_agent") as install_wazuh_agent:
					server.install_wazuh_agent_if_configured()
				install_wazuh_agent.assert_called_once()

	def test_wazuh_agent_not_installed_during_setup_when_manager_unconfigured(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_server", "")

		for server in self._one_server_of_each_type():
			with self.subTest(server_type=server.doctype):
				with patch.object(BaseServer, "install_wazuh_agent") as install_wazuh_agent:
					server.install_wazuh_agent_if_configured()
				install_wazuh_agent.assert_not_called()

	def test_install_marks_wazuh_agent_installed_on_successful_play(self):
		for server in self._one_server_of_each_type():
			with self.subTest(server_type=server.doctype):
				with patch("press.press.doctype.server.server.Ansible") as Ansible:
					Ansible.return_value.run.return_value = Mock(status="Success")
					server._install_wazuh_agent("wazuh.example.com")
				server.reload()
				self.assertTrue(server.is_wazuh_agent_installed)

	def test_uninstall_clears_wazuh_agent_installed_flag_and_status(self):
		for server in self._one_server_of_each_type():
			with self.subTest(server_type=server.doctype):
				server.db_set("is_wazuh_agent_installed", True)
				server.db_set("wazuh_agent_status", "active")
				with patch("press.press.doctype.server.server.Ansible") as Ansible:
					Ansible.return_value.run.return_value = Mock(status="Success")
					server._uninstall_wazuh_agent()
				server.reload()
				self.assertFalse(server.is_wazuh_agent_installed)
				self.assertIsNone(server.wazuh_agent_status)

	def test_uninstall_reloads_before_save_to_preserve_concurrent_writes(self):
		"""The long play window must not clobber edits made concurrently (e.g. archival)."""
		server = create_test_server()
		server.db_set("is_wazuh_agent_installed", True)
		# A concurrent edit lands in the DB while the (mocked) play is "running".
		frappe.db.set_value("Server", server.name, "status", "Broken")

		with patch("press.press.doctype.server.server.Ansible") as Ansible:
			Ansible.return_value.run.return_value = Mock(status="Success")
			server._uninstall_wazuh_agent()

		server.reload()
		self.assertFalse(server.is_wazuh_agent_installed)
		self.assertEqual(server.status, "Broken")

	def test_uninstall_is_noop_when_wazuh_agent_not_installed(self):
		for server in self._one_server_of_each_type():
			with self.subTest(server_type=server.doctype):
				server.db_set("is_wazuh_agent_installed", False)
				with patch("press.press.doctype.server.server.Ansible") as Ansible:
					server._uninstall_wazuh_agent()
				Ansible.return_value.run.assert_not_called()

	def test_setup_auditd_marks_auditd_setup_on_successful_play(self):
		for server in self._one_server_of_each_type():
			with self.subTest(server_type=server.doctype):
				with patch("press.press.doctype.server.server.Ansible") as Ansible:
					Ansible.return_value.run.return_value = Mock(status="Success")
					server._setup_auditd()
				server.reload()
				self.assertTrue(server.is_auditd_setup)

	def test_base_playbook_marks_auditd_setup_except_for_self_hosted(self):
		"""The base setup playbooks bundle auditd; their self-hosted variants do not."""
		for server in self._one_server_of_each_type():
			with self.subTest(server_type=server.doctype):
				server.is_self_hosted = 0
				server.is_auditd_setup = False
				server.set_auditd_setup_from_base_playbook()
				self.assertTrue(server.is_auditd_setup)

				server.is_self_hosted = 1
				server.is_auditd_setup = False
				server.set_auditd_setup_from_base_playbook()
				self.assertFalse(server.is_auditd_setup)

	@patch.object(BaseServer, "_archive", new=Mock())
	@patch.object(BaseServer, "disable_subscription", new=Mock())
	def test_archival_uninstalls_wazuh_agent_when_installed(self):
		server = create_test_server()
		server.db_set("is_wazuh_agent_installed", True)
		with patch.object(BaseServer, "uninstall_wazuh_agent") as uninstall_wazuh_agent:
			server.archive()
		uninstall_wazuh_agent.assert_called_once()

	@patch.object(BaseServer, "_archive", new=Mock())
	@patch.object(BaseServer, "disable_subscription", new=Mock())
	def test_archival_skips_wazuh_uninstall_when_not_installed(self):
		server = create_test_server()
		server.db_set("is_wazuh_agent_installed", False)
		with patch.object(BaseServer, "uninstall_wazuh_agent") as uninstall_wazuh_agent:
			server.archive()
		uninstall_wazuh_agent.assert_not_called()

	@patch.object(BaseServer, "_archive", new=Mock())
	@patch.object(BaseServer, "disable_subscription", new=Mock())
	def test_archival_deregisters_wazuh_agent_when_api_configured(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_api_url", "https://wazuh.example.com:55000")
		server = create_test_server()
		with patch.object(BaseServer, "deregister_wazuh_agent") as deregister_wazuh_agent:
			server.archive()
		deregister_wazuh_agent.assert_called_once()

	@patch.object(BaseServer, "_archive", new=Mock())
	@patch.object(BaseServer, "disable_subscription", new=Mock())
	def test_archival_skips_wazuh_deregister_when_api_unconfigured(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_api_url", "")
		server = create_test_server()
		with patch.object(BaseServer, "deregister_wazuh_agent") as deregister_wazuh_agent:
			server.archive()
		deregister_wazuh_agent.assert_not_called()

	def test_sync_wazuh_agent_status_updates_installed_servers_from_manager(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_api_url", "https://wazuh.example.com:55000")
		server = create_test_server()
		server.db_set("is_wazuh_agent_installed", True)

		with patch("press.press.doctype.server.server.WazuhManager") as WazuhManager:
			WazuhManager.return_value.agent_statuses.return_value = {server.name: "active"}
			sync_wazuh_agent_status()

		self.assertEqual(frappe.db.get_value("Server", server.name, "wazuh_agent_status"), "active")

	def test_sync_wazuh_agent_status_marks_missing_agents_unknown(self):
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_api_url", "https://wazuh.example.com:55000")
		server = create_test_server()
		server.db_set("is_wazuh_agent_installed", True)

		with patch("press.press.doctype.server.server.WazuhManager") as WazuhManager:
			WazuhManager.return_value.agent_statuses.return_value = {}
			sync_wazuh_agent_status()

		self.assertEqual(frappe.db.get_value("Server", server.name, "wazuh_agent_status"), "unknown")

	def test_sync_wazuh_agent_status_skips_archived_servers(self):
		"""An archived server must not be re-stamped every run once the agent is gone."""
		create_test_press_settings()
		frappe.db.set_single_value("Press Settings", "wazuh_api_url", "https://wazuh.example.com:55000")
		server = create_test_server()
		server.db_set("is_wazuh_agent_installed", True)
		server.db_set("wazuh_agent_status", "active")
		server.db_set("status", "Archived")

		with patch("press.press.doctype.server.server.WazuhManager") as WazuhManager:
			WazuhManager.return_value.agent_statuses.return_value = {}
			sync_wazuh_agent_status()

		self.assertEqual(frappe.db.get_value("Server", server.name, "wazuh_agent_status"), "active")

	def test_wazuh_manager_delete_agent_deletes_looked_up_agent_by_id(self):
		from press.wazuh import WazuhManager

		settings = create_test_press_settings()
		settings.wazuh_api_url = "https://wazuh.example.com:55000"
		settings.wazuh_api_username = "user"
		settings.wazuh_api_password = "pass"
		settings.wazuh_api_verify_tls = 0
		settings.save()

		with patch("press.wazuh.requests") as requests:
			requests.post.return_value.json.return_value = {"data": {"token": "t"}}
			requests.request.return_value.json.return_value = {
				"data": {"affected_items": [{"id": "003", "name": "wazuh-target"}]}
			}
			WazuhManager().delete_agent("wazuh-target")

		delete_call = requests.request.call_args_list[-1]
		self.assertEqual(delete_call.args[0], "DELETE")
		self.assertEqual(delete_call.kwargs["params"]["agents_list"], "003")

	def test_wazuh_manager_delete_agent_ignores_non_exact_name_match(self):
		"""A crafted name that broadens the `q` filter must not delete a different agent."""
		from press.wazuh import WazuhManager

		settings = create_test_press_settings()
		settings.wazuh_api_url = "https://wazuh.example.com:55000"
		settings.wazuh_api_username = "user"
		settings.wazuh_api_password = "pass"
		settings.wazuh_api_verify_tls = 0
		settings.save()

		with patch("press.wazuh.requests") as requests:
			requests.post.return_value.json.return_value = {"data": {"token": "t"}}
			# The filter resolved to a different agent ("victim") than the requested name.
			requests.request.return_value.json.return_value = {
				"data": {"affected_items": [{"id": "003", "name": "victim"}]}
			}
			WazuhManager().delete_agent("victim;status=active")

		methods = [call.args[0] for call in requests.request.call_args_list]
		self.assertNotIn("DELETE", methods)
