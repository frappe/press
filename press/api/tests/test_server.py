# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.server import new
from press.press.doctype.ansible_play.test_ansible_play import create_test_ansible_play
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.plan.test_plan import create_test_plan
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.server.server import BaseServer
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine
from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
	create_test_virtual_machine_image,
)
from press.press.doctype.virtual_machine_image.virtual_machine_image import (
	VirtualMachineImage,
)
from press.runner import Ansible
from press.utils.test import foreground_enqueue_doc


def successful_provision(self: VirtualMachine):
	self.status = "Running"
	self.save()


def successful_sync(self: VirtualMachine):
	self.status = "Running"
	self.save()
	self.update_servers()


def successful_ping_ansible(self: BaseServer):
	create_test_ansible_play("Ping Server", "ping.yml", self.doctype, self.name)


@patch.object(VirtualMachineImage, "client", new=MagicMock())
@patch.object(VirtualMachine, "client", new=MagicMock())
class TestAPIServer(FrappeTestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()

		self.app_plan = create_test_plan("Server")
		self.db_plan = create_test_plan("Database Server")
		self.cluster = create_test_cluster()
		create_test_proxy_server(cluster=self.cluster.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _get_doc_count(self, doctype: str, status: str, team: str):
		return frappe.db.count(doctype, filters={"status": status, "team": team})

	def test_create_new_server_creates_pending_server_and_db_server(self):
		create_test_virtual_machine_image(cluster=self.cluster, series="m")
		create_test_virtual_machine_image(
			cluster=self.cluster, series="f"
		)  # call from here and not setup, so mocks work
		frappe.set_user(self.team.user)

		servers_before = self._get_doc_count("Server", "Pending", self.team.name)
		db_servers_before = self._get_doc_count("Database Server", "Pending", self.team.name)

		new(
			{
				"cluster": self.cluster.name,
				"db_plan": self.db_plan.name,
				"app_plan": self.app_plan.name,
				"title": "Test Server",
			}
		)

		servers_after = self._get_doc_count("Server", "Pending", self.team.name)
		db_servers_after = self._get_doc_count("Database Server", "Pending", self.team.name)

		self.assertEqual(servers_before + 1, servers_after)
		self.assertEqual(db_servers_before + 1, db_servers_after)

	@patch(
		"press.press.doctype.press_job.press_job.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	@patch.object(VirtualMachine, "provision", new=successful_provision)
	@patch.object(VirtualMachine, "sync", new=successful_sync)
	@patch.object(Ansible, "run", new=Mock())
	@patch.object(BaseServer, "ping_ansible", new=successful_ping_ansible)
	def test_new_fn_creates_active_server_and_db_server_once_press_job_succeeds(self):
		create_test_virtual_machine_image(cluster=self.cluster, series="m")
		create_test_virtual_machine_image(
			cluster=self.cluster, series="f"
		)  # call from here and not setup, so mocks work
		frappe.set_user(self.team.user)

		servers_before = self._get_doc_count("Server", "Active", self.team.name)
		db_servers_before = self._get_doc_count("Database Server", "Active", self.team.name)

		new(
			{
				"cluster": self.cluster.name,
				"db_plan": self.db_plan.name,
				"app_plan": self.app_plan.name,
				"title": "Test Server",
			}
		)

		servers_after = self._get_doc_count("Server", "Active", self.team.name)
		db_servers_after = self._get_doc_count("Database Server", "Active", self.team.name)

		self.assertEqual(servers_before + 1, servers_after)
		self.assertEqual(db_servers_before + 1, db_servers_after)
