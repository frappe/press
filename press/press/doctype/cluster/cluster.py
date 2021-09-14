# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
import boto3
import ipaddress


class Cluster(Document):
	def validate(self):
		self.validate_monitoring_password()
		self.validate_cidr_block()

	def after_insert(self):
		self.provision()

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

	def provision(self):
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
		self.aws_vpc_id = response["Vpc"]["VpcId"]

		response = client.create_subnet(
			TagSpecifications=[
				{
					"ResourceType": "subnet",
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Public Subnet"}],
				},
			],
			AvailabilityZone=self.availability_zone,
			VpcId=self.aws_vpc_id,
			CidrBlock=self.subnet_cidr_block,
		)
		self.aws_subnet_id = response["Subnet"]["SubnetId"]

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

		self.aws_internet_gateway_id = response["InternetGateway"]["InternetGatewayId"]

		client.attach_internet_gateway(
			InternetGatewayId=self.aws_internet_gateway_id, VpcId=self.aws_vpc_id
		)

		response = client.describe_route_tables(
			Filters=[{"Name": "vpc-id", "Values": [self.aws_vpc_id]}],
		)
		self.aws_route_table_id = response["RouteTables"][0]["RouteTableId"]

		client.create_route(
			DestinationCidrBlock="0.0.0.0/0",
			GatewayId=self.aws_internet_gateway_id,
			RouteTableId=self.aws_route_table_id,
		)

		client.create_tags(
			Resources=[self.aws_route_table_id],
			Tags=[{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Route Table"}],
		)

		response = client.describe_network_acls(
			Filters=[{"Name": "vpc-id", "Values": [self.aws_vpc_id]}],
		)
		self.aws_network_acl_id = response["NetworkAcls"][0]["NetworkAclId"]
		client.create_tags(
			Resources=[self.aws_network_acl_id],
			Tags=[{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Network ACL"}],
		)

		response = client.create_security_group(
			GroupName=f"Frappe Cloud - {self.name} - Security Group",
			Description="Allow Everything",
			VpcId=self.aws_vpc_id,
			TagSpecifications=[
				{
					"ResourceType": "security-group",
					"Tags": [
						{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Security Group"},
					],
				},
			],
		)
		self.aws_security_group_id = response["GroupId"]

		client.authorize_security_group_ingress(
			GroupId=self.aws_security_group_id,
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
					"FromPort": -1,
					"IpProtocol": "icmp",
					"IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "ICMP from anywhere"}],
					"ToPort": -1,
				},
			],
		)

		try:
			# We don't care if the key already exists in this region
			response = client.import_key_pair(
				KeyName=self.ssh_key,
				PublicKeyMaterial=frappe.db.get_value("SSH Key", self.ssh_key, "public_key"),
				TagSpecifications=[
					{"ResourceType": "key-pair", "Tags": [{"Key": "Name", "Value": self.ssh_key},]},
				],
			)
		except Exception:
			pass
		self.save()
