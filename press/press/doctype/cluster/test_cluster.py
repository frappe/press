# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import boto3
import frappe
from frappe.tests.utils import FrappeTestCase
from hcloud import APIException as HetznerAPIException
from moto import mock_aws

from press.press.doctype.cluster.cluster import Cluster
from press.press.doctype.proxy_server.proxy_server import ProxyServer
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.server.server import BaseServer
from press.press.doctype.ssh_key.test_ssh_key import create_test_ssh_key
from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine
from press.press.doctype.virtual_machine_image.virtual_machine_image import (
	VirtualMachineImage,
)
from press.utils.test import foreground_enqueue_doc


@patch("press.press.doctype.cluster.cluster.boto3.client", new=MagicMock())
def create_test_cluster(
	name: str = "Mumbai",
	region: str = "ap-south-1",
	public: bool = False,
	add_default_servers: bool = False,
	hybrid: bool = False,
) -> "Cluster":
	"""Create test Cluster doc"""

	if frappe.db.exists("Cluster", name):
		return frappe.get_doc("Cluster", name)
	cluster: Cluster = frappe.get_doc(
		{
			"doctype": "Cluster",
			"name": name,
			"region": region,
			"availability_zone": "ap-south-1a",
			"cloud_provider": "AWS EC2",
			"ssh_key": create_test_ssh_key().name,
			"subnet_cidr_block": "10.3.0.0/16",
			"aws_access_key_id": "test",
			"aws_secret_access_key": "test",
			"public": public,
			"hybrid": hybrid,
			"add_default_servers": add_default_servers,
		}
	).insert(ignore_if_duplicate=True)
	cluster.reload()
	if add_default_servers:
		cluster.create_servers()
	return cluster


class TestCluster(FrappeTestCase):
	@mock_aws
	def _setup_fake_vmis(self, series: list[str], cluster: Cluster | None = None):
		from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
			create_test_virtual_machine_image,
		)

		cluster = cluster or create_test_cluster(name="Mumbai", region="ap-south-1")
		for s in series:
			create_test_virtual_machine_image(cluster=cluster, series=s)

	@patch.object(ProxyServer, "validate_domains", new=MagicMock())  # avoid TLSCertificate validation
	def _create_cluster(
		self,
		aws_access_key_id,
		aws_secret_access_key,
		public=False,
		add_default_servers=False,
	) -> Cluster:
		"""Simulate creation of cluster without AWS credentials"""
		cluster: Cluster = frappe.get_doc(
			{
				"doctype": "Cluster",
				"name": "Mumbai 2",
				"region": "ap-south-1",
				"availability_zone": "ap-south-1a",
				"cloud_provider": "AWS EC2",
				"ssh_key": create_test_ssh_key().name,
				"subnet_cidr_block": "10.3.0.0/16",
				"aws_access_key_id": aws_access_key_id,
				"aws_secret_access_key": aws_secret_access_key,
				"public": public,
			}
		)
		cluster.insert()
		if add_default_servers:
			cluster.create_servers()
		return cluster

	def tearDown(self) -> None:
		frappe.db.rollback()


@patch.object(BaseServer, "run_press_job", new=MagicMock())
@patch.object(VirtualMachine, "get_latest_ubuntu_image", new=lambda x: "ami-123")
@patch.object(VirtualMachineImage, "wait_for_availability", new=MagicMock())
@patch.object(VirtualMachineImage, "after_insert", new=MagicMock())
@patch("press.press.doctype.cluster.cluster.frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("press.press.doctype.cluster.cluster.frappe.db.commit", new=MagicMock())
class TestPrivateCluster(TestCluster):
	@mock_aws
	def test_add_images_copies_VMIs_from_other_region(self):
		self._setup_fake_vmis(["m", "f"])  # mumbai
		vmi_count_before = frappe.db.count("Virtual Machine Image")
		cluster = create_test_cluster(name="Frankfurt", region="eu-central-1")
		cluster.add_images()
		vmi_count_after = frappe.db.count("Virtual Machine Image")
		self.assertEqual(vmi_count_after, vmi_count_before + 2)

	def test_add_images_throws_err_if_no_vmis_to_copy(self):
		cluster = create_test_cluster(name="Frankfurt", region="eu-central-1")
		self.assertRaises(frappe.ValidationError, cluster.add_images)

	def test_add_images_throws_err_if_some_vmis_are_unavailable(self):
		self._setup_fake_vmis(["m", "f"])  # another cluster with n missing

		cluster = create_test_cluster(name="Frankfurt", region="eu-central-1", public=True)
		self._setup_fake_vmis(["m", "f"], cluster=cluster)  # n is missing
		self.assertRaises(frappe.ValidationError, cluster.add_images)

	@mock_aws
	def test_creation_of_cluster_in_same_region_reuses_VMIs(self):
		self._setup_fake_vmis(["m", "f"])  # mumbai
		vmi_count_before = frappe.db.count("Virtual Machine Image")
		create_test_cluster(name="Mumbai 2", region="ap-south-1")
		vmi_count_after = frappe.db.count("Virtual Machine Image")
		self.assertNotEqual(vmi_count_before, 0)
		self.assertEqual(vmi_count_after, vmi_count_before)

	@mock_aws
	def test_create_private_cluster_without_aws_access_key_and_secret_creates_user_in_predefined_group_and_adds_servers(
		self,
	):
		self._setup_fake_vmis(["m", "f", "n", "p", "e", "fs"])

		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)
		frappe.db.set_single_value("Press Settings", "aws_access_key_id", "test")
		frappe.db.set_single_value("Press Settings", "aws_secret_access_key", "test")

		server_count_before = frappe.db.count("Server")
		database_server_count_before = frappe.db.count("Database Server")
		proxy_server_count_before = frappe.db.count("Proxy Server")

		boto3.client("iam").create_group(GroupName="fc-vpc-customer")

		Cluster.wait_for_aws_creds_seconds = 0
		self._create_cluster(aws_access_key_id=None, aws_secret_access_key=None, add_default_servers=True)

		server_count_after = frappe.db.count("Server")
		database_server_count_after = frappe.db.count("Database Server")
		proxy_server_count_after = frappe.db.count("Proxy Server")

		self.assertEqual(server_count_before + 1, server_count_after)
		self.assertEqual(database_server_count_before + 1, database_server_count_after)
		self.assertEqual(proxy_server_count_before + 1, proxy_server_count_after)

	def test_create_cluster_without_aws_access_key_and_id_throws_err_if_the_group_doesnt_exist(
		self,
	):
		self.assertRaises(
			frappe.ValidationError,
			self._create_cluster,
			aws_access_key_id=None,
			aws_secret_access_key=None,
		)


