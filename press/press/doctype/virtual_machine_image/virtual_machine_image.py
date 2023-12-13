# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from typing import Optional

import boto3
import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from tenacity import retry, stop_after_attempt, wait_fixed
from tenacity.retry import retry_if_result
from oci.core import ComputeClient
from oci.core.models import CreateImageDetails


class VirtualMachineImage(Document):
	DOCTYPE = "Virtual Machine Image"

	def after_insert(self):
		self.set_credentials()
		if self.copied_from:
			self.create_image_from_copy()
		else:
			self.create_image()

	def create_image(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		if cluster.cloud_provider == "AWS EC2":
			response = self.client.create_image(
				InstanceId=self.instance_id,
				Name=f"Frappe Cloud {self.name} - {self.virtual_machine}",
			)
			self.image_id = response["ImageId"]
		elif cluster.cloud_provider == "OCI":
			image = self.client.create_image(
				CreateImageDetails(
					compartment_id=cluster.oci_tenancy,
					display_name=f"Frappe Cloud {self.name} - {self.virtual_machine}",
					instance_id=self.instance_id,
				)
			).data
			self.image_id = image.id
		self.sync()

	def create_image_from_copy(self):
		source = frappe.get_doc("Virtual Machine Image", self.copied_from)
		response = self.client.copy_image(
			Name=f"Frappe Cloud {self.name} - {self.virtual_machine}",
			SourceImageId=source.image_id,
			SourceRegion=source.region,
		)
		self.image_id = response["ImageId"]
		self.sync()

	def set_credentials(self):
		if self.series == "m" and frappe.db.exists("Database Server", self.virtual_machine):
			self.mariadb_root_password = frappe.get_doc(
				"Database Server", self.virtual_machine
			).get_password("mariadb_root_password")

	@frappe.whitelist()
	def sync(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		if cluster.cloud_provider == "AWS EC2":
			images = self.client.describe_images(ImageIds=[self.image_id])["Images"]
			if images:
				image = images[0]
				self.status = self.get_aws_status_map(image["State"])
				self.platform = image["Architecture"]
				volume = find(image["BlockDeviceMappings"], lambda x: "Ebs" in x.keys())
				if volume and "VolumeSize" in volume["Ebs"]:
					self.size = volume["Ebs"]["VolumeSize"]
				if volume and "SnapshotId" in volume["Ebs"]:
					self.snapshot_id = volume["Ebs"]["SnapshotId"]
			else:
				self.status = "Unavailable"
		elif cluster.cloud_provider == "OCI":
			image = self.client.get_image(self.image_id).data
			self.status = self.get_oci_status_map(image.lifecycle_state)
			self.size = image.size_in_mbs // 1024

		self.save()
		return self.status

	@retry(
		retry=retry_if_result(lambda result: result != "Available"),
		wait=wait_fixed(60),
		stop=stop_after_attempt(10),
	)
	def wait_for_availability(self):
		"""Retries sync until the image is available"""
		return self.sync()

	@frappe.whitelist()
	def copy_image(self, cluster: str):
		image = frappe.copy_doc(self)
		image.copied_from = self.name
		image.cluster = cluster
		return image.insert()

	@frappe.whitelist()
	def delete_image(self):
		self.client.deregister_image(ImageId=self.image_id)
		if self.snapshot_id:
			self.client.delete_snapshot(SnapshotId=self.snapshot_id)
		self.sync()

	def get_aws_status_map(self, status):
		return {
			"pending": "Pending",
			"available": "Available",
		}.get(status, "Unavailable")

	def get_oci_status_map(self, status):
		return {
			"PROVISIONING": "Pending",
			"IMPORTING": "Pending",
			"AVAILABLE": "Available",
			"EXPORTING": "Pending",
			"DISABLED": "Unavailable",
			"DELETED": "Unavailable",
		}.get(status, "Unavailable")

	@property
	def client(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		if cluster.cloud_provider == "AWS EC2":
			return boto3.client(
				"ec2",
				region_name=self.region,
				aws_access_key_id=cluster.aws_access_key_id,
				aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
			)
		elif cluster.cloud_provider == "OCI":
			return ComputeClient(cluster.get_oci_config())

	@classmethod
	def get_available_for_series(
		cls, series: str, region: Optional[str] = None
	) -> Optional[str]:
		images = frappe.qb.DocType(cls.DOCTYPE)
		get_available_images = (
			frappe.qb.from_(images)
			.select("name")
			.where(images.status == "Available")
			.where(
				images.series == series,
			)
		)
		if region:
			get_available_images = get_available_images.where(images.region == region)
		available_images = get_available_images.run(as_dict=True)
		if not available_images:
			return None
		return available_images[0].name
