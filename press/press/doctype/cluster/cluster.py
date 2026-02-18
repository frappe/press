# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import base64
import hashlib
import ipaddress
import re
import time
import typing
from textwrap import wrap
from typing import ClassVar, Literal

import boto3
import frappe
import pydo
from frappe.model.document import Document
from frappe.utils.caching import redis_cache
from hcloud import APIException, Client
from hcloud.firewalls.domain import FirewallRule as HetznerFirewallRule
from hcloud.networks.domain import NetworkSubnet
from oci.config import validate_config
from oci.core import VirtualNetworkClient
from oci.core.models import (
	AddNetworkSecurityGroupSecurityRulesDetails,
	AddSecurityRuleDetails,
	CreateInternetGatewayDetails,
	CreateNetworkSecurityGroupDetails,
	CreateSubnetDetails,
	CreateVcnDetails,
	PortRange,
	RouteRule,
	TcpOptions,
	UpdateRouteTableDetails,
)
from oci.identity import IdentityClient

from press.press.doctype.virtual_machine_image.virtual_machine_image import (
	VirtualMachineImage,
)
from press.utils import get_current_team, unique

if typing.TYPE_CHECKING:
	from collections.abc import Generator

	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.log_server.log_server import LogServer
	from press.press.doctype.monitor_server.monitor_server import MonitorServer
	from press.press.doctype.press_job.press_job import PressJob
	from press.press.doctype.press_settings.press_settings import PressSettings
	from press.press.doctype.server.server import BaseServer, Server
	from press.press.doctype.server_plan.server_plan import ServerPlan
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

DEFAULT_SERVER_TITLE = "First"


