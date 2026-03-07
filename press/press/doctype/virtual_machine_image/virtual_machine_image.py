# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import math

import boto3
import frappe
import pydo
from frappe.core.utils import find
from frappe.model.document import Document
from hcloud import APIException, Client
from oci.core import ComputeClient
from oci.core.models import (
	CreateImageDetails,
)
from oci.core.models.image_source_via_object_storage_uri_details import (
	ImageSourceViaObjectStorageUriDetails,
)
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

		action_id: DF.Data | None
		cloud_provider: DF.Data
		cluster: DF.Link
		copied_from: DF.Link | None
		has_data_volume: DF.Check
		image_id: DF.Data | None
		instance_id: DF.Data
		mariadb_root_password: DF.Password | None
		object_storage_uri: DF.SmallText | None
		platform: DF.Data
		public: DF.Check
		region: DF.Link
		root_size: DF.Int
		series: DF.Literal["n", "f", "m", "c", "p", "e", "r", "nfs", "fs", "u"]
		size: DF.Int
		snapshot_id: DF.Data | None
		status: DF.Literal["Pending", "Available", "Unavailable"]
		virtual_machine: DF.Link
		volumes: DF.Table[VirtualMachineImageVolume]
	# end: auto-generated types

	DOCTYPE = "Virtual Machine Image"

	def before_insert(self):
		self.set_credentials()
		if (
			self.cloud_provider == "Hetzner" or self.cloud_provider == "DigitalOcean"
		) and self.has_data_volume:
			frappe.throw("Hetzner Virtual Machine Images cannot have data volumes.")

		if self.cloud_provider == "DigitalOcean":
			snapshots = self.client.droplets.list_snapshots(self.instance_id)
			if snapshots.get("snapshots", []):
				frappe.throw(
					"A snapshot already exists, please delete the existing snapshot before creating a new image."
				)

	def after_insert(self):
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
			object_storage_details = {}
			instance_details = {}
			if self.object_storage_uri:
				object_storage_details = {
					"image_source_details": ImageSourceViaObjectStorageUriDetails(
						source_uri=self.object_storage_uri
					)
				}
			else:
				instance_details = {
					"instance_id": self.instance_id,
				}
			image = self.client.create_image(
				CreateImageDetails(
					compartment_id=cluster.oci_tenancy,
					display_name=f"Frappe Cloud {self.name} - {self.virtual_machine}",
					**instance_details,
					**object_storage_details,
				)
			).data
			self.image_id = image.id

		elif cluster.cloud_provider == "Hetzner":
			from hcloud.servers.domain import Server

			response = self.client.servers.create_image(
				server=Server(id=self.instance_id),
				description=f"Frappe Cloud VMI {self.name} - {self.virtual_machine} ",
				labels={
					"environment": "prod" if not frappe.conf.developer_mode else "local",
					"instance-id": str(self.instance_id),
					"virtual-machine": self.virtual_machine,
				},
				type="snapshot",
			)
			self.image_id = response.image.id

		elif cluster.cloud_provider == "DigitalOcean":
			action = self.client.droplet_actions.post(
				self.instance_id,
				{"type": "snapshot", "name": f"Frappe Cloud {self.name} - {self.virtual_machine}"},
			)
			action = action["action"]
			self.action_id = action["id"]

		self.sync()

	def create_image_from_copy(self):
		if self.cloud_provider == "AWS EC2":
			source = frappe.get_doc("Virtual Machine Image", self.copied_from)
			response = self.client.copy_image(
				Name=f"Frappe Cloud {self.name} - {self.virtual_machine}",
				SourceImageId=source.image_id,
				SourceRegion=source.region,
			)
			self.image_id = response["ImageId"]
			self.sync()

		elif self.cloud_provider == "DigitalOcean":
			action = self.client.image_actions.post(
				self.image_id,
				{"type": "transfer", "region": frappe.db.get_value("Cluster", self.cluster, "region")},
			)
			action = action["action"]
			self.action_id = action["id"]
			self.sync()

		else:
			raise NotImplementedError("Copying images is only supported for AWS EC2 and DigitalOcean.")

	def set_credentials(self):
		if (self.series == "m" or self.series == "u") and frappe.db.exists(
			"Database Server", self.virtual_machine
		):
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
				attached_snapshots = []
				if volume and "SnapshotId" in volume["Ebs"]:
					self.snapshot_id = volume["Ebs"]["SnapshotId"]
				for volume in image["BlockDeviceMappings"]:
					if "Ebs" not in volume:
						# We don't care about non-EBS (instance store) volumes
						continue
					snapshot_id = volume["Ebs"].get("SnapshotId")
					if not snapshot_id:
						# We don't care about volumes without snapshots
						continue
					attached_snapshots.append(snapshot_id)
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
				for volume in list(self.volumes):
					if volume.snapshot_id not in attached_snapshots:
						self.remove(volume)

				self.size = self.get_data_volume().size
				self.root_size = self.get_root_volume().size
			else:
				self.status = "Unavailable"
		elif cluster.cloud_provider == "OCI":
			image = self.client.get_image(self.image_id).data
			self.status = self.get_oci_status_map(image.lifecycle_state)
			if image.size_in_mbs:
				self.size = image.size_in_mbs // 1024
		elif cluster.cloud_provider == "Hetzner":
			try:
				image = self.client.images.get_by_id(self.image_id)
				self.status = self.get_hetzner_status_map(image.status)
				self.size = math.ceil(image.disk_size)
				self.root_size = self.size
			except APIException as e:
				if e.code == "not_found":
					self.status = "Unavailable"
				else:
					raise e
		elif cluster.cloud_provider == "DigitalOcean":
			if self.copied_from:
				action_status = self.client.image_actions.get(
					action_id=self.action_id,
					image_id=frappe.db.get_value("Virtual Machine Image", self.copied_from, "image_id"),
				)
			else:
				action_status = self.client.droplet_actions.get(
					droplet_id=self.instance_id, action_id=self.action_id
				)

			status = action_status["action"]["status"]
			self.status = self.get_digital_ocean_status_map(status)

			if self.status == "Available":
				if self.copied_from:
					images = self.client.snapshots.get(action_status["action"]["resource_id"]).get("snapshot")
				else:
					virtual_machine_status = frappe.db.get_value(
						"Virtual Machine", self.virtual_machine, "status"
					)
					if virtual_machine_status == "Terminated":
						images = self.client.snapshots.get(self.image_id).get("snapshot")
					else:
						# We need this since the image ID might not be ready immediately after creation
						images = self.client.droplets.list_snapshots(self.instance_id).get("snapshots")

				image = images[0] if isinstance(images, list) else images
				self.image_id = image["id"]
				self.size = image["min_disk_size"]
				self.root_size = image["min_disk_size"]

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
		elif cluster.cloud_provider == "Hetzner":
			from hcloud.images.domain import Image

			self.client.images.delete(Image(self.image_id))
		self.sync()

	def get_aws_status_map(self, status):
		return {
			"pending": "Pending",
			"available": "Available",
		}.get(status, "Unavailable")

	def get_hetzner_status_map(self, status):
		return {
			"creating": "Pending",
			"available": "Available",
		}.get(status, "Unavailable")

	def get_digital_ocean_status_map(self, status: str):
		return {
			"in-progress": "Pending",
			"completed": "Available",
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
		if cluster.cloud_provider == "Hetzner":
			api_token = cluster.get_password("hetzner_api_token")
			return Client(token=api_token)
		if cluster.cloud_provider == "DigitalOcean":
			return pydo.Client(token=cluster.get_password("digital_ocean_api_token"))
		return None

	@classmethod
	def get_available_for_series(
		cls,
		series: str,
		region: str | None = None,
		platform: str | None = None,
		cloud_provider: str | None = None,
	) -> str | None:
		images = frappe.qb.DocType(cls.DOCTYPE)
		get_available_images = (
			frappe.qb.from_(images)
			.select(images.name)
			.where(images.status == "Available")
			.where(images.public == 1)
			.where(
				images.series == series,
			)
			.orderby(images.creation, order=frappe.qb.desc)
		)
		if region:
			get_available_images = get_available_images.where(images.region == region)
		if platform:
			get_available_images = get_available_images.where(images.platform == platform)
		if cloud_provider:
			get_available_images = get_available_images.where(images.cloud_provider == cloud_provider)

		available_images = get_available_images.run(as_dict=True)
		if not available_images:
			return None
		return available_images[0].name

	def get_root_volume(self):
		# This only works for AWS
		if len(self.volumes) == 1:
			return self.volumes[0]

		volume = find(self.volumes, lambda v: v.device == "/dev/sda1")
		if volume:
			return volume
		return frappe._dict({"size": 0})

	def get_data_volume(self):
		if not self.has_data_volume:
			return self.get_root_volume()

		# This only works for AWS
		if len(self.volumes) == 1:
			return self.volumes[0]

		volume = find(self.volumes, lambda v: v.device != "/dev/sda1")
		if volume:
			return volume
		return frappe._dict({"size": 0})
