# Copyright (c) 2021, Frappe and Contributors
# See license.txt


from unittest.mock import MagicMock, Mock, patch

import boto3
import frappe
from frappe.tests.utils import FrappeTestCase
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
@patch.object(Cluster, "check_quota", new=MagicMock(return_value=True))
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
	@patch.object(Cluster, "check_quota", new=MagicMock(return_value=True))
	def _create_cluster(
		self,
		aws_access_key_id=None,
		aws_secret_access_key=None,
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


@patch.object(Cluster, "after_insert", new=MagicMock())  # don't provision/copy images on insert
class TestClusterVPCFlowLogs(TestCluster):
	def _active_aws_cluster_with_vpc(self, bucket: str | None = "flow-logs-bucket") -> Cluster:
		"""An Active AWS cluster pointing at a real (moto) VPC."""
		cluster = create_test_cluster(name="Mumbai", region="ap-south-1")
		vpc = boto3.client("ec2", region_name=cluster.region).create_vpc(CidrBlock="10.3.0.0/16")
		cluster.vpc_id = vpc["Vpc"]["VpcId"]
		cluster.status = "Active"
		cluster.vpc_flow_logs_s3_bucket = bucket
		return cluster

	@mock_aws
	def test_setup_vpc_flow_logs_creates_flow_log_and_enables_flag(self):
		# moto can't validate an S3 ARN that carries a key prefix (valid on real AWS),
		# so stub the EC2 client and assert we call create_flow_logs correctly.
		cluster = self._active_aws_cluster_with_vpc()
		client = MagicMock()
		client.create_flow_logs.return_value = {"FlowLogIds": ["fl-123"], "Unsuccessful": []}
		with patch.object(Cluster, "get_aws_client", return_value=client):
			cluster.setup_vpc_flow_logs()

		self.assertTrue(cluster.vpc_flow_logs_enabled)
		self.assertEqual(cluster.flow_log_id, "fl-123")

		kwargs = client.create_flow_logs.call_args.kwargs
		self.assertEqual(kwargs["ResourceIds"], [cluster.vpc_id])
		self.assertEqual(kwargs["TrafficType"], "ALL")
		self.assertEqual(kwargs["LogDestinationType"], "s3")
		self.assertEqual(kwargs["LogDestination"], "arn:aws:s3:::flow-logs-bucket/flow-logs/mumbai/")

	@mock_aws
	def test_setup_vpc_flow_logs_throws_when_bucket_not_set(self):
		cluster = self._active_aws_cluster_with_vpc(bucket=None)
		self.assertRaisesRegex(
			frappe.ValidationError, "Set the VPC Flow Logs S3 bucket", cluster.setup_vpc_flow_logs
		)

	@mock_aws
	def test_setup_vpc_flow_logs_throws_when_already_enabled(self):
		cluster = self._active_aws_cluster_with_vpc()
		cluster.vpc_flow_logs_enabled = 1
		self.assertRaisesRegex(frappe.ValidationError, "already enabled", cluster.setup_vpc_flow_logs)

	@mock_aws
	def test_setup_vpc_flow_logs_throws_on_non_aws_cluster(self):
		cluster = self._active_aws_cluster_with_vpc()
		cluster.cloud_provider = "Generic"
		self.assertRaisesRegex(
			frappe.ValidationError, "only supported on AWS EC2", cluster.setup_vpc_flow_logs
		)
