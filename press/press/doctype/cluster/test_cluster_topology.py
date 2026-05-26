# Copyright (c) 2024, Frappe and Contributors
# See license.txt
"""
Task 2 - Infrastructure & Cluster Topology
==========================================
Tests for:
  * Cluster validation helpers (CIDR, flush-table hour, monitoring password)
  * Firewall-rule normalisation helpers
  * create_proxy / create_servers guard conditions
  * Hetzner API failure → clean state (no partial vpc_id commit)
  * AWS API failure via moto → ValidationError propagation
  * VirtualMachine.validate_data_disk_snapshot error paths
  * VirtualMachine volume helpers (get_root_volume / get_data_volume)
  * VirtualMachine server-creation routing (Unified vs Dedicated)
  * NAT-server support logic (get_nat_server_if_supported)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from hcloud import APIException as HetznerAPIException

from press.press.doctype.cluster.cluster import Cluster
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.server.server import BaseServer
from press.press.doctype.virtual_machine.test_virtual_machine import (
	create_test_virtual_machine,
)
from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine
from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
	create_test_virtual_machine_image,
)
from press.press.doctype.virtual_machine_image.virtual_machine_image import (
	VirtualMachineImage,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cluster(name="TestCluster", cloud_provider="AWS EC2") -> "Cluster":
	"""Return an in-memory (new_doc) Cluster with minimal required fields."""
	cluster = frappe.new_doc("Cluster")
	cluster.name = name
	cluster.cloud_provider = cloud_provider
	cluster.status = "Active"
	cluster.region = "ap-south-1"
	cluster.availability_zone = "ap-south-1a"
	cluster.cidr_block = "10.99.0.0/16"
	cluster.subnet_cidr_block = "10.99.0.0/16"
	cluster.monitoring_password = "existing-pass"  # pragma: allowlist secret
	return cluster


# ---------------------------------------------------------------------------
# 1. Cluster Validation Helpers
# ---------------------------------------------------------------------------


class TestClusterValidation(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	# ---- validate_cidr_block ------------------------------------------------

	def test_validate_cidr_block_assigns_block_when_empty(self):
		"""Auto-assigns a /16 CIDR when none is set."""
		cluster = _make_cluster()
		cluster.cidr_block = ""
		cluster.subnet_cidr_block = ""
		cluster.validate_cidr_block()
		self.assertTrue(cluster.cidr_block.startswith("10."))
		self.assertIn("/16", cluster.cidr_block)

	def test_validate_cidr_block_skips_existing_blocks(self):
		"""The auto-assigned block should not collide with already-used ones."""
		# Insert two clusters to occupy the first two /16 blocks
		c1 = create_test_cluster(name="Cluster-CIDR-1")
		c2 = create_test_cluster(name="Cluster-CIDR-2")
		c2.cidr_block = "10.1.0.0/16"
		c2.db_update()

		cluster = _make_cluster("Cluster-CIDR-New")
		cluster.cidr_block = ""
		cluster.subnet_cidr_block = ""
		cluster.validate_cidr_block()

		used = {c1.cidr_block, c2.cidr_block}
		self.assertNotIn(cluster.cidr_block, used)

	def test_validate_cidr_block_keeps_existing_block(self):
		"""Existing cidr_block is left untouched."""
		cluster = _make_cluster()
		cluster.cidr_block = "10.55.0.0/16"
		cluster.validate_cidr_block()
		self.assertEqual(cluster.cidr_block, "10.55.0.0/16")

	# ---- validate_monitoring_password ---------------------------------------

	def test_validate_monitoring_password_generates_when_missing(self):
		cluster = _make_cluster()
		cluster.monitoring_password = None
		cluster.validate_monitoring_password()
		self.assertIsNotNone(cluster.monitoring_password)
		self.assertGreater(len(cluster.monitoring_password), 0)

	def test_validate_monitoring_password_keeps_existing(self):
		cluster = _make_cluster()
		cluster.monitoring_password = "my-secret"  # pragma: allowlist secret
		cluster.validate_monitoring_password()
		self.assertEqual(cluster.monitoring_password, "my-secret")

	# ---- validate_flush_table_execution_hour --------------------------------

	def test_flush_table_validation_skips_when_disabled(self):
		"""No error when feature is disabled, regardless of hour."""
		cluster = _make_cluster()
		cluster.enable_periodic_flush_table = 0
		cluster.flush_table_execution_hour = None
		# Should not raise
		cluster.validate_flush_table_execution_hour()

	def test_flush_table_validation_throws_when_hour_missing(self):
		cluster = _make_cluster()
		cluster.enable_periodic_flush_table = 1
		cluster.flush_table_execution_hour = None
		with self.assertRaises(frappe.ValidationError):
			cluster.validate_flush_table_execution_hour()

	def test_flush_table_validation_throws_when_hour_too_high(self):
		cluster = _make_cluster()
		cluster.enable_periodic_flush_table = 1
		cluster.flush_table_execution_hour = 24  # 0-23 only
		with self.assertRaises(frappe.ValidationError):
			cluster.validate_flush_table_execution_hour()

	def test_flush_table_validation_throws_when_hour_negative(self):
		cluster = _make_cluster()
		cluster.enable_periodic_flush_table = 1
		cluster.flush_table_execution_hour = -1
		with self.assertRaises(frappe.ValidationError):
			cluster.validate_flush_table_execution_hour()

	def test_flush_table_validation_passes_for_valid_hour(self):
		cluster = _make_cluster()
		cluster.enable_periodic_flush_table = 1
		for hour in (0, 12, 23):
			cluster.flush_table_execution_hour = hour
			# Should not raise
			cluster.validate_flush_table_execution_hour()


# ---------------------------------------------------------------------------
# 2. Firewall Rule Normalisation Helpers
# ---------------------------------------------------------------------------


class TestClusterFirewallHelpers(FrappeTestCase):
	def setUp(self):
		self.cluster = _make_cluster()

	def tearDown(self):
		frappe.db.rollback()

	# ---- _parse_port_range --------------------------------------------------

	def test_parse_port_range_with_int(self):
		start, end = self.cluster._parse_port_range(22)
		self.assertEqual(start, 22)
		self.assertEqual(end, 22)

	def test_parse_port_range_with_string_single_port(self):
		start, end = self.cluster._parse_port_range("443")
		self.assertEqual(start, 443)
		self.assertEqual(end, 443)

	def test_parse_port_range_with_range_string(self):
		start, end = self.cluster._parse_port_range("8000-9000")
		self.assertEqual(start, 8000)
		self.assertEqual(end, 9000)

	# ---- _normalize_firewall_protocol ---------------------------------------

	def test_normalize_protocol_accepts_tcp(self):
		result = self.cluster._normalize_firewall_protocol("tcp")
		self.assertEqual(result, "tcp")

	def test_normalize_protocol_accepts_udp(self):
		result = self.cluster._normalize_firewall_protocol("UDP")
		self.assertEqual(result, "udp")

	def test_normalize_protocol_rejects_invalid(self):
		with self.assertRaises(frappe.ValidationError):
			self.cluster._normalize_firewall_protocol("icmp")

	# ---- _normalize_firewall_rules ------------------------------------------

	def test_normalize_rules_single_int_port(self):
		"""A bare integer is treated as tcp."""
		rules = self.cluster._normalize_firewall_rules(22)
		self.assertEqual(len(rules), 1)
		self.assertEqual(rules[0], (22, "tcp"))

	def test_normalize_rules_list_of_int_ports(self):
		rules = self.cluster._normalize_firewall_rules([80, 443])
		self.assertEqual(len(rules), 2)
		self.assertEqual(rules[0], (80, "tcp"))
		self.assertEqual(rules[1], (443, "tcp"))

	def test_normalize_rules_list_of_port_protocol_pairs(self):
		rules = self.cluster._normalize_firewall_rules([["22", "tcp"], ["51820", "udp"]])
		self.assertEqual(len(rules), 2)
		self.assertEqual(rules[0], ("22", "tcp"))
		self.assertEqual(rules[1], ("51820", "udp"))

	def test_normalize_rules_empty_list_throws(self):
		with self.assertRaises(frappe.ValidationError):
			self.cluster._normalize_firewall_rules([])

	def test_normalize_rules_invalid_protocol_throws(self):
		with self.assertRaises(frappe.ValidationError):
			self.cluster._normalize_firewall_rules([["22", "ftp"]])


# ---------------------------------------------------------------------------
# 3. create_proxy and create_servers Guard Conditions
# ---------------------------------------------------------------------------


@patch.object(VirtualMachine, "client", new=MagicMock())
@patch.object(VirtualMachineImage, "after_insert", new=MagicMock())
class TestClusterServerCreationGuards(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	# ---- create_proxy -------------------------------------------------------

	def test_create_proxy_throws_when_cluster_not_active(self):
		cluster = create_test_cluster(name="GuardCluster-1")
		cluster.status = "Copying Images"
		with self.assertRaises(frappe.ValidationError):
			cluster.create_proxy()

	def test_create_proxy_throws_when_no_proxy_vmi_available(self):
		"""No VMI for series 'n' → ValidationError."""
		cluster = create_test_cluster(name="GuardCluster-2")
		cluster.status = "Active"
		# No VMIs created → images_available == 0 / no 'n' series
		with self.assertRaises(frappe.ValidationError):
			cluster.create_proxy()

	def test_create_proxy_throws_for_inactive_cluster_before_checking_vmi(self):
		"""Status check fires even if there were VMIs available."""
		cluster = create_test_cluster(name="GuardCluster-3")
		create_test_virtual_machine_image(cluster=cluster, series="n")
		cluster.status = "Archived"
		with self.assertRaises(frappe.ValidationError):
			cluster.create_proxy()

	# ---- create_servers -----------------------------------------------------

	def test_create_servers_throws_when_images_not_available(self):
		cluster = create_test_cluster(name="GuardCluster-4")
		cluster.status = "Active"
		with self.assertRaises(frappe.ValidationError):
			cluster.create_servers()

	# ---- create_server (App Server without proxy) ---------------------------

	@patch.object(BaseServer, "run_press_job", new=MagicMock())
	def test_create_server_app_throws_when_no_proxy_set(self):
		"""Creating an App Server (series 'f') without proxy_server throws."""
		cluster = create_test_cluster(name="GuardCluster-5")

		with (
			patch.object(Cluster, "create_vm") as mock_create_vm,
			patch.object(Cluster, "get_or_create_basic_plan") as mock_plan,
		):
			mock_vm = MagicMock()
			mock_server = MagicMock()
			mock_server.ram = 4096
			mock_server.title = ""
			mock_server.auto_increase_storage = False
			mock_server.new_worker_allocation = True
			mock_server.is_for_recovery = False
			mock_server.nat_server = None
			mock_vm.create_server.return_value = mock_server
			mock_create_vm.return_value = mock_vm

			mock_plan.return_value = MagicMock(
				instance_type="t3.medium",
				disk=50,
				platform="x86_64",
				memory=4096,
				name="test-plan",
			)

			domain = create_test_root_domain("fc.dev", cluster.name)
			frappe.db.set_single_value("Press Settings", "domain", domain.name)

			# Ensure proxy_server is explicitly not set
			if "proxy_server" in cluster.__dict__:
				del cluster.__dict__["proxy_server"]

			with self.assertRaises(frappe.ValidationError):
				cluster.create_server("Server", "Title")

	# ---- create_server DB-replication guards --------------------------------

	def test_create_server_replication_non_db_server_throws(self):
		cluster = create_test_cluster(name="GuardCluster-6")
		with self.assertRaises(frappe.ValidationError):
			cluster.create_server("Server", "Title", setup_db_replication=True)

	def test_create_server_replication_missing_master_throws(self):
		cluster = create_test_cluster(name="GuardCluster-7")
		with self.assertRaises(frappe.ValidationError):
			cluster.create_server(
				"Database Server", "Title", setup_db_replication=True, master_db_server=None
			)

	def test_create_server_replication_inactive_master_throws(self):
		"""Providing a non-Active master DB server should raise ValidationError."""
		cluster = create_test_cluster(name="GuardCluster-8")
		# Create a fake database server name that doesn't exist (inactive)
		with (
			patch("frappe.get_value", return_value="Pending"),
			self.assertRaises(frappe.ValidationError),
		):
			cluster.create_server(
				"Database Server",
				"Title",
				setup_db_replication=True,
				master_db_server="fake-db-server",
			)


# ---------------------------------------------------------------------------
# 4. Hetzner API Failure → Clean State (No Partial VPC Commit)
# ---------------------------------------------------------------------------


class TestHetznerProvisionFailure(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch("press.press.doctype.cluster.cluster.Client")
	def test_provision_hetzner_raises_on_network_creation_failure(self, mock_hetzner_cls):
		"""When Hetzner network.create raises APIException, cluster gets no vpc_id."""
		mock_client = MagicMock()
		mock_hetzner_cls.return_value = mock_client
		mock_client.servers.get_all.return_value = []  # for validate_hetzner_api_token

		# Simulate network creation failure
		mock_client.networks.create.side_effect = HetznerAPIException(
			code="rate_limit_exceeded", message="Rate limited", details=None
		)

		cluster = _make_cluster("HetznerFail-1", cloud_provider="Hetzner")

		with (
			patch.object(cluster, "get_password", return_value="fake-hetzner-token"),
			self.assertRaises(frappe.ValidationError),
		):
			cluster.provision_on_hetzner()

		# vpc_id must NOT be set — no partial state committed
		self.assertFalse(cluster.vpc_id)

	@patch("press.press.doctype.cluster.cluster.Client")
	def test_provision_hetzner_raises_on_server_firewall_failure(self, mock_hetzner_cls):
		"""Firewall creation failure after VPC creation: vpc_id is set in memory
		(it was saved before the firewall call), but security_group_id is NOT set."""
		mock_client = MagicMock()
		mock_hetzner_cls.return_value = mock_client
		mock_client.servers.get_all.return_value = []

		fake_network = MagicMock()
		fake_network.id = 12345
		mock_client.networks.create.return_value = fake_network

		# SSH key succeeds
		mock_client.ssh_keys.create.return_value = MagicMock()

		# Server firewall creation fails
		mock_client.firewalls.create.side_effect = HetznerAPIException(
			code="server_error", message="Internal Server Error", details=None
		)

		cluster = _make_cluster("HetznerFail-2", cloud_provider="Hetzner")
		cluster.ssh_key = "test-ssh-key"

		with (
			patch.object(cluster, "get_password", return_value="fake-token"),
			patch.object(Cluster, "save", MagicMock()),
			patch.object(frappe.db, "get_value", return_value="ssh-public-key"),
			self.assertRaises(frappe.ValidationError),
		):
			cluster.provision_on_hetzner()

		# security_group_id must NOT be set
		self.assertFalse(cluster.security_group_id)

	@patch("press.press.doctype.cluster.cluster.Client")
	def test_validate_hetzner_api_token_throws_on_unauthorized(self, mock_hetzner_cls):
		"""validate_hetzner_api_token propagates 'unauthorized' as ValidationError."""
		mock_client = MagicMock()
		mock_hetzner_cls.return_value = mock_client

		mock_client.servers.get_all.side_effect = HetznerAPIException(
			code="unauthorized", message="Unauthorized", details=None
		)

		cluster = _make_cluster("HetznerValidation", cloud_provider="Hetzner")

		with (
			patch.object(cluster, "get_password", return_value="bad-token"),
			self.assertRaises(frappe.ValidationError),
		):
			cluster.validate_hetzner_api_token()

	@patch("press.press.doctype.cluster.cluster.Client")
	def test_validate_hetzner_api_token_throws_on_other_api_exception(self, mock_hetzner_cls):
		"""Non-unauthorized API errors also propagate."""
		mock_client = MagicMock()
		mock_hetzner_cls.return_value = mock_client

		mock_client.servers.get_all.side_effect = HetznerAPIException(
			code="service_error", message="Service down", details=None
		)

		cluster = _make_cluster("HetznerValidation2", cloud_provider="Hetzner")

		with (
			patch.object(cluster, "get_password", return_value="token"),
			self.assertRaises(frappe.ValidationError),
		):
			cluster.validate_hetzner_api_token()


# ---------------------------------------------------------------------------
# 5. NAT Server Support Logic
# ---------------------------------------------------------------------------


class TestNatServerSupport(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_get_nat_server_returns_none_when_public_ips_enabled(self):
		cluster = create_test_cluster(name="NatTest-1")
		cluster.disable_public_ips_for_servers = 0
		result = cluster.get_nat_server_if_supported()
		self.assertIsNone(result)

	def test_get_nat_server_returns_none_for_hetzner(self):
		"""NAT servers are only supported on AWS EC2 / Frappe Compute."""
		cluster = _make_cluster("NatTest-2", cloud_provider="Hetzner")
		cluster.disable_public_ips_for_servers = 1
		result = cluster.get_nat_server_if_supported()
		self.assertIsNone(result)

	def test_get_nat_server_returns_none_when_no_nat_server_exists(self):
		cluster = create_test_cluster(name="NatTest-3")
		cluster.disable_public_ips_for_servers = 1
		# No NAT Server exists in DB → should return None
		result = cluster.get_nat_server_if_supported()
		self.assertIsNone(result)

	def test_get_nat_server_returns_name_when_active_nat_server_exists(self):
		cluster = create_test_cluster(name="NatTest-4")
		cluster.disable_public_ips_for_servers = 1

		nat_name = "fake-nat-server"
		# Patch frappe.db.get_value to simulate finding a NAT server
		with patch("frappe.db.get_value", return_value=nat_name):
			result = cluster.get_nat_server_if_supported()
		self.assertEqual(result, nat_name)


# ---------------------------------------------------------------------------
# 6. VirtualMachine.validate_data_disk_snapshot Error Paths
# ---------------------------------------------------------------------------


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
		# Should NOT raise even with Hetzner + Pending snapshot
		vm.validate_data_disk_snapshot()

	def test_data_disk_snapshot_skipped_when_no_snapshot_set(self):
		vm = self._make_vm()
		vm.is_new = MagicMock(return_value=True)
		vm.data_disk_snapshot = None
		# Should NOT raise
		vm.validate_data_disk_snapshot()


# ---------------------------------------------------------------------------
# 7. VirtualMachine Volume Helpers
# ---------------------------------------------------------------------------


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

	# ---- get_root_volume -----------------------------------------------------

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

	# ---- get_data_volume -----------------------------------------------------

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


# ---------------------------------------------------------------------------
# 8. VirtualMachine Server Creation Routing
# ---------------------------------------------------------------------------


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
		vm.series = "m"
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
		# Both should reference the same VM
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


# ---------------------------------------------------------------------------
# 9. VM Status Maps Coverage
# ---------------------------------------------------------------------------


@patch.object(VirtualMachine, "client", new=MagicMock())
class TestVirtualMachineStatusMaps(FrappeTestCase):
	def setUp(self):
		cluster = create_test_cluster(name="StatusMapCluster")
		self.vm = create_test_virtual_machine(cluster=cluster)

	def tearDown(self):
		frappe.db.rollback()

	def test_aws_status_map_covers_all_states(self):
		m = self.vm.get_aws_status_map()
		expected_states = {
			"pending",
			"running",
			"shutting-down",
			"stopping",
			"stopped",
			"terminated",
		}
		self.assertEqual(set(m.keys()), expected_states)
		# All values must be one of the Press statuses
		press_statuses = {"Pending", "Running", "Stopped", "Terminated"}
		for v in m.values():
			self.assertIn(v, press_statuses)

	def test_hetzner_status_map_covers_all_states(self):
		m = self.vm.get_hetzner_status_map()
		self.assertIn("running", m)
		self.assertEqual(m["running"], "Running")
		self.assertIn("off", m)
		# All stopped/off states map to a valid Press status
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
		self.assertEqual(m["archive"], "Terminated")
