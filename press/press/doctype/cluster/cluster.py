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
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name}"},],
				},
			],
			CidrBlock=self.cidr_block,
		)
		self.aws_vpc_id = response["Vpc"]["VpcId"]

		response = client.create_subnet(
			TagSpecifications=[
				{
					"ResourceType": "subnet",
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - Public Subnet"},],
				},
			],
			AvailabilityZone=self.availability_zone,
			VpcId=self.aws_vpc_id,
			CidrBlock=self.subnet_cidr_block,
		)
		self.aws_subnet_id = response["Subnet"]["SubnetId"]
		self.save()
