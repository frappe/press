# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.core.utils import find
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

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

	@patch(
		"press.press.doctype.database_server.database_server.Ansible",
	)
	def test_setup_server_marks_server_active_on_success(self, Mock_Ansible):
		server = create_test_database_server()

		mock_play = Mock()
		mock_play.status = "Success"

		mock_ansible_instance = Mock()
		mock_ansible_instance.run.return_value = mock_play

		Mock_Ansible.return_value = mock_ansible_instance

		server._generate_secret = Mock(return_value="secret")
		server.sign_agent_token = Mock(return_value="signed-token")
		server._set_mount_status = Mock()
		server.process_hybrid_server_setup = Mock()
		server.reboot = Mock()

		server._setup_server()

		server.reload()

		Mock_Ansible.assert_called_once_with(
			playbook="database.yml",
			server=server,
			user=server.ssh_user or "root",
			port=server.ssh_port or 22,
			variables={
				"server_type": server.doctype,
				"server": server.name,
				"workers": "2",
				"agent_password": Mock_Ansible.call_args.kwargs["variables"]["agent_password"],
				"agent_repository_url": Mock_Ansible.call_args.kwargs["variables"]["agent_repository_url"],
				"agent_branch": Mock_Ansible.call_args.kwargs["variables"]["agent_branch"],
				"monitoring_password": Mock_Ansible.call_args.kwargs["variables"]["monitoring_password"],
				"log_server": Mock_Ansible.call_args.kwargs["variables"]["log_server"],
				"kibana_password": Mock_Ansible.call_args.kwargs["variables"]["kibana_password"],
				"agent_token": "signed-token",
				"private_ip": server.private_ip,
				"server_id": server.server_id,
				"allocator": server.memory_allocator.lower(),
				"db_port": server.db_port or 3306,
				"mariadb_root_password": Mock_Ansible.call_args.kwargs["variables"]["mariadb_root_password"],
				"certificate_private_key": Mock_Ansible.call_args.kwargs["variables"][
					"certificate_private_key"
				],
				"certificate_full_chain": Mock_Ansible.call_args.kwargs["variables"][
					"certificate_full_chain"
				],
				"certificate_intermediate_chain": Mock_Ansible.call_args.kwargs["variables"][
					"certificate_intermediate_chain"
				],
				"mariadb_depends_on_mounts": server.mariadb_depends_on_mounts,
				"nat_gateway_ip": server.get_nat_gateway_ip(),
				**server.get_mount_variables(),
			},
		)

		self.assertEqual(server.status, "Active")
		self.assertEqual(server.is_server_setup, 1)
		self.assertEqual(server.is_agent_auth_setup, 1)

		server.process_hybrid_server_setup.assert_called_once()
		server._set_mount_status.assert_called_once_with(mock_play)

	@patch(
		"press.press.doctype.database_server.database_server.Ansible",
	)
	def test_setup_server_marks_server_broken_on_failed_play(self, Mock_Ansible):
		server = create_test_database_server()

		mock_play = Mock()
		mock_play.status = "Failure"

		mock_ansible_instance = Mock()
		mock_ansible_instance.run.return_value = mock_play

		Mock_Ansible.return_value = mock_ansible_instance

		server._generate_secret = Mock(return_value="secret")
		server.sign_agent_token = Mock(return_value="signed-token")
		server._set_mount_status = Mock()

		server._setup_server()

		server.reload()

		self.assertEqual(server.status, "Broken")
		self.assertEqual(server.is_server_setup, 0)
		self.assertEqual(server.is_agent_auth_setup, 0)

		server._set_mount_status.assert_called_once_with(mock_play)

	@patch(
		"press.press.doctype.database_server.database_server.Ansible",
	)
	def test_setup_server_marks_server_broken_on_exception(self, Mock_Ansible):
		server = create_test_database_server()

		mock_ansible_instance = Mock()
		mock_ansible_instance.run.side_effect = Exception("Setup failed")

		Mock_Ansible.return_value = mock_ansible_instance

		server._generate_secret = Mock(return_value="secret")
		server.sign_agent_token = Mock(return_value="signed-token")

		server._setup_server()

		server.reload()

		self.assertEqual(server.status, "Broken")
		self.assertEqual(server.is_server_setup, 0)
		self.assertEqual(server.is_agent_auth_setup, 0)
