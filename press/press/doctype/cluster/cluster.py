# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import ipaddress
import base64
import time
import re
import hashlib
from textwrap import wrap
from typing import Dict, Generator, List, Optional

import boto3
from oci.core import VirtualNetworkClient
from oci.identity import IdentityClient
from oci.config import validate_config
from oci.core.models import (
	CreateVcnDetails,
	CreateSubnetDetails,
	CreateInternetGatewayDetails,
	UpdateRouteTableDetails,
	RouteRule,
	CreateNetworkSecurityGroupDetails,
	AddNetworkSecurityGroupSecurityRulesDetails,
	AddSecurityRuleDetails,
	TcpOptions,
	PortRange,
)

import frappe
from frappe.model.document import Document
from press.press.doctype.virtual_machine_image.virtual_machine_image import (
	VirtualMachineImage,
)

from press.utils import get_current_team, unique

import typing

if typing.TYPE_CHECKING:
	from press.press.doctype.plan.plan import Plan
	from press.press.doctype.press_settings.press_settings import PressSettings
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class Cluster(Document):
	dashboard_fields = ["title", "image"]

	base_servers = {
		"Proxy Server": "n",
		"Database Server": "m",
		"Server": "f",  # App server is last as it needs both proxy and db server
	}
	private_servers = {
		# TODO: Uncomment these when they are implemented
		# "Monitor Server": "p",
		# "Log Server": "e",
	}
	wait_for_aws_creds_seconds = 20

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		if filters and filters.get("group"):
			rg = frappe.get_doc("Release Group", filters.get("group"))
			cluster_names = rg.get_clusters()
			clusters = frappe.get_all(
				"Cluster",
				fields=["name", "title", "image", "beta"],
				filters={"name": ("in", cluster_names)},
			)
			return clusters

	def validate(self):
		self.validate_monitoring_password()
		self.validate_cidr_block()
		if self.cloud_provider == "AWS EC2":
			self.validate_aws_credentials()
		elif self.cloud_provider == "OCI":
			self.set_oci_availability_zone()

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

	def on_trash(self):
		machines = frappe.get_all(
			"Virtual Machine", {"cluster": self.name, "status": "Terminated"}, pluck="name"
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
			existing_blocks = ["10.0.0.0/16"] + frappe.get_all(
				"Cluster", ["cidr_block"], pluck="cidr_block"
			)
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
		client = boto3.client(
			"ec2",
			region_name=self.region,
			aws_access_key_id=self.aws_access_key_id,
			aws_secret_access_key=self.get_password("aws_secret_access_key"),
		)

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
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Public Subnet"}],
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
						{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Internet Gateway"},
					],
				},
			],
		)

		self.internet_gateway_id = response["InternetGateway"]["InternetGatewayId"]

		client.attach_internet_gateway(
			InternetGatewayId=self.internet_gateway_id, VpcId=self.vpc_id
		)

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
						{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Security Group"},
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
						{"CidrIp": self.subnet_cidr_block, "Description": "MariaDB from private network"}
					],
					"ToPort": 3306,
				},
				{
					"FromPort": 22000,
					"IpProtocol": "tcp",
					"IpRanges": [
						{"CidrIp": self.subnet_cidr_block, "Description": "SSH from private network"}
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

		try:
			# We don't care if the key already exists in this region
			response = client.import_key_pair(
				KeyName=self.ssh_key,
				PublicKeyMaterial=frappe.db.get_value("SSH Key", self.ssh_key, "public_key"),
				TagSpecifications=[
					{"ResourceType": "key-pair", "Tags": [{"Key": "Name", "Value": self.ssh_key}]},
				],
			)
		except Exception:
			pass
		self.save()

	def create_proxy_security_group(self):
		client = boto3.client(
			"ec2",
			region_name=self.region,
			aws_access_key_id=self.aws_access_key_id,
			aws_secret_access_key=self.get_password("aws_secret_access_key"),
		)
		response = client.create_security_group(
			GroupName=f"Frappe Cloud - {self.name} - Proxy - Security Group",
			Description="Allow Everything on Proxy",
			VpcId=self.vpc_id,
			TagSpecifications=[
				{
					"ResourceType": "security-group",
					"Tags": [
						{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Proxy - Security Group"},
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
					"IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH proxy from anywhere"}],
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
			self.get_password("oci_private_key")
			.replace(" ", "\n")
			.replace("\nPRIVATE\n", " PRIVATE ")
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
		identiy_client = IdentityClient(self.get_oci_config())
		availibility_domain = (
			identiy_client.list_availability_domains(self.oci_tenancy).data[0].name
		)
		self.availability_zone = availibility_domain

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
		vcn_client.add_network_security_group_security_rules(
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

	def get_available_vmi(self, series) -> Optional[str]:
		"""Virtual Machine Image available in region for given series"""
		return VirtualMachineImage.get_available_for_series(series, self.region)

	@property
	def server_doctypes(self):
		server_doctypes = {**self.base_servers}
		if not self.public:
			server_doctypes = {**server_doctypes, **self.private_servers}
		return server_doctypes

	def get_same_region_vmis(self, get_series=False):
		return frappe.get_all(
			"Virtual Machine Image",
			filters={
				"region": self.region,
				"series": ("in", list(self.server_doctypes.values())),
				"status": "Available",
			},
			pluck="name" if not get_series else "series",
		)

	def get_other_region_vmis(self, get_series=False):
		vmis = []
		for series in list(self.server_doctypes.values()):
			vmis.extend(
				frappe.get_all(
					"Virtual Machine Image",
					["name", "series", "creation"],
					filters={
						"region": ("!=", self.region),
						"series": series,
						"status": "Available",
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
		for vmi in self.get_other_region_vmis():
			copies.append(
				frappe.get_doc(
					"Virtual Machine Image",
					vmi,
				).copy_image(self.name)
			)
			frappe.db.commit()
		for copy in copies:
			yield copy

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
				"Test",
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
				"Test",
				create_subscription=False,
			)

	def create_vm(
		self, machine_type: str, disk_size: int, domain: str, series: str, team: str
	) -> "VirtualMachine":
		return frappe.get_doc(
			{
				"doctype": "Virtual Machine",
				"cluster": self.name,
				"domain": domain,
				"series": series,
				"disk_size": disk_size,
				"machine_type": machine_type,
				"virtual_machine_image": self.get_available_vmi(series),
				"team": team,
			},
		).insert()

	def get_or_create_basic_plan(self, server_type):
		plan = frappe.db.exists("Server Plan", f"Basic Cluster - {server_type}")
		if plan:
			return frappe.get_doc("Server Plan", f"Basic Cluster - {server_type}")
		else:
			return frappe.get_doc(
				{
					"doctype": "Server Plan",
					"name": f"Basic Cluster - {server_type}",
					"title": f"Basic Cluster - {server_type}",
					"instance_type": "t2.medium",
					"price_inr": 0,
					"price_usd": 0,
					"vcpu": 2,
					"memory": 4096,
					"disk": 50,
				}
			).insert(ignore_permissions=True, ignore_if_duplicate=True)

	def create_server(
		self,
		doctype: str,
		title: str,
		plan: "Plan" = None,
		domain: str = None,
		team: str = None,
		create_subscription=True,
	):
		"""Creates a server for the cluster"""
		domain = domain or frappe.db.get_single_value("Press Settings", "domain")
		server_series = {**self.base_servers, **self.private_servers}
		team = team or get_current_team()
		plan = plan or self.get_or_create_basic_plan(doctype)
		vm = self.create_vm(
			plan.instance_type, plan.disk, domain, server_series[doctype], team
		)
		server = None
		match doctype:
			case "Database Server":
				server = vm.create_database_server()
				server.ram = plan.memory
				server.title = f"{title} - Database"
			case "Server":
				server = vm.create_server()
				server.title = f"{title} - Application"
				server.ram = plan.memory
				server.database_server = self.database_server
				server.proxy_server = self.proxy_server
				server.new_worker_allocation = True
			case "Proxy Server":
				server = vm.create_proxy_server()
				server.title = f"{title} - Proxy"
			case "Monitor Server":
				server = vm.create_monitor_server()
				server.title = f"{title} - Monitor"
			case "Log Server":
				server = vm.create_log_server()
				server.title = f"{title} - Log"

		if create_subscription:
			server.plan = plan.name
			server.save()
			server.create_subscription(plan.name)
		job = server.run_press_job("Create Server")

		return server, job

	@classmethod
	def get_all_for_new_bench(cls, extra_filters={}) -> List[Dict[str, str]]:
		cluster_names = unique(
			frappe.db.get_all("Server", filters={"status": "Active"}, pluck="cluster")
		)
		filters = {"name": ("in", cluster_names), "public": True}
		return frappe.db.get_all(
			"Cluster",
			filters={**filters, **extra_filters},
			fields=["name", "title", "image", "beta"],
		)