class Cluster(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		availability_zone: DF.Data | None
		aws_access_key_id: DF.Data | None
		aws_secret_access_key: DF.Password | None
		beta: DF.Check
		by_default_select_unified_mode: DF.Check
		cidr_block: DF.Data | None
		cloud_provider: DF.Literal["AWS EC2", "Generic", "OCI", "Hetzner", "DigitalOcean"]
		default_app_server_plan: DF.Link | None
		default_app_server_plan_type: DF.Link | None
		default_db_server_plan: DF.Link | None
		default_db_server_plan_type: DF.Link | None
		description: DF.Data | None
		digital_ocean_api_token: DF.Password | None
		enable_autoscaling: DF.Check
		has_add_on_storage_support: DF.Check
		has_arm_support: DF.Check
		has_unified_server_support: DF.Check
		hetzner_api_token: DF.Password | None
		hybrid: DF.Check
		image: DF.AttachImage | None
		monitoring_password: DF.Password | None
		network_acl_id: DF.Data | None
		oci_private_key: DF.Password | None
		oci_public_key: DF.Code | None
		oci_tenancy: DF.Data | None
		oci_user: DF.Data | None
		proxy_security_group_id: DF.Data | None
		public: DF.Check
		region: DF.Link | None
		repository: DF.Data | None
		route_table_id: DF.Data | None
		security_group_id: DF.Data | None
		ssh_key: DF.Link | None
		status: DF.Literal["Active", "Copying Images", "Archived"]
		subnet_cidr_block: DF.Data | None
		subnet_id: DF.Data | None
		team: DF.Link | None
		title: DF.Data | None
		vpc_id: DF.Data | None
	# end: auto-generated types

	dashboard_fields: ClassVar[list[str]] = ["title", "image", "has_add_on_storage_support"]

	base_servers: ClassVar[dict[str, str]] = {
		"Proxy Server": "n",
		"Database Server": "m",
		"Server": "f",  # App server is last as it needs both proxy and db server
	}

	private_servers: ClassVar[dict] = {
		# TODO: Uncomment these when they are implemented
		# "Monitor Server": "p",
		# "Log Server": "e,
	}

	secondary_server_series: ClassVar[str] = "fs"
	unified_server_series: ClassVar[str] = "u"

	wait_for_aws_creds_seconds = 20

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		if filters and filters.get("group"):
			rg = frappe.get_doc("Release Group", filters.get("group"))
			cluster_names = rg.get_clusters()
			return frappe.get_all(
				"Cluster",
				fields=["name", "title", "image", "beta"],
				filters={"name": ("in", cluster_names)},
			)
		return None

	def validate(self):
		self.validate_monitoring_password()
		self.validate_cidr_block()
		if self.cloud_provider == "AWS EC2":
			self.validate_aws_credentials()
		elif self.cloud_provider == "OCI":
			self.set_oci_availability_zone()
		elif self.cloud_provider == "Hetzner":
			self.validate_hetzner_api_token()

	def validate_hetzner_api_token(self):
		api_token = self.get_password("hetzner_api_token")
		client = Client(token=api_token)
		try:
			# Check if we can list servers (read access)
			servers = client.servers.get_all()

			if servers is None:
				frappe.throw("API token does not have read access to the Hetzner Cloud.")

		except APIException as e:
			# Handle specific API exceptions like unauthorized access
			if e.code == "unauthorized":
				frappe.throw("API token is invalid or does not have the correct permissions.")
			else:
				frappe.throw(f"An error occurred while validating the API token: {e}")

	def validate_aws_credentials(self):
		settings: "PressSettings" = frappe.get_single("Press Settings")
		if self.public and not self.aws_access_key_id:
			self.aws_access_key_id = settings.aws_access_key_id
			self.aws_secret_access_key = settings.get_password("aws_secret_access_key")
		elif not self.aws_access_key_id or not self.aws_secret_access_key:
			root_client = settings.boto3_iam_client
			group = (  # make sure group exists
				root_client.get_group(GroupName="fc-vpc-customer").get("Group", {}).get("GroupName")
			)
			root_client.create_user(
				UserName=frappe.scrub(self.name),
			)
			root_client.add_user_to_group(GroupName=group, UserName=frappe.scrub(self.name))
			access_key_pair = root_client.create_access_key(
				UserName=frappe.scrub(self.name),
			)["AccessKey"]

			self.aws_access_key_id = access_key_pair["AccessKeyId"]
			self.aws_secret_access_key = access_key_pair["SecretAccessKey"]
			from time import sleep

			sleep(self.wait_for_aws_creds_seconds)  # wait for key to be valid

	def after_insert(self):
		if self.cloud_provider == "AWS EC2":
			self.provision_on_aws_ec2()
		elif self.cloud_provider == "OCI":
			self.provision_on_oci()
		elif self.cloud_provider == "Hetzner":
			self.provision_on_hetzner()
		elif self.cloud_provider == "DigitalOcean":
			self.provision_on_digital_ocean()

	def provision_on_digital_ocean(self):
		api_token = self.get_password("digital_ocean_api_token")
		client = pydo.Client(api_token)

		# Provision VPC
		self._add_digital_ocean_vpc(client=client)
		# Add ssh key to digital ocean, if it doesn't already exist
		self._add_digital_ocean_ssh_keys(client=client)
		# Add firewall to digital ocean, if it doesn't already exist
		self._add_digital_ocean_firewall(client=client)
		# Add proxy firewall to digital ocean, if it doesn't already exist
		self._add_digital_ocean_proxy_firewall(client=client)

		self.save()

	def _add_digital_ocean_vpc(self, client):
		"""Provisions a VPC on Digital Ocean"""
		try:
			network = client.vpcs.create(
				{
					"name": f"Frappe - Cloud - {self.name}".replace(" ", ""),
					"description": f"VPC for Frappe Cloud {self.name} Cluster",
					"region": self.region,
					"ip_range": self.cidr_block,
				}
			)
			self.vpc_id = network["vpc"]["id"]
		except Exception as e:
			frappe.throw(f"Failed to provision VPC on Digital Ocean: {e!s}")

	def _add_digital_ocean_ssh_keys(self, client):
		"""Adds the SSH key to Digital Ocean if it doesn't already exist"""
		try:
			client.ssh_keys.create(
				{
					"name": self.ssh_key,
					"public_key": frappe.db.get_value("SSH Key", self.ssh_key, "public_key"),
				}
			)
		except Exception as e:
			if "SSH Key is already in use" in str(e):
				return
			frappe.throw(f"Failed to create SSH Key on Digital Ocean: {e!s}")

	def _add_digital_ocean_proxy_firewall(self, client):
		"""Adds the proxy firewall to Digital Ocean if it doesn't already exist"""
		firewalls = client.firewalls.list()
		firewalls = firewalls.get("firewalls", [])
		existing_firewalls = [
			fw
			for fw in firewalls
			if fw["name"] == f"Frappe Cloud - {self.name} - Proxy - Security Group".replace(" ", "")
		]
		if existing_firewalls:
			self.proxy_security_group_id = existing_firewalls[0]["id"]
			return

		try:
			firewall = client.firewalls.create(
				{
					"name": f"Frappe Cloud - {self.name} - Proxy - Security Group".replace(" ", ""),
					"inbound_rules": [
						{"protocol": "tcp", "ports": "2222", "sources": {"addresses": ["0.0.0.0/0"]}},
						{"protocol": "tcp", "ports": "3306", "sources": {"addresses": ["0.0.0.0/0"]}},
					],
					"outbound_rules": [
						{"protocol": "tcp", "ports": "0", "destinations": {"addresses": ["0.0.0.0/0"]}},
						{"protocol": "udp", "ports": "0", "destinations": {"addresses": ["0.0.0.0/0"]}},
						{"protocol": "icmp", "ports": "0", "destinations": {"addresses": ["0.0.0.0/0"]}},
					],
				}
			)
			self.proxy_security_group_id = firewall["firewall"]["id"]
		except Exception as e:
			frappe.throw(f"Failed to create Proxy Firewall on Digital Ocean: {e!s}")

	def _add_digital_ocean_firewall(self, client):
		"""Adds the firewall to Digital Ocean if it doesn't already exist"""
		firewalls = client.firewalls.list()
		firewalls = firewalls.get("firewalls", [])
		existing_firewalls = [
			fw
			for fw in firewalls
			if fw["name"] == f"Frappe Cloud - {self.name} - Security Group".replace(" ", "")
		]
		if existing_firewalls:
			self.security_group_id = existing_firewalls[0]["id"]
			return

		try:
			firewall = client.firewalls.create(
				{
					"name": f"Frappe Cloud - {self.name} - Security Group".replace(" ", ""),
					"inbound_rules": [
						{"protocol": "tcp", "ports": "80", "sources": {"addresses": ["0.0.0.0/0"]}},
						{"protocol": "tcp", "ports": "443", "sources": {"addresses": ["0.0.0.0/0"]}},
						{"protocol": "tcp", "ports": "22", "sources": {"addresses": ["0.0.0.0/0"]}},
						{
							"protocol": "tcp",
							"ports": "3306",
							"sources": {"addresses": [self.subnet_cidr_block]},
						},
						{
							"protocol": "tcp",
							"ports": "2049",
							"sources": {"addresses": [self.subnet_cidr_block]},
						},
						{
							"protocol": "tcp",
							"ports": "11000-20000",
							"sources": {"addresses": [self.subnet_cidr_block]},
						},
						{
							"protocol": "tcp",
							"ports": "22000-22999",
							"sources": {"addresses": [self.subnet_cidr_block]},
						},
						{"protocol": "icmp", "ports": "0", "sources": {"addresses": ["0.0.0.0/0"]}},
					],
					"outbound_rules": [
						{"protocol": "tcp", "ports": "0", "destinations": {"addresses": ["0.0.0.0/0"]}},
						{"protocol": "udp", "ports": "0", "destinations": {"addresses": ["0.0.0.0/0"]}},
						{"protocol": "icmp", "ports": "0", "destinations": {"addresses": ["0.0.0.0/0"]}},
					],
				}
			)

			if "id" not in firewall.get("firewall", {}):
				frappe.throw("Failed to create Firewall on Digital Ocean.")

			self.security_group_id = firewall["firewall"]["id"]
		except Exception as e:
			frappe.throw(f"Failed to create Firewall on Digital Ocean: {e!s}")

		frappe.msgprint(
			"To add this cluster to monitoring, go to the Monitor Server and trigger the 'Reconfigure Monitor Server' action from the Actions menu."
		)

	def provision_on_hetzner(self):
		try:
			# Get Hetzner API token from Press Settings
			api_token = self.get_password("hetzner_api_token")

			client = Client(token=api_token)

			# Create the network (VPC) on Hetzner
			network = client.networks.create(
				name=f"Frappe Cloud - {self.name}",
				ip_range=self.cidr_block,  # The IP range for the entire network (CIDR)
				subnets=[
					NetworkSubnet(
						type="cloud",  # VPCs in Hetzner are defined as 'cloud' subnets
						ip_range=self.subnet_cidr_block,
						network_zone=self.availability_zone,
					)
				],
				routes=[],
			)
			self.vpc_id = network.id
			self.save()
		except APIException as e:
			frappe.throw(f"Failed to provision network on Hetzner: {e!s}")

		# Create the SSH Key on Hetzner
		try:
			client.ssh_keys.create(
				name=self.ssh_key,
				public_key=frappe.db.get_value("SSH Key", self.ssh_key, "public_key"),
			)
		except APIException:
			# If the SSH key already exists, retrieve it
			existing_keys = client.ssh_keys.get_all(name=self.ssh_key)
			if len(existing_keys) == 0:
				frappe.throw(f"SSH Key creation failed and '{self.ssh_key}' not found on Hetzner Cloud.")

		try:
			# Create Server Firewall
			server_firewall = client.firewalls.create(
				name=f"Frappe Cloud - {self.name} - Security Group",
				rules=[
					HetznerFirewallRule(
						description="HTTP from anywhere",
						direction="in",
						protocol="tcp",
						port="80",
						source_ips=["0.0.0.0/0"],
					),
					HetznerFirewallRule(
						description="HTTPS from anywhere",
						direction="in",
						protocol="tcp",
						port="443",
						source_ips=["0.0.0.0/0"],
					),
					HetznerFirewallRule(
						description="SSH from anywhere",
						direction="in",
						protocol="tcp",
						port="22",
						source_ips=["0.0.0.0/0"],
					),
					HetznerFirewallRule(
						description="MariaDB from private network",
						direction="in",
						protocol="tcp",
						port="3306",
						source_ips=[self.subnet_cidr_block],
					),
					HetznerFirewallRule(
						description="NFS from private network",
						direction="in",
						protocol="tcp",
						port="2049",
						source_ips=[self.subnet_cidr_block],
					),
					HetznerFirewallRule(
						description="Redis from private network",
						direction="in",
						protocol="tcp",
						port="11000-20000",
						source_ips=[self.subnet_cidr_block],
					),
					HetznerFirewallRule(
						description="SSH from private network",
						direction="in",
						protocol="tcp",
						port="22000-22999",
						source_ips=[self.subnet_cidr_block],
					),
					HetznerFirewallRule(
						description="ICMP from anywhere",
						direction="in",
						protocol="icmp",
						port=None,
						source_ips=["0.0.0.0/0"],
					),
				],
			)
			self.security_group_id = server_firewall.firewall.id
			self.save()
		except APIException as e:
			frappe.throw(f"Failed to provision server firewall on Hetzner: {e!s}")

		try:
			# Create Proxy Server Firewall
			proxy_firewall = client.firewalls.create(
				f"Frappe Cloud - {self.name} - Proxy - Security Group",
				rules=[
					HetznerFirewallRule(
						description="SSH proxy from anywhere",
						direction="in",
						protocol="tcp",
						port="2222",
						source_ips=["0.0.0.0/0"],
					),
					HetznerFirewallRule(
						description="MariaDB from anywhere",
						direction="in",
						protocol="tcp",
						port="3306",
						source_ips=["0.0.0.0/0"],
					),
				],
			)
			self.proxy_security_group_id = proxy_firewall.firewall.id
			self.save()
		except APIException as e:
			frappe.throw(f"Failed to provision proxy server firewall on Hetzner: {e!s}")

	def on_trash(self):
		machines = frappe.get_all(
			"Virtual Machine",
			{"cluster": self.name, "status": "Terminated"},
			pluck="name",
		)
		for machine in machines:
			frappe.delete_doc("Virtual Machine", machine)

	@frappe.whitelist()
	def add_images(self):
		if self.images_available == 1:
			frappe.throw("Images are already available", frappe.ValidationError)
		if not set(self.get_other_region_vmis(get_series=True)) - set(
			self.get_same_region_vmis(get_series=True)
		):
			frappe.throw(
				"Images for required series not available in other regions. Create Images from server docs.",
				frappe.ValidationError,
			)
		frappe.enqueue_doc(self.doctype, self.name, "_add_images", queue="long", timeout=1200)

	def _add_images(self):
		"""Copies VMIs required for the cluster"""
		self.db_set("status", "Copying Images")
		frappe.db.commit()
		for vmi in self.copy_virtual_machine_images():
			vmi.wait_for_availability()
		self.reload()
		self.db_set("status", "Active")

	@property
	def images_available(self) -> float:
		return len(self.get_same_region_vmis()) / len(self.server_doctypes)

	def validate_cidr_block(self):
		if not self.cidr_block:
			blocks = ipaddress.ip_network("10.0.0.0/8").subnets(new_prefix=16)
			existing_blocks = ["10.0.0.0/16"] + frappe.get_all("Cluster", ["cidr_block"], pluck="cidr_block")  # noqa: RUF005
			for block in blocks:
				cidr_block = str(block)
				if cidr_block not in existing_blocks:
					self.cidr_block = cidr_block
					self.subnet_cidr_block = cidr_block
					break
		if not self.cidr_block:
			frappe.throw("No CIDR block available", frappe.ValidationError)

	def validate_monitoring_password(self):
		if not self.monitoring_password:
			self.monitoring_password = frappe.generate_hash()

	def provision_on_aws_ec2(self):
		client = self.get_aws_client()

		response = client.create_vpc(
			AmazonProvidedIpv6CidrBlock=False,
			InstanceTenancy="default",
			TagSpecifications=[
				{
					"ResourceType": "vpc",
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name}"}],
				},
			],
			CidrBlock=self.cidr_block,
		)
		self.vpc_id = response["Vpc"]["VpcId"]

		client.modify_vpc_attribute(VpcId=self.vpc_id, EnableDnsHostnames={"Value": True})

		response = client.create_subnet(
			TagSpecifications=[
				{
					"ResourceType": "subnet",
					"Tags": [
						{
							"Key": "Name",
							"Value": f"Frappe Cloud - {self.name} - Public Subnet",
						}
					],
				},
			],
			AvailabilityZone=self.availability_zone,
			VpcId=self.vpc_id,
			CidrBlock=self.subnet_cidr_block,
		)
		self.subnet_id = response["Subnet"]["SubnetId"]

		response = client.create_internet_gateway(
			TagSpecifications=[
				{
					"ResourceType": "internet-gateway",
					"Tags": [
						{
							"Key": "Name",
							"Value": f"Frappe Cloud - {self.name} - Internet Gateway",
						},
					],
				},
			],
		)

		self.internet_gateway_id = response["InternetGateway"]["InternetGatewayId"]

		client.attach_internet_gateway(InternetGatewayId=self.internet_gateway_id, VpcId=self.vpc_id)

		response = client.describe_route_tables(
			Filters=[{"Name": "vpc-id", "Values": [self.vpc_id]}],
		)
		self.route_table_id = response["RouteTables"][0]["RouteTableId"]

		client.create_route(
			DestinationCidrBlock="0.0.0.0/0",
			GatewayId=self.internet_gateway_id,
			RouteTableId=self.route_table_id,
		)

		client.create_tags(
			Resources=[self.route_table_id],
			Tags=[{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Route Table"}],
		)

		response = client.describe_network_acls(
			Filters=[{"Name": "vpc-id", "Values": [self.vpc_id]}],
		)
		self.network_acl_id = response["NetworkAcls"][0]["NetworkAclId"]
		client.create_tags(
			Resources=[self.network_acl_id],
			Tags=[{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Network ACL"}],
		)

		response = client.create_security_group(
			GroupName=f"Frappe Cloud - {self.name} - Security Group",
			Description="Allow Everything",
			VpcId=self.vpc_id,
			TagSpecifications=[
				{
					"ResourceType": "security-group",
					"Tags": [
						{
							"Key": "Name",
							"Value": f"Frappe Cloud - {self.name} - Security Group",
						},
					],
				},
			],
		)
		self.security_group_id = response["GroupId"]

		client.authorize_security_group_ingress(
			GroupId=self.security_group_id,
			IpPermissions=[
				{
					"FromPort": 80,
					"IpProtocol": "tcp",
					"IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTP from anywhere"}],
					"ToPort": 80,
				},
				{
					"FromPort": 443,
					"IpProtocol": "tcp",
					"IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTPS from anywhere"}],
					"ToPort": 443,
				},
				{
					"FromPort": 22,
					"IpProtocol": "tcp",
					"IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH from anywhere"}],
					"ToPort": 22,
				},
				{
					"FromPort": 3306,
					"IpProtocol": "tcp",
					"IpRanges": [
						{
							"CidrIp": self.subnet_cidr_block,
							"Description": "MariaDB from private network",
						}
					],
					"ToPort": 3306,
				},
				{
					"FromPort": 2049,
					"IpProtocol": "tcp",
					"IpRanges": [
						{
							"CidrIp": self.subnet_cidr_block,
							"Description": "NFS Access from private network",
						}
					],
					"ToPort": 2049,
				},
				{
					"FromPort": 11000,
					"IpProtocol": "tcp",
					"IpRanges": [
						{
							"CidrIp": self.subnet_cidr_block,
							"Description": "Redis from private network",
						}
					],
					"ToPort": 20000,
				},
				{
					"FromPort": 22000,
					"IpProtocol": "tcp",
					"IpRanges": [
						{
							"CidrIp": self.subnet_cidr_block,
							"Description": "SSH from private network",
						}
					],
					"ToPort": 22999,
				},
				{
					"FromPort": -1,
					"IpProtocol": "icmp",
					"IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "ICMP from anywhere"}],
					"ToPort": -1,
				},
			],
		)
		self.create_proxy_security_group()

		try:  # noqa: SIM105
			# We don't care if the key already exists in this region
			response = client.import_key_pair(
				KeyName=self.ssh_key,
				PublicKeyMaterial=frappe.db.get_value("SSH Key", self.ssh_key, "public_key"),
				TagSpecifications=[
					{
						"ResourceType": "key-pair",
						"Tags": [{"Key": "Name", "Value": self.ssh_key}],
					},
				],
			)
		except Exception:
			pass
		self.save()

	def create_proxy_security_group(self):
		client = self.get_aws_client()
		response = client.create_security_group(
			GroupName=f"Frappe Cloud - {self.name} - Proxy - Security Group",
			Description="Allow Everything on Proxy",
			VpcId=self.vpc_id,
			TagSpecifications=[
				{
					"ResourceType": "security-group",
					"Tags": [
						{
							"Key": "Name",
							"Value": f"Frappe Cloud - {self.name} - Proxy - Security Group",
						},
					],
				},
			],
		)
		self.proxy_security_group_id = response["GroupId"]

		client.authorize_security_group_ingress(
			GroupId=self.proxy_security_group_id,
			IpPermissions=[
				{
					"FromPort": 2222,
					"IpProtocol": "tcp",
					"IpRanges": [
						{
							"CidrIp": "0.0.0.0/0",
							"Description": "SSH proxy from anywhere",
						}
					],
					"ToPort": 2222,
				},
				{
					"FromPort": 3306,
					"IpProtocol": "tcp",
					"IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "MariaDB from anywhere"}],
					"ToPort": 3306,
				},
			],
		)

	def get_oci_public_key_fingerprint(self):
		match = re.match(
			r"-*BEGIN PUBLIC KEY-*(.*?)-*END PUBLIC KEY-*",
			"".join(self.oci_public_key.splitlines()),
		)
		base64_key = match.group(1).encode("utf-8")
		binary_key = base64.b64decode(base64_key)
		digest = hashlib.md5(binary_key).hexdigest()
		return ":".join(wrap(digest, 2))

	def get_oci_config(self):
		# Stupid Password field, replaces newines with spaces
		private_key = (
			self.get_password("oci_private_key").replace(" ", "\n").replace("\nPRIVATE\n", " PRIVATE ")
		)

		config = {
			"user": self.oci_user,
			"fingerprint": self.get_oci_public_key_fingerprint(),
			"tenancy": self.oci_tenancy,
			"region": self.region,
			"key_content": private_key,
		}
		validate_config(config)
		return config

	def set_oci_availability_zone(self):
		identity_client = IdentityClient(self.get_oci_config())
		availability_domain = identity_client.list_availability_domains(self.oci_tenancy).data[0].name
		self.availability_zone = availability_domain

	def provision_on_oci(self):
		vcn_client = VirtualNetworkClient(self.get_oci_config())
		vcn = vcn_client.create_vcn(
			CreateVcnDetails(
				compartment_id=self.oci_tenancy,
				display_name=f"Frappe Cloud - {self.name}",
				cidr_block=self.subnet_cidr_block,
			)
		).data
		self.vpc_id = vcn.id
		self.route_table_id = vcn.default_route_table_id
		self.network_acl_id = vcn.default_security_list_id

		time.sleep(1)
		# https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml
		# 1 ICMP
		# 6 TCP
		# 17 UDP
		security_group = vcn_client.create_network_security_group(
			CreateNetworkSecurityGroupDetails(
				compartment_id=self.oci_tenancy,
				display_name=f"Frappe Cloud - {self.name} - Security Group",
				vcn_id=self.vpc_id,
			)
		).data
		self.security_group_id = security_group.id

		time.sleep(1)
		vcn_client.add_network_security_group_security_rules(
			self.security_group_id,
			AddNetworkSecurityGroupSecurityRulesDetails(
				security_rules=[
					AddSecurityRuleDetails(
						description="HTTP from anywhere",
						direction="INGRESS",
						protocol="6",
						source="0.0.0.0/0",
						tcp_options=TcpOptions(destination_port_range=PortRange(min=80, max=80)),
					),
					AddSecurityRuleDetails(
						description="HTTPS from anywhere",
						direction="INGRESS",
						protocol="6",
						source="0.0.0.0/0",
						tcp_options=TcpOptions(destination_port_range=PortRange(min=443, max=443)),
					),
					AddSecurityRuleDetails(
						description="SSH from anywhere",
						direction="INGRESS",
						protocol="6",
						source="0.0.0.0/0",
						tcp_options=TcpOptions(destination_port_range=PortRange(min=22, max=22)),
					),
					AddSecurityRuleDetails(
						description="MariaDB from private network",
						direction="INGRESS",
						protocol="6",
						source=self.subnet_cidr_block,
						tcp_options=TcpOptions(destination_port_range=PortRange(min=3306, max=3306)),
					),
					AddSecurityRuleDetails(
						description="SSH from private network",
						direction="INGRESS",
						protocol="6",
						source=self.subnet_cidr_block,
						tcp_options=TcpOptions(destination_port_range=PortRange(min=22000, max=22999)),
					),
					AddSecurityRuleDetails(
						description="ICMP from anywhere",
						direction="INGRESS",
						protocol="1",
						source="0.0.0.0/0",
						# Ignoring IcmpOptions for now. https://docs.oracle.com/en-us/iaas/tools/python/2.117.0/api/core/models/oci.core.models.IcmpOptions.html#oci.core.models.IcmpOptions
					),
					AddSecurityRuleDetails(
						description="Everything to anywhere",
						direction="EGRESS",
						protocol="all",
						destination="0.0.0.0/0",
					),
				],
			),
		)

		time.sleep(1)
		proxy_security_group = vcn_client.create_network_security_group(
			CreateNetworkSecurityGroupDetails(
				compartment_id=self.oci_tenancy,
				display_name=f"Frappe Cloud - {self.name} - Proxy - Security Group",
				vcn_id=self.vpc_id,
			)
		).data
		self.proxy_security_group_id = proxy_security_group.id

		time.sleep(1)
		vcn_client.add_network_security_group_security_rules(  # noqa: B018
			self.proxy_security_group_id,
			AddNetworkSecurityGroupSecurityRulesDetails(
				security_rules=[
					AddSecurityRuleDetails(
						description="SSH proxy from anywhere",
						direction="INGRESS",
						protocol="6",
						source="0.0.0.0/0",
						tcp_options=TcpOptions(destination_port_range=PortRange(min=2222, max=2222)),
					),
					AddSecurityRuleDetails(
						description="MariaDB from anywhere",
						direction="INGRESS",
						protocol="6",
						source="0.0.0.0/0",
						tcp_options=TcpOptions(destination_port_range=PortRange(min=3306, max=3306)),
					),
					AddSecurityRuleDetails(
						description="NFS from from anywhere",
						direction="INGRESS",
						protocol="6",
						source="0.0.0.0/0",
						tcp_options=TcpOptions(destination_port_range=PortRange(min=2049, max=2049)),
					),
					AddSecurityRuleDetails(
						description="Everything to anywhere",
						direction="EGRESS",
						protocol="all",
						destination="0.0.0.0/0",
					),
				],
			),
		).data

		time.sleep(1)
		subnet = vcn_client.create_subnet(
			CreateSubnetDetails(
				compartment_id=self.oci_tenancy,
				display_name=f"Frappe Cloud - {self.name} - Public Subnet",
				vcn_id=self.vpc_id,
				cidr_block=self.subnet_cidr_block,
				route_table_id=self.route_table_id,
				security_list_ids=[self.network_acl_id],
			)
		).data
		self.subnet_id = subnet.id

		time.sleep(1)
		# Don't associate IGW with any route table Otherwise it fails with "Rules in the route table must use private IP"
		internet_gateway = vcn_client.create_internet_gateway(
			CreateInternetGatewayDetails(
				compartment_id=self.oci_tenancy,
				display_name=f"Frappe Cloud - {self.name} - Internet Gateway",
				is_enabled=True,
				vcn_id=self.vpc_id,
			)
		).data
		self.internet_gateway_id = internet_gateway.id

		time.sleep(1)
		vcn_client.update_route_table(
			self.route_table_id,
			UpdateRouteTableDetails(
				route_rules=[
					RouteRule(
						destination="0.0.0.0/0",
						network_entity_id=self.internet_gateway_id,
					)
				]
			),
		)

		self.save()

	def get_available_vmi(self, series, platform=None) -> str | None:
		"""Virtual Machine Image available in region [if not hetzner] for given series"""
		region = self.region if self.cloud_provider != "Hetzner" else None
		return VirtualMachineImage.get_available_for_series(
			series, cloud_provider=self.cloud_provider, region=region, platform=platform
		)

	@property
	def server_doctypes(self):
		server_doctypes = {**self.base_servers}
		if not self.public:
			server_doctypes = {**server_doctypes, **self.private_servers}
		return server_doctypes

	def get_same_region_vmis(self, platform="x86_64", get_series=False) -> list[str]:
		vmis = []
		for series in list(self.server_doctypes.values()):
			vmis.extend(
				frappe.get_all(
					"Virtual Machine Image",
					filters={
						"region": self.region,
						"series": series,
						"status": "Available",
						"public": True,
						"platform": "x86_64" if series == "n" else platform,
						"cloud_provider": self.cloud_provider,
					},
					limit=1,
					order_by="creation DESC",
					pluck="name" if not get_series else "series",
				)
			)

		return vmis

	def get_other_region_vmis(self, platform="x86_64", get_series=False) -> list[str]:
		vmis = []
		for series in list(self.server_doctypes.values()):
			vmis.extend(
				frappe.get_all(
					"Virtual Machine Image",
					filters={
						"region": ("!=", self.region),
						"series": series,
						"status": "Available",
						"public": True,
						"platform": "x86_64" if series == "n" else platform,
						"cloud_provider": self.cloud_provider,
					},
					limit=1,
					order_by="creation DESC",
					pluck="name" if not get_series else "series",
				)
			)

		return vmis

	def copy_virtual_machine_images(self) -> Generator[VirtualMachineImage, None, None]:
		"""Creates VMIs required for the cluster"""
		copies = []
		for vmi in set(self.get_other_region_vmis()) - set(self.get_same_region_vmis()):
			copies.append(
				VirtualMachineImage(
					"Virtual Machine Image",
					vmi,
				).copy_image(str(self.name))
			)
			frappe.db.commit()
		yield from copies

	@frappe.whitelist()
	def create_proxy(self):
		"""Creates a proxy server for the cluster"""
		if self.get_same_region_vmis(get_series=True).count("n") < 1:
			frappe.throw(
				"Proxy Image not available in this region. Add them or wait for copy to complete",
				frappe.ValidationError,
			)
		if self.status != "Active":
			frappe.throw("Cluster is not active", frappe.ValidationError)

		self.create_server("Proxy Server", DEFAULT_SERVER_TITLE)

	@frappe.whitelist()
	def create_servers(self):
		"""Creates servers for the cluster"""
		if self.images_available < 1:
			frappe.throw(
				"Images are not available. Add them or wait for copy to complete",
				frappe.ValidationError,
			)
		if self.status != "Active":
			frappe.throw("Cluster is not active", frappe.ValidationError)

		for doctype, _ in self.base_servers.items():
			# TODO: remove Test title #
			server, _ = self.create_server(
				doctype,
				DEFAULT_SERVER_TITLE,
			)
			match doctype:  # for populating Server doc's fields; assume the trio is created together
				case "Database Server":
					self.database_server = server.name
				case "Proxy Server":
					self.proxy_server = server.name
		if self.public:
			return
		for doctype, _ in self.private_servers.items():
			self.create_server(
				doctype,
				DEFAULT_SERVER_TITLE,
				create_subscription=False,
			)

	def get_aws_client(self):
		return boto3.client(
			"ec2",
			region_name=self.region,
			aws_access_key_id=self.aws_access_key_id,
			aws_secret_access_key=self.get_password("aws_secret_access_key"),
		)

	def get_hetzner_client(self):
		from hcloud import Client

		api_token = self.get_password("hetzner_api_token")
		return Client(token=api_token)

	def _check_aws_machine_availability(self, machine_type: str) -> bool:
		"""Check if instance offering in the region is present"""
		client = self.get_aws_client()
		response = client.describe_instance_type_offerings(
			Filters=[{"Name": "instance-type", "Values": [machine_type]}]
		)
		return bool(response.get("InstanceTypeOfferings"))

	def _check_oci_machine_availability(self, machine_type: str) -> bool:
		"""
		We use machine type VM.Standard.E4.Flex or all OCI machines
		This simply checks if VM.Standard.E4.Flex is present in the region
		and the memory and cpu options are within supported limit.
		"""
		return True

	@redis_cache(ttl=60)
	def _check_hetzner_machine_availability(self, machine_type: str) -> bool:
		client = self.get_hetzner_client()
		machine = client.server_types.get_by_name(machine_type)
		if not machine:
			return False

		machine_id = machine.id

		datacenters = client.datacenters.get_all()
		datacenters = [dc for dc in datacenters if dc.location.name == self.region]
		for dc in datacenters:
			for st in dc.server_types.available:
				if st.id == machine_id:
					return True
		return False

	@frappe.whitelist()
	def check_machine_availability(self, machine_type: str) -> bool:
		"Check availability of machine in the region before allowing provision"
		if self.cloud_provider == "AWS EC2":
			return self._check_aws_machine_availability(machine_type)
		if self.cloud_provider == "OCI":
			return self._check_oci_machine_availability(machine_type)
		if self.cloud_provider == "Hetzner":
			return self._check_hetzner_machine_availability(machine_type)

		return True

	def create_vm(
		self,
		machine_type: str,
		platform: str,
		disk_size: int,
		domain: str,
		series: str,
		team: str,
		data_disk_snapshot: str | None = None,
		temporary_server: bool = False,
		kms_key_id: str | None = None,
		vmi_series: str | None = None,
	) -> "VirtualMachine":
		"""Creates a Virtual Machine for the cluster
		temporary_server: If you are creating a temporary server for some special purpose, set this to True.
				This will use a different nameing series `t` for the server to avoid conflicts
				with the regular servers.
		"""
		vmi_series = vmi_series or series
		return frappe.get_doc(
			{
				"doctype": "Virtual Machine",
				"cluster": self.name,
				"domain": domain,
				"series": "t" if temporary_server else series,
				"disk_size": disk_size,
				"machine_type": machine_type,
				"platform": platform,
				"virtual_machine_image": self.get_available_vmi(vmi_series, platform=platform),
				"team": team,
				"data_disk_snapshot": data_disk_snapshot,
				"kms_key_id": kms_key_id,
			},
		).insert()

	def get_default_instance_type(self):
		if self.cloud_provider == "AWS EC2":
			return "t3.medium"
		if self.cloud_provider == "OCI":
			return "VM.Standard.E4.Flex"
		if self.cloud_provider == "Hetzner":
			return "cpx21"
		return None

	def get_or_create_basic_plan(self, server_type) -> ServerPlan:
		plan = frappe.db.exists("Server Plan", f"Basic Cluster - {server_type}")
		if plan:
			return frappe.get_doc("Server Plan", f"Basic Cluster - {server_type}")
		return frappe.get_doc(
			{
				"doctype": "Server Plan",
				"name": f"Basic Cluster - {server_type}",
				"title": f"Basic Cluster - {server_type}",
				"instance_type": self.get_default_instance_type(),
				"price_inr": 0,
				"price_usd": 0,
				"vcpu": 2,
				"memory": 4096,
				"disk": 50,
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

	def create_unified_server(
		self,
		title: str,
		plan: ServerPlan,
		team: str | None = None,
		auto_increase_storage: bool | None = False,
	) -> tuple[Server, DatabaseServer, PressJob]:
		"""Minimal creation of a unified server with app and database on same vmi"""
		# Accepting only arguments allowed via the API to create a server.
		# Other arguments can be added laters.

		team = team or get_current_team()
		vm = self.create_vm(
			machine_type=str(plan.instance_type),
			platform=plan.platform,
			disk_size=plan.disk,
			domain=frappe.db.get_single_value("Press Settings", "domain"),
			series=self.unified_server_series,
			team=team,
		)
		server, database_server = vm.create_unified_server()

		server.title = f"{title} - Unified"
		database_server.title = f"{title} - Database"

		# Common configurations
		server.ram = database_server.ram = plan.memory
		server.auto_increase_storage = database_server.auto_increase_storage = auto_increase_storage
		server.plan = database_server.plan = plan.name

		# Server configurations
		server.new_worker_allocation = True
		server.database_server = database_server.name
		server.proxy_server = self.proxy_server

		# Database configurations
		database_server.auto_purge_binlog_based_on_size = True
		database_server.binlog_max_disk_usage_percent = 75 if auto_increase_storage else 20

		server.save()  # Creating server before database server to use the preset agent password
		database_server.save()

		# Deliberately skipping subscription creation for database server
		server.create_subscription(plan.name)

		job = server.run_press_job(
			"Create Server", arguments=None
		)  # Deliberately calling via `Server` and not `Database Server`

		# TODO: Create new press job to create unified server.
		return server, database_server, job

	def create_server(  # noqa: C901
		self,
		doctype: str,
		title: str,
		plan: ServerPlan | None = None,
		domain: str | None = None,
		team: str | None = None,
		create_subscription=True,
		auto_increase_storage: bool = False,
		data_disk_snapshot: str | None = None,
		temporary_server: bool = False,
		is_for_recovery: bool = False,
		setup_db_replication: bool = False,
		master_db_server: str | None = None,
		press_job_arguments: dict[str, typing.Any] | None = None,
		kms_key_id: str | None = None,
		is_secondary: bool = False,
		primary: str | None = None,
	) -> tuple[BaseServer | MonitorServer | LogServer, PressJob]:
		"""Creates a server for the cluster

		temporary_server: If you are creating a temporary server for some special purpose, set this to True.
			This will use a different nameing series `t` for the server to avoid conflicts
			with the regular servers.
		"""

		if press_job_arguments is None:
			press_job_arguments = {}

		if setup_db_replication:
			if doctype != "Database Server":
				frappe.throw(
					"Replication can only be set up for Database Servers",
					frappe.ValidationError,
				)
			if not master_db_server:
				frappe.throw(
					"Please provide the master database server for replication setup", frappe.ValidationError
				)
			if frappe.get_value("Database Server", master_db_server, "status") != "Active":
				frappe.throw(
					"Master Database Server is not active. Please check the status of the server before creating replication.",
					frappe.ValidationError,
				)

		domain = domain or frappe.db.get_single_value("Press Settings", "domain")
		server_series = {**self.base_servers, **self.private_servers}
		team = team or get_current_team()
		plan = plan or self.get_or_create_basic_plan(doctype)
		assert plan.instance_type is not None, "Instance type is required in the plan"
		vm = self.create_vm(
			str(plan.instance_type),
			plan.platform,
			plan.disk,
			domain,
			server_series[doctype] if not is_secondary else self.secondary_server_series,
			team,
			data_disk_snapshot=data_disk_snapshot,
			temporary_server=temporary_server,
			kms_key_id=kms_key_id,
			vmi_series="f" if is_secondary else None,  # Just use `f` series for secondary servers
		)
		server: BaseServer | MonitorServer | LogServer | None = None
		match doctype:
			case "Database Server":
				server = vm.create_database_server()
				server.ram = plan.memory
				server.title = f"{title} - Database"
				server.auto_increase_storage = auto_increase_storage
				server.is_for_recovery = is_for_recovery

				if setup_db_replication:
					server.is_primary = False
					server.primary = master_db_server

				if server.auto_increase_storage:
					server.auto_purge_binlog_based_on_size = True
					server.binlog_max_disk_usage_percent = 75
				else:
					server.auto_purge_binlog_based_on_size = True
					server.binlog_max_disk_usage_percent = 20

			case "Server":
				server = vm.create_server(is_secondary=is_secondary, primary=primary)
				server.title = f"{title} - Application" if not is_secondary else title
				server.ram = plan.memory
				if hasattr(self, "database_server") and self.database_server:
					server.database_server = self.database_server

				if not hasattr(self, "proxy_server") or not self.proxy_server:
					frappe.throw(
						"Please set the Proxy Server to Cluster record before creating the App Server",
						frappe.ValidationError,
					)
				else:
					server.proxy_server = self.proxy_server
				server.new_worker_allocation = True
				server.auto_increase_storage = auto_increase_storage
				server.is_for_recovery = is_for_recovery
			case "Proxy Server":
				server = vm.create_proxy_server()
				server.title = f"{title} - Proxy"
			case "Monitor Server":
				server = vm.create_monitor_server()
				server.title = f"{title} - Monitor"
			case "Log Server":
				server = vm.create_log_server()
				server.title = f"{title} - Log"
			case _:
				raise NotImplementedError

		if create_subscription:
			server.plan = plan.name

		server.save()

		if create_subscription:
			server.create_subscription(plan.name)

		job_arguments: dict[str, str | bool | None] = {}
		if setup_db_replication:
			job_arguments["master_db_server"] = master_db_server
			job_arguments["setup_db_replication"] = True
			job_arguments.update(press_job_arguments)
		job = server.run_press_job("Create Server", arguments=job_arguments)

		return server, job

	@classmethod
	def get_all_for_new_bench(cls, extra_filters=None) -> list[dict[str, str]]:
		if extra_filters is None:
			extra_filters = {}
		cluster_names = unique(frappe.db.get_all("Server", filters={"status": "Active"}, pluck="cluster"))
		filters = {"name": ("in", cluster_names), "public": True}
		return frappe.db.get_all(
			"Cluster",
			filters={**filters, **extra_filters},
			fields=["name", "title", "image", "beta"],
		)

	def find_server_plan_with_compute_config(
		self,
		server_type: Literal["Server", "Database Server"],
		vcpu: int,
		memory: int,
		platform: Literal["arm64", "amd64", "x86_64"] | None = None,
	) -> str | None:
		platforms = [platform] if platform else ["arm64", "amd64", "x86_64"]  # Priority of platform
		best_plan = None
		best_score = float("inf")

		for platform in platforms:
			plans = frappe.get_all(
				"Server Plan",
				filters={
					"enabled": True,
					"legacy_plan": False,
					"cluster": self.name,
					"platform": platform,
					"server_type": server_type,
					"premium": False,
				},
				fields=["name", "vcpu", "memory", "platform"],
			)

			# Skip platform if no plans available
			if not plans:
				continue

			# Find best plan for this platform
			for plan in plans:
				vcpu_diff = abs(plan.vcpu - vcpu) / max(vcpu, 1) * 100
				memory_diff = abs(plan.memory - memory) / max(memory, 1) * 100

				# Calculate weighted average difference (you can adjust weights as needed)
				total_score = (vcpu_diff * 0.4) + (memory_diff * 0.2)

				# Prefer plans that meet or exceed requirements rather than fall short
				# Add penalty if plan doesn't meet minimum requirements
				penalty = 0
				if plan.vcpu < vcpu:
					penalty += 50
				if plan.memory < memory:
					penalty += 50

				final_score = total_score + penalty

				# Update best plan if this one is better
				if final_score < best_score:
					best_score = final_score
					best_plan = plan.name

			return best_plan
		return None
