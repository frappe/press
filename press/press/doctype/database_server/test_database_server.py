# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.database_server.database_server import DatabaseServer
from press.press.doctype.server.server import BaseServer
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
			"agent_password": frappe.mock("password"),
			"hostname": f"m{make_autoname('.##')}",
			"cluster": cluster,
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
		wraps=Ansible,
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_mariadb_service_restarted_on_restart_mariadb_fn_call(
		self, Mock_Ansible: Mock
	):
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
		wraps=Ansible,
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_memory_limits_updated_on_update_of_corresponding_fields(
		self, Mock_Ansible: MagicMock
	):
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
			},
		)

	@patch(
		"press.press.doctype.database_server.database_server.Ansible",
		wraps=Ansible,
	)
	@patch(
		"press.press.doctype.database_server.database_server.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	def test_reconfigure_mariadb_exporter_play_runs_on_reconfigure_fn_call(
		self, Mock_Ansible: Mock
	):
		server = create_test_database_server()
		server.reconfigure_mariadb_exporter()
		server.reload()
		Mock_Ansible.assert_called_with(
			playbook="reconfigure_mysqld_exporter.yml",
			server=server,
			variables={
				"private_ip": server.private_ip,
				"mariadb_root_password": server.get_password("mariadb_root_password"),
			},
		)