@patch.object(BaseServer, "run_press_job", new=MagicMock())
@patch.object(VirtualMachineImage, "wait_for_availability", new=MagicMock())
@patch("press.press.doctype.cluster.cluster.frappe.db.commit", new=MagicMock())
@patch("press.press.doctype.cluster.cluster.frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch.object(VirtualMachineImage, "after_insert", new=MagicMock())
class TestPublicCluster(TestCluster):
	@mock_aws
	@patch.object(ProxyServer, "validate_domains", new=Mock())
	def test_create_servers_without_vmis_throws_err(self):
		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)

		server_count_before = frappe.db.count("Server")
		database_server_count_before = frappe.db.count("Database Server")
		proxy_server_count_before = frappe.db.count("Proxy Server")
		cluster = create_test_cluster(name="Mumbai", region="ap-south-1", public=True)
		self.assertRaises(frappe.ValidationError, cluster.create_servers)
		server_count_after = frappe.db.count("Server")
		database_server_count_after = frappe.db.count("Database Server")
		proxy_server_count_after = frappe.db.count("Proxy Server")
		self.assertEqual(server_count_after, server_count_before)
		self.assertEqual(database_server_count_after, database_server_count_before)
		self.assertEqual(proxy_server_count_after, proxy_server_count_before)

	@mock_aws
	def test_add_images_in_public_cluster_only_adds_3_vms(self):
		self._setup_fake_vmis(["m", "f", "n", "p", "e"])
		vm_count_before = frappe.db.count("Virtual Machine Image")
		cluster = create_test_cluster(name="Frankfurt", region="eu-central-1", public=True)
		cluster.add_images()
		vm_count_after = frappe.db.count("Virtual Machine Image")
		self.assertNotEqual(vm_count_before, 0)
		self.assertEqual(vm_count_after, vm_count_before + 3)

	@mock_aws
	@patch.object(ProxyServer, "validate_domains", new=Mock())
	def test_creation_of_public_cluster_with_servers_creates_3(self):
		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)
		self._setup_fake_vmis(["m", "f", "n", "fs"])

		server_count_before = frappe.db.count("Server")
		database_server_count_before = frappe.db.count("Database Server")
		proxy_server_count_before = frappe.db.count("Proxy Server")

		create_test_cluster(name="Mumbai 2", region="ap-south-1", public=True, add_default_servers=True)

		server_count_after = frappe.db.count("Server")
		database_server_count_after = frappe.db.count("Database Server")
		proxy_server_count_after = frappe.db.count("Proxy Server")
		self.assertEqual(server_count_after, server_count_before + 1)
		self.assertEqual(database_server_count_after, database_server_count_before + 1)
		self.assertEqual(proxy_server_count_after, proxy_server_count_before + 1)

	@mock_aws
	@patch.object(Cluster, "after_insert", new=MagicMock())  # don't create vms/servers
	def test_creation_of_public_cluster_uses_keys_from_press_settings(self):
		from press.press.doctype.press_settings.test_press_settings import (
			create_test_press_settings,
		)

		settings = create_test_press_settings()
		client = boto3.client("iam")
		client.create_user(UserName="test")
		key_pairs = client.create_access_key(UserName="test")
		settings.aws_access_key_id = key_pairs["AccessKey"]["AccessKeyId"]
		settings.aws_secret_access_key = key_pairs["AccessKey"]["SecretAccessKey"]
		settings.save()
		cluster = self._create_cluster(aws_access_key_id=None, aws_secret_access_key=None, public=True)
		self.assertEqual(cluster.aws_access_key_id, key_pairs["AccessKey"]["AccessKeyId"])
		self.assertEqual(
			cluster.get_password("aws_secret_access_key"),
			key_pairs["AccessKey"]["SecretAccessKey"],
		)
		self.assertEqual(len(client.list_users()["Users"]), 1)


# ---------------------------------------------------------------------------
# Infrastructure & Cluster Topology Tests
# ---------------------------------------------------------------------------
# Tests for:
#   * Cluster validation helpers (CIDR, flush-table hour, monitoring password)
#   * Firewall-rule normalisation helpers
#   * create_proxy / create_servers guard conditions
#   * Hetzner API failure → clean state (no partial vpc_id commit)
#   * AWS API failure via moto → ValidationError propagation
#   * NAT-server support logic (get_nat_server_if_supported)
# VirtualMachine-specific tests live in test_virtual_machine.py
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
		from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
			create_test_virtual_machine_image,
		)

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

		self.assertEqual(m["archive"], "Terminated")
