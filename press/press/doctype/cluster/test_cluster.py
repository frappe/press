# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt


import boto3
import frappe
import unittest
from press.press.doctype.proxy_server.proxy_server import ProxyServer
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain

from press.press.doctype.ssh_key.test_ssh_key import create_test_ssh_key

from press.press.doctype.cluster.cluster import Cluster

from unittest.mock import MagicMock, patch
from moto import mock_ec2, mock_ssm, mock_iam

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
	cluster = frappe.get_doc(
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


class TestCluster(unittest.TestCase):
	@mock_ec2
	@mock_ssm
	def _setup_fake_vmis(self, series: list[str], cluster: Cluster = None):
		from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
			create_test_virtual_machine_image,
		)

		cluster = cluster or create_test_cluster(name="Mumbai", region="ap-south-1")
		for s in series:
			create_test_virtual_machine_image(cluster=cluster, series=s)

	@patch.object(
		ProxyServer, "validate", new=MagicMock()
	)  # avoid TLSCertificate validation
	def _create_cluster(
		self,
		aws_access_key_id,
		aws_secret_access_key,
		public=False,
		add_default_servers=False,
	) -> Cluster:
		"""Simulate creation of cluster without AWS credentials"""
		cluster = frappe.get_doc(
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


@patch.object(VirtualMachine, "get_latest_ubuntu_image", new=lambda x: "ami-123")
@patch.object(VirtualMachineImage, "wait_for_availability", new=MagicMock())
@patch.object(VirtualMachineImage, "after_insert", new=MagicMock())
@patch(
	"press.press.doctype.cluster.cluster.frappe.enqueue_doc", new=foreground_enqueue_doc
)
@patch("press.press.doctype.cluster.cluster.frappe.db.commit", new=MagicMock())
class TestPrivateCluster(TestCluster):
	@mock_ec2
	@mock_ssm
	def test_add_images_copies_VMIs_from_other_region(self):

		self._setup_fake_vmis(["m", "f"])  # mumbai
		vmi_count_before = frappe.db.count("Virtual Machine Image")
		cluster = create_test_cluster(name="Frankfurt", region="eu-central-1")
		cluster.add_images()
		vmi_count_after = frappe.db.count("Virtual Machine Image")
		self.assertEqual(vmi_count_after, vmi_count_before + 2)

	def test_add_images_throws_err_if_no_vmis_to_copy(self):
		cluster = create_test_cluster(name="Frankfurt", region="eu-central-1")
		self.assertRaises(Exception, cluster.add_images)

	def test_add_images_throws_err_if_some_vmis_are_unavailable(self):
		self._setup_fake_vmis(["m", "f"])  # another cluster with n missing

		cluster = create_test_cluster(name="Frankfurt", region="eu-central-1", public=True)
		self._setup_fake_vmis(["m", "f"], cluster=cluster)  # n is missing
		self.assertRaises(Exception, cluster.add_images)

	@mock_ec2
	@mock_ssm
	def test_creation_of_cluster_in_same_region_reuses_VMIs(self):
		self._setup_fake_vmis(["m", "f"])  # mumbai
		vmi_count_before = frappe.db.count("Virtual Machine Image")
		create_test_cluster(name="Mumbai 2", region="ap-south-1")
		vmi_count_after = frappe.db.count("Virtual Machine Image")
		self.assertNotEqual(vmi_count_before, 0)
		self.assertEqual(vmi_count_after, vmi_count_before)

	@mock_ec2
	@mock_ssm
	@mock_iam
	def test_create_private_cluster_without_aws_access_key_and_secret_creates_user_in_predefined_group_and_adds_servers(
		self,
	):
		self._setup_fake_vmis(["m", "f", "n", "p", "e"])

		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)
		frappe.db.set_single_value("Press Settings", "aws_access_key_id", "test")
		frappe.db.set_single_value("Press Settings", "aws_secret_access_key", "test")

		server_count_before = frappe.db.count("Server")
		database_server_count_before = frappe.db.count("Database Server")
		proxy_server_count_before = frappe.db.count("Proxy Server")

		boto3.client("iam").create_group(GroupName="fc-vpc-customer")

		Cluster.wait_for_aws_creds_seconds = 0
		self._create_cluster(
			aws_access_key_id=None, aws_secret_access_key=None, add_default_servers=True
		)

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
			Exception,
			self._create_cluster,
			aws_access_key_id=None,
			aws_secret_access_key=None,
		)


@patch.object(VirtualMachineImage, "wait_for_availability", new=MagicMock())
@patch("press.press.doctype.cluster.cluster.frappe.db.commit", new=MagicMock())
@patch(
	"press.press.doctype.cluster.cluster.frappe.enqueue_doc", new=foreground_enqueue_doc
)
@patch.object(VirtualMachineImage, "after_insert", new=MagicMock())
class TestPublicCluster(TestCluster):
	@mock_ec2
	@mock_ssm
	@patch.object(ProxyServer, "validate", new=MagicMock())
	def test_create_servers_without_vmis_throws_err(self):
		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)

		server_count_before = frappe.db.count("Server")
		database_server_count_before = frappe.db.count("Database Server")
		proxy_server_count_before = frappe.db.count("Proxy Server")
		cluster = create_test_cluster(name="Mumbai", region="ap-south-1", public=True)
		self.assertRaises(Exception, cluster.create_servers)
		server_count_after = frappe.db.count("Server")
		database_server_count_after = frappe.db.count("Database Server")
		proxy_server_count_after = frappe.db.count("Proxy Server")
		self.assertEqual(server_count_after, server_count_before)
		self.assertEqual(database_server_count_after, database_server_count_before)
		self.assertEqual(proxy_server_count_after, proxy_server_count_before)

	@mock_ec2
	@mock_ssm
	def test_add_images_in_public_cluster_only_adds_3_vms(self):
		self._setup_fake_vmis(["m", "f", "n", "p", "e"])
		vm_count_before = frappe.db.count("Virtual Machine Image")
		cluster = create_test_cluster(name="Frankfurt", region="eu-central-1", public=True)
		cluster.add_images()
		vm_count_after = frappe.db.count("Virtual Machine Image")
		self.assertNotEqual(vm_count_before, 0)
		self.assertEqual(vm_count_after, vm_count_before + 3)

	@mock_ec2
	@patch.object(ProxyServer, "validate", new=MagicMock())
	def test_creation_of_public_cluster_with_servers_creates_3(self):

		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)
		self._setup_fake_vmis(["m", "f", "n"])

		server_count_before = frappe.db.count("Server")
		database_server_count_before = frappe.db.count("Database Server")
		proxy_server_count_before = frappe.db.count("Proxy Server")

		create_test_cluster(
			name="Mumbai 2", region="ap-south-1", public=True, add_default_servers=True
		)

		server_count_after = frappe.db.count("Server")
		database_server_count_after = frappe.db.count("Database Server")
		proxy_server_count_after = frappe.db.count("Proxy Server")
		self.assertEqual(server_count_after, server_count_before + 1)
		self.assertEqual(database_server_count_after, database_server_count_before + 1)
		self.assertEqual(proxy_server_count_after, proxy_server_count_before + 1)

	@mock_iam
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
		cluster = self._create_cluster(
			aws_access_key_id=None, aws_secret_access_key=None, public=True
		)
		self.assertEqual(cluster.aws_access_key_id, key_pairs["AccessKey"]["AccessKeyId"])
		self.assertEqual(
			cluster.get_password("aws_secret_access_key"),
			key_pairs["AccessKey"]["SecretAccessKey"],
		)
		self.assertEqual(len(client.list_users()["Users"]), 1)
