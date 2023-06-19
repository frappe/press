# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import frappe
from frappe.query_builder.functions import Count
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.plan.test_plan import create_test_plan

from press.press.doctype.team.test_team import create_test_press_admin_team

from frappe.tests.utils import FrappeTestCase

from press.api.server import new

from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

from unittest.mock import patch, MagicMock

from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
	create_test_virtual_machine_image,
)
from press.press.doctype.virtual_machine_image.virtual_machine_image import (
	VirtualMachineImage,
)


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

	def test_create_new_server_creates_pending_server_and_db_server(self):
		create_test_virtual_machine_image()  # call from here so mocks work
		frappe.set_user(self.team.user)
		servers = frappe.qb.DocType("Server")
		db_servers = frappe.qb.DocType("Database Server")
		servers_query = (
			frappe.qb.from_(servers)
			.select(Count("*"))
			.where(servers.status == "Pending")
			.where(servers.team == self.team.name)
		)
		db_servers_query = (
			frappe.qb.from_(db_servers)
			.select(Count("*"))
			.where(db_servers.status == "Pending")
			.where(db_servers.team == self.team.name)
		)

		servers_before = servers_query.run()
		db_servers_before = db_servers_query.run()
		new(
			{
				"cluster": self.cluster.name,
				"db_plan": self.db_plan.name,
				"app_plan": self.app_plan.name,
				"title": "Test Server",
			}
		)
		servers_after = servers_query.run()
		db_servers_after = db_servers_query.run()
		self.assertEqual(servers_before[0][0] + 1, servers_after[0][0])
		self.assertEqual(db_servers_before[0][0] + 1, db_servers_after[0][0])
