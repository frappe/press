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


@patch.object(VirtualMachine, "client", new=MagicMock())
class TestVirtualMachineDataDiskSnapshot(FrappeTestCase):
	def setUp(self):
		self.cluster = create_test_cluster(name="VMSnapshotTest")
		self.domain = create_test_root_domain("snap.fc.dev", self.cluster.name)

	def tearDown(self):
		frappe.db.rollback()

	def _make_vm(self, cloud_provider="AWS EC2") -> VirtualMachine:
		vm = frappe.new_doc("Virtual Machine")
		vm.cluster = self.cluster.name
		vm.cloud_provider = cloud_provider
		vm.series = "m"
		vm.domain = self.domain.name
		vm.machine_type = "r5.xlarge"
		vm.disk_size = 100
		vm.platform = "x86_64"
		vm.ssh_key = self.cluster.ssh_key
		return vm

	def _create_snapshot(self, status="Completed", region="ap-south-1") -> str:
		"""Insert a VirtualDiskSnapshot and return its name."""
		snap = frappe.get_doc(
			{
				"doctype": "Virtual Disk Snapshot",
				"virtual_machine": create_test_virtual_machine(cluster=self.cluster).name,
				"status": status,
				"region": region,
				"snapshot_id": f"snap-{frappe.generate_hash(8)}",
				"size": 50,
			}
		).insert(ignore_permissions=True)
		return snap.name

	def test_data_disk_snapshot_only_allowed_on_aws(self):
		vm = self._make_vm(cloud_provider="Hetzner")
		vm.is_new = MagicMock(return_value=True)
		vm.data_disk_snapshot = self._create_snapshot()
		with self.assertRaises(frappe.ValidationError):
			vm.validate_data_disk_snapshot()

	def test_data_disk_snapshot_throws_when_snapshot_not_completed(self):
		snap_name = self._create_snapshot(status="Pending")
		vm = self._make_vm()
		vm.is_new = MagicMock(return_value=True)
		vm.data_disk_snapshot = snap_name
		vm.virtual_machine_image = "any-vmi"
		with self.assertRaises(frappe.ValidationError):
			vm.validate_data_disk_snapshot()

	def test_data_disk_snapshot_throws_on_region_mismatch(self):
		"""Snapshot in a different region than cluster should throw."""
		snap_name = self._create_snapshot(status="Completed", region="us-east-1")
		vm = self._make_vm()
		vm.is_new = MagicMock(return_value=True)
		vm.data_disk_snapshot = snap_name
		vm.virtual_machine_image = "any-vmi"
		with self.assertRaises(frappe.ValidationError):
			vm.validate_data_disk_snapshot()

	def test_data_disk_snapshot_throws_when_no_vmi_set(self):
		"""Snapshot requires a VMI to be attached."""
		snap_name = self._create_snapshot(status="Completed")
		vm = self._make_vm()
		vm.is_new = MagicMock(return_value=True)
		vm.data_disk_snapshot = snap_name
		vm.virtual_machine_image = None
		with self.assertRaises(frappe.ValidationError):
			vm.validate_data_disk_snapshot()

	def test_data_disk_snapshot_skipped_for_existing_vm(self):
		"""validate_data_disk_snapshot is a no-op for existing (non-new) VMs."""
		snap_name = self._create_snapshot(status="Pending")
		vm = self._make_vm(cloud_provider="Hetzner")
		vm.is_new = MagicMock(return_value=False)
		vm.data_disk_snapshot = snap_name
		vm.validate_data_disk_snapshot()

	def test_data_disk_snapshot_skipped_when_no_snapshot_set(self):
		vm = self._make_vm()
		vm.is_new = MagicMock(return_value=True)
		vm.data_disk_snapshot = None
		vm.validate_data_disk_snapshot()


