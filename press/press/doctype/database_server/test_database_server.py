# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.core.utils import find
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.exceptions import MonitorServerDown
from press.press.doctype.database_server.database_server import DatabaseServer
from press.press.doctype.server.server import BaseServer
from press.press.doctype.virtual_machine.test_virtual_machine import create_test_virtual_machine
from press.runner import Ansible
from press.utils.test import foreground_enqueue_doc


@patch.object(BaseServer, "after_insert", new=Mock())
def create_test_database_server(ip=None, cluster="Default") -> DatabaseServer:
	"""Create test Database Server doc"""
	if not ip:
		ip = frappe.mock("ipv4")
	server = frappe.get_doc(
		{
			"doctype": "Database Server",
			"status": "Active",
			"ip": ip,
			"private_ip": frappe.mock("ipv4_private"),
			"db_port": 3306,
			"agent_password": frappe.mock("password"),
			"hostname": f"m{make_autoname('.##')}",
			"cluster": cluster,
			"ram": 16384,
			"virtual_machine": create_test_virtual_machine().name,
			"provider": "AWS EC2",
		}
	).insert(ignore_if_duplicate=True)
	server.reload()
	return server


def create_test_database_replica(primary: DatabaseServer) -> DatabaseServer:
	"""Create a Database Server already set up as a replica of primary"""
	replica = create_test_database_server()
	replica.is_primary = False
	replica.primary = primary.name
	# on_update forbids binlog auto purge once replication is set up, and new servers
	# default it on
	replica.auto_purge_binlog_based_on_size = False
	replica.is_replication_setup = True
	replica.save()
	return replica


