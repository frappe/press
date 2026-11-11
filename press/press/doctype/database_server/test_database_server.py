# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.core.utils import find
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.exceptions import MonitorServerDown
from press.press.doctype.database_server import database_server
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
	def test_is_mariadb_up_treats_missing_monitoring_data_as_down(self, mysql_up: Mock):
		# A one-shot restore a user triggers must not run on a guess, so it asks for proof.
		server = create_test_database_server()

		mysql_up.return_value = None
		self.assertFalse(server.is_mariadb_up(), "No monitoring data means no proof")

		mysql_up.side_effect = MonitorServerDown("Unable to connect to monitor server")
		self.assertFalse(server.is_mariadb_up(), "An unreachable monitor server means no proof")

	@patch("press.api.server.get_decrypted_password", new=Mock(return_value="password"))
	@patch("press.api.server.requests.get")
	def test_prometheus_instant_value_treats_an_error_response_as_no_data(self, get: Mock):
		# Prometheus answers a bad or overloaded query with {"status": "error", ...} and no
		# "data" key. Reading it must not raise into the caller.
		frappe.db.set_single_value("Press Settings", "monitor_server", "monitor.example.com")
		get.return_value.json.return_value = {"status": "error", "errorType": "bad_data"}

		from press.api.server import prometheus_instant_value

		self.assertIsNone(prometheus_instant_value('mysql_up{instance="m1",job="mariadb"}'))

	@patch.object(Agent, "purge_binlogs_by_size_limit")
	def test_binlog_purge_skipped_while_a_recent_purge_job_is_open(self, purge: Mock):
		server = create_test_database_server()
		create_test_binlog_purge_job(server, "Undelivered", hours_ago=0.1)

		server.purge_binlogs_by_configured_size_limit()

		purge.assert_not_called()

	@patch.object(Agent, "purge_binlogs_by_size_limit")
	def test_binlog_purge_runs_when_the_open_purge_job_is_older_than_an_hour(self, purge: Mock):
		# An undelivered job from months ago used to skip the purge forever, and the disk filled up.
		server = create_test_database_server()
		create_test_binlog_purge_job(server, "Undelivered", hours_ago=24 * 30)

		server.purge_binlogs_by_configured_size_limit()

		purge.assert_called_once()


def create_test_binlog_purge_job(server: DatabaseServer, status: str, hours_ago: float):
	"""Purge agent job inserted straight into the db, so no HTTP request gets queued."""
	creation = frappe.utils.add_to_date(None, hours=-hours_ago)
	frappe.get_doc(
		{
			"doctype": "Agent Job",
			"job_type": "Purge Binlogs By Size Limit",
			"status": status,
			"server": server.name,
			"server_type": "Database Server",
			"request_method": "POST",
			"request_path": "database/binlogs/purge_by_size_limit",
			"request_data": "{}",
			"creation": creation,
			"modified": creation,
		}
	).db_insert()


class TestForcePurgeBinlogsScript(FrappeTestCase):
	def setUp(self):
		self.binlog_dir = Path(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, self.binlog_dir)
		stub_bin = self.binlog_dir / "bin"
		stub_bin.mkdir()
		(stub_bin / "systemctl").write_text(f'#!/bin/sh\necho "$@" > {self.binlog_dir}/systemctl.log\n')
		(stub_bin / "systemctl").chmod(0o755)
		# Prints the checkpoint file if a test sets one, else the binlog it reads, as after a clean rotation
		(stub_bin / "mysqlbinlog").write_text(
			f'#!/bin/sh\ncp="$(cat {self.binlog_dir}/checkpoint 2>/dev/null || basename "$1")"\n'
			'echo "# at 256 Binlog checkpoint $cp"\n'
		)
		(stub_bin / "mysqlbinlog").chmod(0o755)
		self.env = {
			**os.environ,
			"BINLOG_DIR": str(self.binlog_dir),
			"PATH": f"{stub_bin}:{os.environ['PATH']}",
		}

	def create_binlogs(self, count: int):
		names = [f"mysql-bin.{number:06d}" for number in range(1, count + 1)]
		for name in names:
			(self.binlog_dir / name).write_text("binlog")
		(self.binlog_dir / "mysql-bin.index").write_text("".join(f"{self.binlog_dir}/{n}\n" for n in names))

	def run_script(self, no_of_binlogs: int) -> subprocess.CompletedProcess:
		script = Path(database_server.__file__).with_name("force_purge_binlogs.sh")
		return subprocess.run(
			["bash", str(script), str(no_of_binlogs)], env=self.env, capture_output=True, text=True
		)

	def binlogs_on_disk(self) -> list[str]:
		return sorted(p.name for p in self.binlog_dir.glob("mysql-bin.[0-9]*"))

	def binlogs_in_index(self) -> list[str]:
		return [Path(line).name for line in (self.binlog_dir / "mysql-bin.index").read_text().splitlines()]

	def test_force_purge_keeps_the_newest_binlog_when_asked_to_delete_all(self):
		# Crash recovery reads the newest binlog. Without it, MariaDB did not start after a disk-full crash.
		self.create_binlogs(3)

		result = self.run_script(130)

		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(self.binlogs_on_disk(), ["mysql-bin.000003"])
		self.assertEqual(self.binlogs_in_index(), ["mysql-bin.000003"])
		self.assertEqual((self.binlog_dir / "systemctl.log").read_text().strip(), "restart mariadb")

	def test_force_purge_removes_deleted_binlogs_from_the_index(self):
		# The old script left the index unchanged when it emptied it, so MariaDB failed on a missing file.
		self.create_binlogs(5)

		self.run_script(2)

		self.assertEqual(self.binlogs_on_disk(), ["mysql-bin.000003", "mysql-bin.000004", "mysql-bin.000005"])
		self.assertEqual(self.binlogs_in_index(), self.binlogs_on_disk())
		self.assertFalse((self.binlog_dir / "mysql-bin.index.tmp").exists())

	def test_force_purge_fails_without_a_change_when_only_the_newest_binlog_is_left(self):
		self.create_binlogs(1)

		result = self.run_script(5)

		self.assertEqual(result.returncode, 1)
		self.assertIn("Nothing to purge", result.stderr)
		self.assertEqual(self.binlogs_on_disk(), ["mysql-bin.000001"])
		self.assertFalse((self.binlog_dir / "systemctl.log").exists())

	def test_force_purge_keeps_the_binlogs_from_the_last_checkpoint_onward(self):
		# After a rotation the checkpoint can still point one binlog back, and recovery reads from there.
		self.create_binlogs(5)
		(self.binlog_dir / "checkpoint").write_text("mysql-bin.000004")

		self.run_script(130)

		self.assertEqual(self.binlogs_on_disk(), ["mysql-bin.000004", "mysql-bin.000005"])
		self.assertEqual(self.binlogs_in_index(), self.binlogs_on_disk())

	def test_force_purge_keeps_the_newest_two_binlogs_when_the_checkpoint_cannot_be_read(self):
		self.create_binlogs(5)
		(self.binlog_dir / "checkpoint").write_text("")

		self.run_script(130)

		self.assertEqual(self.binlogs_on_disk(), ["mysql-bin.000004", "mysql-bin.000005"])