@patch.object(VirtualMachine, "client", new=MagicMock())
class TestVirtualMachineVolumeHelpers(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _vm_with_volumes(self, volumes_data: list[dict], cloud_provider="AWS EC2") -> VirtualMachine:
		"""Create a VM and attach in-memory volume rows (not saved)."""
		cluster = create_test_cluster(name="VolTestCluster")
		vm = create_test_virtual_machine(cluster=cluster, disk_size=100)
		vm.cloud_provider = cloud_provider
		vm.volumes = []
		for v in volumes_data:
			vm.append("volumes", v)
		return vm

	def test_get_root_volume_single_volume_returns_it(self):
		vm = self._vm_with_volumes(
			[{"device": "/dev/sda1", "volume_id": "vol-aaa", "size": 50, "volume_type": "gp3"}]
		)
		vm.has_data_volume = False
		root = vm.get_root_volume()
		self.assertEqual(root.device, "/dev/sda1")

	def test_get_root_volume_multi_volume_aws_picks_sda1(self):
		vm = self._vm_with_volumes(
			[
				{"device": "/dev/sda1", "volume_id": "vol-root", "size": 20, "volume_type": "gp3"},
				{"device": "/dev/sdf", "volume_id": "vol-data", "size": 100, "volume_type": "gp3"},
			]
		)
		vm.cloud_provider = "AWS EC2"
		vm.has_data_volume = True
		root = vm.get_root_volume()
		self.assertEqual(root.volume_id, "vol-root")

	def test_get_data_volume_returns_root_when_no_data_volume(self):
		vm = self._vm_with_volumes(
			[{"device": "/dev/sda1", "volume_id": "vol-aaa", "size": 50, "volume_type": "gp3"}]
		)
		vm.has_data_volume = False
		data = vm.get_data_volume()
		self.assertEqual(data.volume_id, "vol-aaa")

	def test_get_data_volume_returns_non_root_volume_on_aws(self):
		vm = self._vm_with_volumes(
			[
				{"device": "/dev/sda1", "volume_id": "vol-root", "size": 20, "volume_type": "gp3"},
				{"device": "/dev/sdf", "volume_id": "vol-data", "size": 100, "volume_type": "gp3"},
			]
		)
		vm.cloud_provider = "AWS EC2"
		vm.has_data_volume = True
		data = vm.get_data_volume()
		self.assertEqual(data.volume_id, "vol-data")

	def test_get_data_volume_fallback_when_no_volumes(self):
		"""Empty volumes → returns a dummy dict with size=0."""
		vm = self._vm_with_volumes([])
		vm.has_data_volume = True
		vm.cloud_provider = "AWS EC2"
		data = vm.get_data_volume()
		self.assertEqual(data.size, 0)


@patch.object(VirtualMachine, "client", new=MagicMock())
class TestVirtualMachineServerRouting(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_database_server_works(self):
		cluster = create_test_cluster(name="Routing-Cluster-1")
		vm = create_test_virtual_machine(cluster=cluster, series="m")
		db_server = vm.create_database_server()
		self.assertEqual(db_server.doctype, "Database Server")
		self.assertEqual(db_server.virtual_machine, vm.name)

	def test_create_proxy_server_works(self):
		cluster = create_test_cluster(name="Routing-Cluster-2")
		vm = create_test_virtual_machine(cluster=cluster, series="n")
		proxy = vm.create_proxy_server()
		self.assertEqual(proxy.doctype, "Proxy Server")
		self.assertEqual(proxy.virtual_machine, vm.name)

	def test_create_server_works(self):
		cluster = create_test_cluster(name="Routing-Cluster-3")
		vm = create_test_virtual_machine(cluster=cluster, series="f")
		app_server = vm.create_server()
		self.assertEqual(app_server.doctype, "Server")
		self.assertEqual(app_server.virtual_machine, vm.name)

	def test_create_unified_server_requires_u_series(self):
		"""Only 'u' series VMs can create unified servers."""
		cluster = create_test_cluster(name="Routing-Cluster-4")
		vm = create_test_virtual_machine(cluster=cluster, series="f")
		with self.assertRaises(frappe.ValidationError):
			vm.create_unified_server()

	def test_create_nat_server_requires_nat_series(self):
		cluster = create_test_cluster(name="Routing-Cluster-5")
		vm = create_test_virtual_machine(cluster=cluster, series="m")
		with self.assertRaises(frappe.ValidationError):
			vm.create_nat_server()

	def test_create_unified_server_creates_app_and_db_pair(self):
		"""A 'u' series VM should create both Server and DatabaseServer docs."""
		cluster = create_test_cluster(name="Routing-Cluster-6")
		vm = create_test_virtual_machine(cluster=cluster, series="u")
		team = frappe.get_value("Team", {"user": "Administrator"}, "name") or "Administrator"
		vm.team = team
		vm.save()

		server, db_server = vm.create_unified_server()
		self.assertEqual(server.doctype, "Server")
		self.assertEqual(db_server.doctype, "Database Server")
		self.assertTrue(server.is_unified_server)
		self.assertTrue(db_server.is_unified_server)
		self.assertEqual(server.virtual_machine, vm.name)
		self.assertEqual(db_server.virtual_machine, vm.name)

	def test_nat_vm_validate_throws_for_non_aws(self):
		"""NAT servers are not supported outside AWS EC2 / Frappe Compute."""
		cluster = create_test_cluster(name="Routing-Cluster-7")
		vm = frappe.new_doc("Virtual Machine")
		vm.series = "nat"
		vm.cloud_provider = "Hetzner"
		vm.cluster = cluster.name
		vm.machine_type = "cpx21"
		vm.disk_size = 50
		vm.platform = "x86_64"
		vm.ssh_key = cluster.ssh_key
		domain = create_test_root_domain("nat.fc.dev", cluster.name)
		vm.domain = domain.name
		vm.private_ip_address = "10.3.0.1"
		with self.assertRaises(frappe.ValidationError):
			vm.validate()


@patch.object(VirtualMachine, "client", new=MagicMock())
class TestVirtualMachineStatusMaps(FrappeTestCase):
	def setUp(self):
		cluster = create_test_cluster(name="StatusMapCluster")
		self.vm = create_test_virtual_machine(cluster=cluster)

	def tearDown(self):
		frappe.db.rollback()

	def test_aws_status_map_covers_all_states(self):
		m = self.vm.get_aws_status_map()
		expected_states = {"pending", "running", "shutting-down", "stopping", "stopped", "terminated"}
		self.assertEqual(set(m.keys()), expected_states)
		press_statuses = {"Pending", "Running", "Stopped", "Terminated"}
		for v in m.values():
			self.assertIn(v, press_statuses)

	def test_hetzner_status_map_covers_all_states(self):
		m = self.vm.get_hetzner_status_map()
		self.assertIn("running", m)
		self.assertEqual(m["running"], "Running")
		self.assertIn("off", m)
		press_statuses = {"Pending", "Running", "Stopped", "Terminated"}
		for v in m.values():
			self.assertIn(v, press_statuses)

	def test_oci_status_map_covers_all_states(self):
		m = self.vm.get_oci_status_map()
		self.assertIn("RUNNING", m)
		self.assertEqual(m["RUNNING"], "Running")
		self.assertIn("TERMINATED", m)
		self.assertEqual(m["TERMINATED"], "Terminated")

	def test_digital_ocean_status_map(self):
		m = self.vm.get_digital_ocean_status_map()
		self.assertEqual(m["active"], "Running")
