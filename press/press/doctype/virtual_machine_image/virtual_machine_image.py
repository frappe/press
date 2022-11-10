# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.utils import find

import boto3


class VirtualMachineImage(Document):
	def after_insert(self):
		self.create_image()

	def create_image(self):
		response = self.client.create_image(
			InstanceId=self.aws_instance_id,
			Name=f"Frappe Cloud {self.name} - {self.virtual_machine}",
		)
		self.aws_ami_id = response["ImageId"]
		self.sync()

	@frappe.whitelist()
	def sync(self):
		images = self.client.describe_images(ImageIds=[self.aws_ami_id])["Images"]
		if images:
			image = images[0]
			self.status = self.get_status_map(image["State"])
			self.platform = image["Architecture"]
			volume = find(image["BlockDeviceMappings"], lambda x: "Ebs" in x.keys())
			if volume and "VolumeSize" in volume["Ebs"]:
				self.size = volume["Ebs"]["VolumeSize"]
			if volume and "SnapshotId" in volume["Ebs"]:
				self.aws_snapshot_id = volume["Ebs"]["SnapshotId"]
		else:
			self.status = "Unavailable"
		self.save()

	def get_status_map(self, status):
		return {
			"pending": "Pending",
			"available": "Available",
		}.get(status, "Unavailable")

	@property
	def client(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		return boto3.client(
			"ec2",
			region_name=self.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)
