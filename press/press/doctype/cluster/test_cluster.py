# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt


import typing
import frappe
import unittest
from press.press.doctype.proxy_server.proxy_server import ProxyServer
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain

from press.press.doctype.ssh_key.test_ssh_key import create_test_ssh_key

if typing.TYPE_CHECKING:
	from press.press.doctype.cluster.cluster import Cluster

from unittest.mock import MagicMock, patch

from moto import mock_ec2, mock_ssm


@patch("press.press.doctype.cluster.cluster.boto3.client", new=MagicMock())
def create_test_cluster(
	name: str = None,
	region: str = None,
	public: bool = False,
	add_default_servers: bool = False,
) -> "Cluster":
	"""Create test Cluster doc"""
	if frappe.db.exists("Cluster", name):
		return frappe.get_doc("Cluster", name)
	doc = frappe.get_doc(
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
			"add_default_servers": add_default_servers,
		}
	).insert(ignore_if_duplicate=True)
	doc.reload()
	return doc


class TestCluster(unittest.TestCase):
	def tearDown(self) -> None:
		frappe.db.rollback()

	@mock_ec2
	@mock_ssm
	def test_creation_cluster_in_new_region_copies_VMIs_from_other_region(self):
		from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
			create_test_virtual_machine_image,
		)

		cluster = create_test_cluster(name="Mumbai", region="ap-south-1")
		create_test_virtual_machine_image(cluster=cluster, series="m")
		create_test_virtual_machine_image(cluster=cluster, series="f")
		vmi_count_before = frappe.db.count("Virtual Machine Image")
		create_test_cluster(name="Frankfurt", region="eu-central-1")
		vmi_count_after = frappe.db.count("Virtual Machine Image")
		self.assertEqual(vmi_count_before, 2)
		self.assertEqual(vmi_count_after, vmi_count_before * 2)

	@mock_ec2
	@mock_ssm
	def test_creation_of_cluster_in_same_region_reuses_VMIs(self):
		from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
			create_test_virtual_machine_image,
		)

		cluster = create_test_cluster(name="Mumbai", region="ap-south-1")
		create_test_virtual_machine_image(cluster=cluster, series="m")
		create_test_virtual_machine_image(cluster=cluster, series="f")
		vmi_count_before = frappe.db.count("Virtual Machine Image")
		create_test_cluster(name="Mumbai 2", region="ap-south-1")
		vmi_count_after = frappe.db.count("Virtual Machine Image")
		self.assertEqual(vmi_count_before, 2)
		self.assertEqual(vmi_count_after, vmi_count_before)

	@mock_ec2
	@mock_ssm
	def test_creation_of_public_cluster_only_adds_3_vms(self):
		from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
			create_test_virtual_machine_image,
		)

		cluster = create_test_cluster(name="Mumbai", region="ap-south-1", public=True)
		create_test_virtual_machine_image(cluster=cluster, series="m")
		create_test_virtual_machine_image(cluster=cluster, series="f")
		create_test_virtual_machine_image(cluster=cluster, series="n")
		create_test_virtual_machine_image(cluster=cluster, series="p")
		create_test_virtual_machine_image(cluster=cluster, series="e")
		vm_count_before = frappe.db.count("Virtual Machine Image")
		create_test_cluster(name="Frankfurt", region="eu-central-1", public=True)
		vm_count_after = frappe.db.count("Virtual Machine Image")
		self.assertEqual(vm_count_before, 5)
		self.assertEqual(vm_count_after, vm_count_before + 3)

	@mock_ec2
	@patch.object(ProxyServer, "validate", new=MagicMock())
	def test_creation_of_public_cluster_with_servers_creates_3(self):
		from press.press.doctype.virtual_machine_image.test_virtual_machine_image import (
			create_test_virtual_machine_image,
		)

		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)
		cluster = create_test_cluster(
			name="Mumbai", region="ap-south-1", public=True, add_default_servers=False
		)
		create_test_virtual_machine_image(cluster=cluster, series="m")
		create_test_virtual_machine_image(cluster=cluster, series="f")
		create_test_virtual_machine_image(cluster=cluster, series="n")

		server_count_before = frappe.db.count("Server")
		database_server_count_before = frappe.db.count("Database Server")
		proxy_server_count_before = frappe.db.count("Proxy Server")

		cluster = frappe.get_doc(
			{
				"doctype": "Cluster",
				"name": "Mumbai 2",
				"region": "ap-south-1",
				"availability_zone": "ap-south-1a",
				"cloud_provider": "AWS EC2",
				"ssh_key": create_test_ssh_key().name,
				"subnet_cidr_block": "10.3.0.0/16",
				"aws_access_key_id": "test",
				"aws_secret_access_key": "test",
				"public": True,
				"add_default_servers": True,
			}
		)
		cluster.insert()
		server_count_after = frappe.db.count("Server")
		database_server_count_after = frappe.db.count("Database Server")
		proxy_server_count_after = frappe.db.count("Proxy Server")
		self.assertEqual(server_count_before, 0)
		self.assertEqual(database_server_count_before, 0)
		self.assertEqual(proxy_server_count_before, 0)
		self.assertEqual(server_count_after, 1)
		self.assertEqual(database_server_count_after, 1)
		self.assertEqual(proxy_server_count_after, 1)

	def test_create_cluster_without_aws_access_key_and_id_creates_user_in_predefined_group_and_then_adds_servers(
		self,
	):
		pass

	def test_create_cluster_without_aws_access_key_and_id_throws_err_if_the_group_doesnt_exist(
		self,
	):
		pass