@patch.object(Ansible, "run", new=Mock())
class TestDatabaseServer(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch(
		"press.press.doctype.database_server.database_server.Ansible",
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_mariadb_service_restarted_on_restart_mariadb_fn_call(self, Mock_Ansible: Mock):
		server = create_test_database_server()
		server.restart_mariadb()
		server.reload()  # modified timestamp datatype
		Mock_Ansible.assert_called_with(
			playbook="restart_mysql.yml",
			server=server,
			user=server.ssh_user or "root",
			port=server.ssh_port or 22,
			variables={
				"server": server.name,
			},
		)

	@patch(
		"press.press.doctype.database_server.database_server.Ansible",
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_memory_limits_updated_on_update_of_corresponding_fields(self, Mock_Ansible: MagicMock):
		server = create_test_database_server()
		server.memory_high = 1
		server.save()
		Mock_Ansible.assert_not_called()
		server.memory_max = 2
		server.save()
		server.reload()  # modified timestamp datatype

		Mock_Ansible.assert_called_with(
			playbook="database_memory_limits.yml",
			server=server,
			user=server.ssh_user or "root",
			port=server.ssh_port or 22,
			variables={
				"server": server.name,
				"memory_high": server.memory_high,
				"memory_max": server.memory_max,
				"memory_swap_max": 0.1,
			},
		)

	@patch(
		"press.press.doctype.database_server.database_server.Ansible",
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_reconfigure_mariadb_exporter_play_runs_on_reconfigure_fn_call(self, Mock_Ansible: Mock):
		server = create_test_database_server()
		server.reconfigure_mariadb_exporter()
		server.reload()
		Mock_Ansible.assert_called_with(
			playbook="reconfigure_mysqld_exporter.yml",
			server=server,
			user=server.ssh_user or "root",
			port=server.ssh_port or 22,
			variables={
				"private_ip": server.private_ip,
				"mariadb_root_password": server.get_password("mariadb_root_password"),
			},
		)

	@patch(
		"press.press.doctype.database_server.database_server.Ansible",
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_exception_on_failed_reconfigure_fn_call(self, Mock_Ansible: Mock):
		Mock_Ansible.side_effect = Exception()
		server = create_test_database_server()
		self.assertRaises(Exception, server.reconfigure_mariadb_exporter)  # noqa

	@patch.object(Agent, "configure_replication", return_value={"success": True})
	def test_configure_replication_disables_binlog_auto_purge_on_replica(self, _):
		"""New DB servers default binlog auto purge on, but on_update forbids it for
		replication-configured servers. configure_replication must clear the flag as the
		server becomes a replica instead of tripping that guard and failing provisioning."""
		primary = create_test_database_server()
		replica = create_test_database_server()
		replica.is_primary = False
		replica.primary = primary.name
		replica.auto_purge_binlog_based_on_size = True
		replica.is_replication_setup = False
		replica.save()

		replica.configure_replication()
		replica.reload()

		self.assertTrue(replica.is_replication_setup)
		self.assertFalse(replica.auto_purge_binlog_based_on_size)

	@patch.object(DatabaseServer, "_restart_mariadb")
	@patch.object(Agent, "configure_replication", return_value={"success": True})
	def test_configure_replication_starts_mariadb_before_contacting_agent(
		self, mock_agent_configure, mock_restart
	):
		"""Configure runs as a separate job from Prepare; a stopped MariaDB would fail
		with connection-refused in the agent. configure_replication must start MariaDB
		before contacting the agent."""
		call_order = []
		mock_restart.side_effect = lambda *a, **k: call_order.append("restart")
		mock_agent_configure.side_effect = lambda *a, **k: call_order.append("agent") or {"success": True}

		primary = create_test_database_server()
		replica = create_test_database_server()
		replica.is_primary = False
		replica.primary = primary.name
		replica.save()

		replica.configure_replication()

		mock_restart.assert_called_once()
		self.assertEqual(call_order, ["restart", "agent"])

	def test_replica_is_offered_only_the_actions_the_dashboard_supports(self):
		"""A replica used to be offered every database action, grouped as "Database Server
		Actions" so they merged into the primary's card. The dashboard doesn't whitelist
		the methods behind them for a replica, so those buttons did nothing when clicked."""
		replica = create_test_database_replica(create_test_database_server())

		actions = replica.get_actions()

		self.assertEqual({action["action"] for action in actions}, {"Rename server", "Reboot server"})
		self.assertEqual({action["group"] for action in actions}, {"Replication Server Actions"})

	def test_primary_of_a_replica_is_still_offered_its_database_actions(self):
		primary = create_test_database_server()
		create_test_database_replica(primary)

		actions = primary.get_actions()

		self.assertIn("Update Max DB Connections", {action["action"] for action in actions})
		self.assertEqual({action["group"] for action in actions}, {"Database Server Actions"})

	@patch("press.press.doctype.database_server.database_server.Ansible", new=Mock())
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_adjust_memory_config_sets_memory_limits_with_some_buffer(self):
		server = create_test_database_server()
		server.ram = 16384
		self.assertEqual(server.real_ram, 15707.248)
		self.assertEqual(server.ram_for_mariadb, 15007.248)
		server.adjust_memory_config()
		server.reload()
		self.assertEqual(server.memory_high, 13.656)
		self.assertEqual(server.memory_max, 14.656)
		self.assertEqual(
			find(
				server.mariadb_system_variables,
				lambda x: x.mariadb_variable == "innodb_buffer_pool_size",
			).value_int,
			int(15007.248 * 0.65),
		)

	@patch("press.api.server.prometheus_instant_value")
	def test_is_mariadb_up_reads_the_currently_scraped_mysql_up_value(self, mysql_up: Mock):
		server = create_test_database_server()

		mysql_up.return_value = 0.0
		self.assertFalse(server.is_mariadb_up(), "mysql_up=0 means MariaDB is down")

		mysql_up.return_value = 1.0
		self.assertTrue(server.is_mariadb_up(), "mysql_up=1 means MariaDB is up")

		self.assertEqual(
			mysql_up.call_args[0][0],
			f'mysql_up{{instance="{server.name}",job="mariadb"}}',
			"The scrape must be read for this database server's own instance",
		)

	@patch("press.api.server.prometheus_instant_value")
	def test_is_mariadb_up_treats_missing_monitoring_data_as_up(self, mysql_up: Mock):
		# A server without monitoring, or one Prometheus can't be reached for, must not look
		# down — that would block actions that depend on the check.
		server = create_test_database_server()

		mysql_up.return_value = None
		self.assertTrue(server.is_mariadb_up(), "No monitoring data should count as up")

		mysql_up.side_effect = MonitorServerDown("Unable to connect to monitor server")
		self.assertTrue(server.is_mariadb_up(), "An unreachable monitor server should count as up")

	@patch("press.api.server.get_decrypted_password", new=Mock(return_value="password"))
	@patch("press.api.server.requests.get")
	def test_prometheus_instant_value_treats_an_error_response_as_no_data(self, get: Mock):
		# Prometheus answers a bad or overloaded query with {"status": "error", ...} and no
		# "data" key. Reading it must not raise into the caller.
		frappe.db.set_single_value("Press Settings", "monitor_server", "monitor.example.com")
		get.return_value.json.return_value = {"status": "error", "errorType": "bad_data"}

		from press.api.server import prometheus_instant_value

		self.assertIsNone(prometheus_instant_value('mysql_up{instance="m1",job="mariadb"}'))
