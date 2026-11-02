# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

if TYPE_CHECKING:
	from press.press.doctype.cluster.cluster import Cluster


@patch.object(VirtualMachine, "client", new=MagicMock())
def create_test_virtual_machine(
	ip: str | None = None,
	cluster: Cluster | None = None,
	series: str = "m",
	platform: str = "x86_64",
	cloud_provider: str = "AWS EC2",
	disk_size: int = 100,
	has_data_volume: bool = False,
) -> VirtualMachine:
	"""Create test Virtual Machine doc"""
	if not ip:
		ip = frappe.mock("ipv4")
	if not cluster:
		cluster = create_test_cluster()
	vm = frappe.get_doc(
		{
			"doctype": "Virtual Machine",
			"domain": create_test_root_domain("fc.dev", cluster.name).name,
			"series": series,
			"status": "Running",
			"machine_type": "r5.xlarge",
			"disk_size": disk_size,
			"cluster": cluster.name,
			"instance_id": "i-1234567890",
			"vcpu": 4,
			"platform": platform,
			"cloud_provider": cloud_provider,
		}
	).insert(ignore_if_duplicate=True)

	volumes = []
	# Root volume
	volumes.append(
		frappe.get_doc(
			{
				"doctype": "Virtual Machine Volume",
				"parenttype": "Virtual Machine",
				"parent": vm.name,
				"parentfield": "volumes",
				"volume_type": "gp3",
				"throughput": 125,
				"device": "/dev/sdf",
				"size": disk_size if not has_data_volume else 8,
				"volume_id": f"vol-{frappe.generate_hash(11)}",
			}
		)
	)
	if has_data_volume:
		volumes.append(
			frappe.get_doc(
				{
					"doctype": "Virtual Machine Volume",
					"parenttype": "Virtual Machine",
					"parent": vm.name,
					"parentfield": "volumes",
					"volume_type": "gp3",
					"throughput": 125,
					"device": "/dev/sdg",
					"size": disk_size,
					"volume_id": f"vol-{frappe.generate_hash(11)}",
				}
			)
		)

	for volume in volumes:
		volume.insert()

	return vm


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

	def test_no_private_ip_collision(self):
		list_of_series = ["n", "f", "m", "c", "p", "e", "r", "u", "t", "nfs", "fs", "nat"]
		list_of_big_series = ["f", "m", "u", "t"]
		vm_doc: VirtualMachine = frappe.new_doc("Virtual Machine")
		vm_doc.subnet_cidr_block = "10.29.0.0/16"

		allocated_ips = set()  # to keep track of collisions
		for series in list_of_series:
			if series in ["c", "r"]:  # unused
				continue
			vm_doc.series = series
			max_index = 256  # most series will never have these many instances
			if series in list_of_big_series:
				max_index = 8192  # f, m, u and t have a theoretical max of 8192

			for idx in range(max_index):
				vm_doc.index = idx + 1
				ip = vm_doc.get_private_ip()
				self.assertTrue(ip not in allocated_ips)
				allocated_ips.add(ip)
