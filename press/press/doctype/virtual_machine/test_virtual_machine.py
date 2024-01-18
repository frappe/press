# Copyright (c) 2021, Frappe and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from unittest.mock import MagicMock, patch
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

from press.press.doctype.cluster.cluster import Cluster


@patch.object(VirtualMachine, "client", new=MagicMock())
def create_test_virtual_machine(
	ip: str = None,
	cluster: Cluster = None,
	series: str = "m",
) -> VirtualMachine:
	"""Create test Virtual Machine doc"""
	if not ip:
		ip = frappe.mock("ipv4")
	if not cluster:
		cluster = create_test_cluster()
	return frappe.get_doc(
		{
			"doctype": "Virtual Machine",
			"domain": create_test_root_domain("fc.dev", cluster.name).name,
			"series": series,
			"status": "Running",
			"machine_type": "r5.xlarge",
			"disk_size": 100,
			"cluster": cluster.name,
			"instance_id": "i-1234567890",
		}
	).insert(ignore_if_duplicate=True)


@patch.object(VirtualMachine, "client", new=MagicMock())
class TestVirtualMachine(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_database_server_creation_works(self):
		"""Test if database server creation works"""
		vm = create_test_virtual_machine()
		try:
			vm.create_database_server()
		except Exception as e:
			self.fail(e)
