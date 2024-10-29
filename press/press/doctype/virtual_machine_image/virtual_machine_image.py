# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import boto3
import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from oci.core import ComputeClient
from oci.core.models import CreateImageDetails
from tenacity import retry, stop_after_attempt, wait_fixed
from tenacity.retry import retry_if_result


class VirtualMachineImage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.virtual_machine_image_volume.virtual_machine_image_volume import (
			VirtualMachineImageVolume,
		)

		cluster: DF.Link
		copied_from: DF.Link | None
		image_id: DF.Data | None
		instance_id: DF.Data
		mariadb_root_password: DF.Password | None
		platform: DF.Data | None
		public: DF.Check
		region: DF.Link
		series: DF.Literal["n", "f", "m", "c", "p", "e", "r"]
		size: DF.Int
		snapshot_id: DF.Data | None
		status: DF.Literal["Pending", "Available", "Unavailable"]
		virtual_machine: DF.Link
		volumes: DF.Table[VirtualMachineImageVolume]
	# end: auto-generated types

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
			volumes = self.get_volumes_from_virtual_machine()
			response = self.client.create_image(
				InstanceId=self.instance_id,
				Name=f"Frappe Cloud {self.name} - {self.virtual_machine}",
				BlockDeviceMappings=volumes,
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
			self.mariadb_root_password = frappe.get_doc("Database Server", self.virtual_machine).get_password(
				"mariadb_root_password"
			)

	@frappe.whitelist()
	def sync(self):  # noqa: C901
		cluster = frappe.get_doc("Cluster", self.cluster)
		if cluster.cloud_provider == "AWS EC2":
			images = self.client.describe_images(ImageIds=[self.image_id])["Images"]
			if images:
				image = images[0]
				self.status = self.get_aws_status_map(image["State"])
				self.platform = image["Architecture"]
				volume = find(image["BlockDeviceMappings"], lambda x: "Ebs" in x)
				# This information is not accurate for images created from multiple volumes
				if volume and "VolumeSize" in volume["Ebs"]:
					self.size = volume["Ebs"]["VolumeSize"]
				if volume and "SnapshotId" in volume["Ebs"]:
					self.snapshot_id = volume["Ebs"]["SnapshotId"]
				for volume in image["BlockDeviceMappings"]:
					if "Ebs" not in volume:
						# We don't care about non-EBS (instance store) volumes
						continue
					snapshot_id = volume["Ebs"].get("SnapshotId")
					existing = find(self.volumes, lambda x: x.snapshot_id == snapshot_id)
					device = volume["DeviceName"]
					volume_type = volume["Ebs"]["VolumeType"]
					size = volume["Ebs"]["VolumeSize"]
					if existing:
						existing.device = device
						existing.volume_type = volume_type
						existing.size = size
					else:
						self.append(
							"volumes",
							{
								"snapshot_id": snapshot_id,
								"device": device,
								"volume_type": volume_type,
								"size": size,
							},
						)
			else:
				self.status = "Unavailable"
		elif cluster.cloud_provider == "OCI":
			image = self.client.get_image(self.image_id).data
			self.status = self.get_oci_status_map(image.lifecycle_state)
			if image.size_in_mbs:
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
		cluster = frappe.get_doc("Cluster", self.cluster)
		if cluster.cloud_provider == "AWS EC2":
			self.client.deregister_image(ImageId=self.image_id)
			if self.snapshot_id:
				self.client.delete_snapshot(SnapshotId=self.snapshot_id)
		elif cluster.cloud_provider == "OCI":
			self.client.delete_image(self.image_id)
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

	def get_volumes_from_virtual_machine(self):
		machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
		volumes = []
		for volume in machine.volumes:
			volumes.append(
				{
					"DeviceName": volume.device,
					"Ebs": {
						"DeleteOnTermination": True,
						"VolumeSize": volume.size,
						"VolumeType": volume.volume_type,
					},
				}
			)
		return volumes

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
		if cluster.cloud_provider == "OCI":
			return ComputeClient(cluster.get_oci_config())
		return None

	@classmethod
	def get_available_for_series(cls, series: str, region: str | None = None) -> str | None:
		images = frappe.qb.DocType(cls.DOCTYPE)
		get_available_images = (
			frappe.qb.from_(images)
			.select("name")
			.where(images.status == "Available")
			.where(images.public == 1)
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
