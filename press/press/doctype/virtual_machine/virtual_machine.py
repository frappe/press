# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import base64
import ipaddress
import time

import boto3
import botocore
import frappe
import rq
from frappe.core.utils import find
from frappe.desk.utils import slug
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from hcloud import APIException, Client
from hcloud.images import Image
from hcloud.servers.domain import ServerCreatePublicNetwork
from oci.core import BlockstorageClient, ComputeClient, VirtualNetworkClient
from oci.core.models import (
	CreateBootVolumeBackupDetails,
	CreateVnicDetails,
	CreateVolumeBackupDetails,
	InstanceOptions,
	InstanceSourceViaImageDetails,
	LaunchInstanceDetails,
	LaunchInstancePlatformConfig,
	LaunchInstanceShapeConfigDetails,
	UpdateBootVolumeDetails,
	UpdateInstanceDetails,
	UpdateInstanceShapeConfigDetails,
	UpdateVolumeDetails,
)
from oci.exceptions import TransientServiceError

from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import log_error
from press.utils.jobs import has_job_timeout_exceeded

server_doctypes = [
	"Server",
	"Database Server",
	"Proxy Server",
	"Monitor Server",
	"Log Server",
]


class VirtualMachine(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.virtual_machine_temporary_volume.virtual_machine_temporary_volume import (
			VirtualMachineTemporaryVolume,
		)
		from press.press.doctype.virtual_machine_volume.virtual_machine_volume import VirtualMachineVolume

		availability_zone: DF.Data
		cloud_provider: DF.Literal["", "AWS EC2", "OCI", "Hetzner"]
		cluster: DF.Link
		disk_size: DF.Int
		domain: DF.Link
		has_data_volume: DF.Check
		index: DF.Int
		instance_id: DF.Data | None
		machine_image: DF.Data | None
		machine_type: DF.Data
		platform: DF.Literal["x86_64", "arm64"]
		private_dns_name: DF.Data | None
		private_ip_address: DF.Data | None
		public_dns_name: DF.Data | None
		public_ip_address: DF.Data | None
		ram: DF.Int
		region: DF.Link
		root_disk_size: DF.Int
		security_group_id: DF.Data | None
		series: DF.Literal["n", "f", "m", "c", "p", "e", "r"]
		skip_automated_snapshot: DF.Check
		ssh_key: DF.Link
		status: DF.Literal["Draft", "Pending", "Running", "Stopped", "Terminated"]
		subnet_cidr_block: DF.Data | None
		subnet_id: DF.Data | None
		team: DF.Link | None
		temporary_volumes: DF.Table[VirtualMachineTemporaryVolume]
		termination_protection: DF.Check
		vcpu: DF.Int
		virtual_machine_image: DF.Link | None
		volumes: DF.Table[VirtualMachineVolume]
	# end: auto-generated types

	def autoname(self):
		series = f"{self.series}-{slug(self.cluster)}.#####"
		self.index = int(make_autoname(series)[-5:])
		self.name = f"{self.series}{self.index}-{slug(self.cluster)}.{self.domain}"

	def after_insert(self):
		if self.virtual_machine_image:
			image = frappe.get_doc("Virtual Machine Image", self.virtual_machine_image)
			if image.has_data_volume:
				# We have two separate volumes for root and data
				# Copy their sizes correctly
				self.disk_size = max(self.disk_size, image.size)
				self.root_disk_size = max(self.root_disk_size, image.root_size)
			else:
				# We have only one volume. Both root and data are the same
				self.disk_size = max(self.disk_size, image.size)
				self.root_disk_size = self.disk_size
			self.machine_image = image.image_id
			self.has_data_volume = image.has_data_volume
		if not self.machine_image:
			self.machine_image = self.get_latest_ubuntu_image()
		self.save()

	def validate(self):
		if not self.private_ip_address:
			ip = ipaddress.IPv4Interface(self.subnet_cidr_block).ip
			index = self.index + 356
			if self.series == "n":
				self.private_ip_address = str(ip + index)
			else:
				offset = ["f", "m", "c", "p", "e", "r"].index(self.series)
				self.private_ip_address = str(ip + 256 * (2 * (index // 256) + offset) + (index % 256))

	def on_trash(self):
		snapshots = frappe.get_all(
			"Virtual Disk Snapshot",
			{"virtual_machine": self.name, "status": "Unavailable"},
			pluck="name",
		)
		for snapshot in snapshots:
			frappe.delete_doc("Virtual Disk Snapshot", snapshot)

		images = frappe.get_all(
			"Virtual Machine Image",
			{"virtual_machine": self.name, "status": "Unavailable"},
			pluck="name",
		)
		for image in images:
			frappe.delete_doc("Virtual Machine Image", image)

	def on_update(self):
		if self.has_value_changed("has_data_volume"):
			server = self.get_server()
			if server:
				server.has_data_volume = self.has_data_volume
				server.save()

	@frappe.whitelist()
	def provision(self):
		if self.cloud_provider == "AWS EC2":
			return self._provision_aws()
		if self.cloud_provider == "OCI":
			return self._provision_oci()
		if self.cloud_provider == "Hetzner":
			return self._provision_hetzner()
		return None

	def _provision_hetzner(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		server_type = self.client().server_types.get_by_name(self.machine_type)
		location = self.client().locations.get_by_name(cluster.region)
		network = self.client().networks.get_by_id(cluster.vpc_id)
		public_net = ServerCreatePublicNetwork(enable_ipv4=True, enable_ipv6=False)
		ssh_key_name = self.ssh_key
		ssh_key = self.client().ssh_keys.get_by_name(ssh_key_name)
		server_response = self.client().servers.create(
			name=f"{self.name}",
			server_type=server_type,
			image=Image(name="ubuntu-22.04"),
			networks=[network],
			location=location,
			public_net=public_net,
			ssh_keys=[ssh_key],
		)
		server = server_response.server
		# We assing only one private IP, so should be fine
		self.private_ip_address = server.private_net[0].ip

		self.public_ip_address = server.public_net.ipv4.ip

		self.instance_id = server.id

		self.status = self.get_hetzner_status_map()[server.status]

		self.save()

	def _provision_aws(self):
		additional_volumes = []
		if self.virtual_machine_image:
			image = frappe.get_doc("Virtual Machine Image", self.virtual_machine_image)
			if image.has_data_volume:
				volume = image.get_data_volume()
				additional_volumes.append(
					{
						"DeviceName": volume.device,
						"Ebs": {
							"DeleteOnTermination": True,
							"VolumeSize": max(self.disk_size, volume.size),
							"VolumeType": volume.volume_type,
						},
					}
				)

		for index, volume in enumerate(self.volumes, start=len(additional_volumes)):
			device_name_index = chr(ord("f") + index)
			volume_options = {
				"DeviceName": f"/dev/sd{device_name_index}",
				"Ebs": {
					"DeleteOnTermination": True,
					"VolumeSize": volume.size,
					"VolumeType": volume.volume_type,
				},
			}
			if volume.iops:
				volume_options["Ebs"]["Iops"] = volume.iops
			if volume.throughput:
				volume_options["Ebs"]["Throughput"] = volume.throughput
			additional_volumes.append(volume_options)

		options = {
			"BlockDeviceMappings": [
				*[
					{
						"DeviceName": "/dev/sda1",
						"Ebs": {
							"DeleteOnTermination": True,
							"VolumeSize": self.root_disk_size,  # This in GB. Fucking AWS!
							"VolumeType": "gp3",
						},
					}
				],
				*additional_volumes,
			],
			"ImageId": self.machine_image,
			"InstanceType": self.machine_type,
			"KeyName": self.ssh_key,
			"MaxCount": 1,
			"MinCount": 1,
			"Monitoring": {"Enabled": False},
			"Placement": {
				"AvailabilityZone": self.availability_zone,
				"Tenancy": "default",
			},
			"NetworkInterfaces": [
				{
					"AssociatePublicIpAddress": True,
					"DeleteOnTermination": True,
					"DeviceIndex": 0,
					"PrivateIpAddress": self.private_ip_address,
					"Groups": self.get_security_groups(),
					"SubnetId": self.subnet_id,
				},
			],
			"DisableApiTermination": True,
			"InstanceInitiatedShutdownBehavior": "stop",
			"TagSpecifications": [
				{
					"ResourceType": "instance",
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name}"}],
				},
			],
			"UserData": self.get_cloud_init() if self.virtual_machine_image else "",
		}
		if self.machine_type.startswith("t"):
			options["CreditSpecification"] = {"CpuCredits": "unlimited" if self.series == "n" else "standard"}
		response = self.client().run_instances(**options)

		self.instance_id = response["Instances"][0]["InstanceId"]
		self.status = self.get_aws_status_map()[response["Instances"][0]["State"]["Name"]]
		self.save()

	def _provision_oci(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		# OCI doesn't have machine types. So let's make up our own.
		# nxm = n vcpus and m GB ram
		vcpu, ram_in_gbs = map(int, self.machine_type.split("x"))
		instance = (
			self.client()
			.launch_instance(
				LaunchInstanceDetails(
					compartment_id=cluster.oci_tenancy,
					availability_domain=self.availability_zone,
					display_name=self.name,
					create_vnic_details=CreateVnicDetails(
						private_ip=self.private_ip_address,
						assign_private_dns_record=True,
						nsg_ids=self.get_security_groups(),
					),
					subnet_id=self.subnet_id,
					instance_options=InstanceOptions(are_legacy_imds_endpoints_disabled=True),
					source_details=InstanceSourceViaImageDetails(
						image_id=self.machine_image,
						boot_volume_size_in_gbs=max(self.root_disk_size, 50),
						boot_volume_vpus_per_gb=30,
					),
					shape="VM.Standard.E4.Flex",
					shape_config=LaunchInstanceShapeConfigDetails(
						ocpus=vcpu // 2, vcpus=vcpu, memory_in_gbs=ram_in_gbs
					),
					platform_config=LaunchInstancePlatformConfig(
						type="AMD_VM",
					),
					is_pv_encryption_in_transit_enabled=True,
					metadata={
						"ssh_authorized_keys": frappe.db.get_value("SSH Key", self.ssh_key, "public_key"),
						"user_data": (
							base64.b64encode(self.get_cloud_init().encode()).decode()
							if self.virtual_machine_image
							else ""
						),
					},
				)
			)
			.data
		)
		self.instance_id = instance.id
		self.status = self.get_oci_status_map()[instance.lifecycle_state]
		self.save()

	def get_cloud_init(self):
		server = self.get_server()
		if not server:
			return ""
		log_server, kibana_password = server.get_log_server()
		cloud_init_template = "press/press/doctype/virtual_machine/cloud-init.yml.jinja2"
		context = {
			"server": server,
			"machine": self.name,
			"ssh_key": frappe.db.get_value("SSH Key", self.ssh_key, "public_key"),
			"agent_password": server.get_password("agent_password"),
			"monitoring_password": server.get_monitoring_password(),
			"statsd_exporter_service": frappe.render_template(
				"press/playbooks/roles/statsd_exporter/templates/statsd_exporter.service",
				{"private_ip": self.private_ip_address},
				is_path=True,
			),
			"filebeat_config": frappe.render_template(
				"press/playbooks/roles/filebeat/templates/filebeat.yml",
				{
					"server_type": server.doctype,
					"server": self.name,
					"log_server": log_server,
					"kibana_password": kibana_password,
				},
				is_path=True,
			),
		}
		if server.doctype == "Database Server":
			mariadb_context = {
				"server_id": server.server_id,
				"private_ip": self.private_ip_address,
				"ansible_memtotal_mb": frappe.db.get_value("Server Plan", server.plan, "memory") or 1024,
				"mariadb_root_password": server.get_password("mariadb_root_password"),
			}

			context.update(
				{
					"log_requests": True,
					"mariadb_config": frappe.render_template(
						"press/playbooks/roles/mariadb/templates/mariadb.cnf",
						mariadb_context,
						is_path=True,
					),
					"mariadb_systemd_config": frappe.render_template(
						"press/playbooks/roles/mariadb_systemd_limits/templates/memory.conf",
						mariadb_context,
						is_path=True,
					),
					"mariadb_root_config": frappe.render_template(
						"press/playbooks/roles/mariadb/templates/my.cnf",
						mariadb_context,
						is_path=True,
					),
					"mariadb_exporter_config": frappe.render_template(
						"press/playbooks/roles/mysqld_exporter/templates/mysqld_exporter.service",
						mariadb_context,
						is_path=True,
					),
					"deadlock_logger_config": frappe.render_template(
						"press/playbooks/roles/deadlock_logger/templates/deadlock_logger.service",
						mariadb_context,
						is_path=True,
					),
				}
			)

		return frappe.render_template(cloud_init_template, context, is_path=True)

	def get_server(self):
		for doctype in server_doctypes:
			server = frappe.db.get_value(doctype, {"virtual_machine": self.name}, "name")
			if server:
				return frappe.get_doc(doctype, server)
		return None

	def get_hetzner_status_map(self):
		# Hetzner has not status for Terminating or Terminated. Just returns a server not found.
		return {
			"running": "Running",
			"initializing": "Pending",
			"starting": "Pending",
			"stopping": "Pending",
			"off": "Stopped",
			"deleting": "Pending",
			"migrating": "Pending",
			"rebuilding": "Pending",
			"unknown": "Pending",
		}

	def get_aws_status_map(self):
		return {
			"pending": "Pending",
			"running": "Running",
			"shutting-down": "Pending",
			"stopping": "Pending",
			"stopped": "Stopped",
			"terminated": "Terminated",
		}

	def get_oci_status_map(self):
		return {
			"MOVING": "Pending",
			"PROVISIONING": "Pending",
			"RUNNING": "Running",
			"STARTING": "Pending",
			"STOPPING": "Pending",
			"STOPPED": "Stopped",
			"CREATING_IMAGE": "Pending",
			"TERMINATING": "Pending",
			"TERMINATED": "Terminated",
		}

	def get_latest_ubuntu_image(self):
		if self.cloud_provider == "AWS EC2":
			architecture = {"x86_64": "amd64", "arm64": "arm64"}[self.platform]
			return self.client("ssm").get_parameter(
				Name=f"/aws/service/canonical/ubuntu/server/20.04/stable/current/{architecture}/hvm/ebs-gp2/ami-id"
			)["Parameter"]["Value"]
		if self.cloud_provider == "OCI":
			cluster = frappe.get_doc("Cluster", self.cluster)
			client = ComputeClient(cluster.get_oci_config())
			images = client.list_images(
				compartment_id=cluster.oci_tenancy,
				operating_system="Canonical Ubuntu",
				operating_system_version="20.04",
				shape="VM.Standard3.Flex",
				lifecycle_state="AVAILABLE",
			).data
			return images[0].id
		return None

	@frappe.whitelist()
	def reboot(self):
		if self.cloud_provider == "AWS EC2":
			self.client().reboot_instances(InstanceIds=[self.instance_id])
		elif self.cloud_provider == "OCI":
			self.client().instance_action(instance_id=self.instance_id, action="RESET")
		self.sync()

	@frappe.whitelist()
	def increase_disk_size(self, volume_id=None, increment=50):
		if not increment:
			return
		if not volume_id:
			volume_id = self.volumes[0].volume_id

		volume = find(self.volumes, lambda v: v.volume_id == volume_id)
		volume.size += int(increment)
		self.disk_size = self.get_data_volume().size
		self.root_disk_size = self.get_root_volume().size
		volume.last_updated_at = frappe.utils.now_datetime()
		if self.cloud_provider == "AWS EC2":
			self.client().modify_volume(VolumeId=volume.volume_id, Size=volume.size)
		elif self.cloud_provider == "OCI":
			if ".bootvolume." in volume.volume_id:
				self.client(BlockstorageClient).update_boot_volume(
					boot_volume_id=volume.volume_id,
					update_boot_volume_details=UpdateBootVolumeDetails(size_in_gbs=volume.size),
				)
			else:
				self.client(BlockstorageClient).update_volume(
					volume_id=volume.volume_id,
					update_volume_details=UpdateVolumeDetails(size_in_gbs=volume.size),
				)
		self.save()

	def get_volumes(self):
		if self.cloud_provider == "AWS EC2":
			response = self.client().describe_volumes(
				Filters=[{"Name": "attachment.instance-id", "Values": [self.instance_id]}]
			)
			return response["Volumes"]
		if self.cloud_provider == "OCI":
			cluster = frappe.get_doc("Cluster", self.cluster)
			return (
				self.client()
				.list_boot_volume_attachments(
					compartment_id=cluster.oci_tenancy,
					availability_domain=self.availability_zone,
					instance_id=self.instance_id,
				)
				.data
				+ self.client()
				.list_volume_attachments(
					compartment_id=cluster.oci_tenancy,
					instance_id=self.instance_id,
				)
				.data
			)
		return None

	def convert_to_gp3(self):
		for volume in self.volumes:
			if volume.volume_type != "gp3":
				volume.volume_type = "gp3"
				volume.iops = max(3000, volume.iops)
				volume.throughput = 250 if volume.size > 340 else 125
				self.client().modify_volume(
					VolumeId=volume.volume_id,
					VolumeType=volume.volume_type,
					Iops=volume.iops,
					Throughput=volume.throughput,
				)
				self.save()

	@frappe.whitelist()
	def sync(self, *args, **kwargs):
		try:
			frappe.db.get_value(self.doctype, self.name, "status", for_update=True)
		except frappe.QueryTimeoutError:  # lock wait timeout
			return None
		if self.cloud_provider == "AWS EC2":
			return self._sync_aws(*args, **kwargs)
		if self.cloud_provider == "OCI":
			return self._sync_oci(*args, **kwargs)
		if self.cloud_provider == "Hetzner":
			return self._sync_hetzner(*args, **kwargs)
		return None

	def _sync_hetzner(self, server_instance=None):
		is_deleted = False
		if not server_instance:
			try:
				server_instance = self.client().servers.get_by_id(self.instance_id)
			except APIException:
				is_deleted = True
		if server_instance and not is_deleted:
			# cluster: Document = frappe.get_doc("Cluster", self.cluster)
			self.status = self.get_hetzner_status_map()[server_instance.status]
			self.machine_type = server_instance.server_type.name
			self.private_ip_address = server_instance.private_net[0].ip
			self.public_ip_address = server_instance.public_net.ipv4.ip
		else:
			self.status = "Terminated"
		self.save()

	def _sync_oci(self, instance=None):  # noqa: C901
		if not instance:
			instance = self.client().get_instance(instance_id=self.instance_id).data
		if instance and instance.lifecycle_state != "TERMINATED":
			cluster = frappe.get_doc("Cluster", self.cluster)

			self.status = self.get_oci_status_map()[instance.lifecycle_state]

			self.ram = instance.shape_config.memory_in_gbs * 1024
			self.vcpu = instance.shape_config.vcpus
			self.machine_type = f"{int(self.vcpu)}x{int(instance.shape_config.memory_in_gbs)}"

			for vnic_attachment in (
				self.client()
				.list_vnic_attachments(compartment_id=cluster.oci_tenancy, instance_id=self.instance_id)
				.data
			):
				try:
					vnic = self.client(VirtualNetworkClient).get_vnic(vnic_id=vnic_attachment.vnic_id).data
					self.public_ip_address = vnic.public_ip
				except Exception:
					log_error(
						title="OCI VNIC Fetch Error",
						virtual_machine=self.name,
						vnic_attachment=vnic_attachment,
					)

			available_volumes = []
			for volume in self.get_volumes():
				try:
					if hasattr(volume, "volume_id"):
						volume = self.client(BlockstorageClient).get_volume(volume_id=volume.volume_id).data
					else:
						volume = (
							self.client(BlockstorageClient)
							.get_boot_volume(boot_volume_id=volume.boot_volume_id)
							.data
						)
					existing_volume = find(self.volumes, lambda v: v.volume_id == volume.id)
					if existing_volume:
						row = existing_volume
					else:
						row = frappe._dict()
					row.volume_id = volume.id
					row.size = volume.size_in_gbs

					vpus = volume.vpus_per_gb
					# Reference: https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/blockvolumeperformance.htm
					row.iops = min(1.5 * vpus + 45, 2500 * vpus) * row.size
					row.throughput = min(12 * vpus + 360, 20 * vpus + 280) * row.size // 1000

					if row.volume_id:
						available_volumes.append(row.volume_id)

					if not existing_volume and row.volume_id:
						self.append("volumes", row)
				except Exception:
					log_error(
						title="OCI Volume Fetch Error",
						virtual_machine=self.name,
						volume=volume,
					)
			if self.volumes:
				self.disk_size = self.get_data_volume().size
				self.root_disk_size = self.get_root_volume().size

			for volume in list(self.volumes):
				if volume.volume_id not in available_volumes:
					self.remove(volume)

		else:
			self.status = "Terminated"
		self.save()
		self.update_servers()

	def _sync_aws(self, response=None):  # noqa: C901
		if not response:
			try:
				response = self.client().describe_instances(InstanceIds=[self.instance_id])
			except botocore.exceptions.ClientError as e:
				if e.response.get("Error", {}).get("Code") == "InvalidInstanceID.NotFound":
					response = {"Reservations": []}
		if response["Reservations"]:
			instance = response["Reservations"][0]["Instances"][0]

			self.status = self.get_aws_status_map()[instance["State"]["Name"]]
			self.machine_type = instance.get("InstanceType")

			self.public_ip_address = instance.get("PublicIpAddress")
			self.private_ip_address = instance.get("PrivateIpAddress")

			self.public_dns_name = instance.get("PublicDnsName")
			self.private_dns_name = instance.get("PrivateDnsName")
			self.platform = instance.get("Architecture", "x86_64")

			attached_volumes = []
			attached_devices = []
			for volume_index, volume in enumerate(self.get_volumes(), start=1):  # idx starts from 1
				existing_volume = find(self.volumes, lambda v: v.volume_id == volume["VolumeId"])
				if existing_volume:
					row = existing_volume
				else:
					row = frappe._dict()
				row.volume_id = volume["VolumeId"]
				attached_volumes.append(row.volume_id)
				row.volume_type = volume["VolumeType"]
				row.size = volume["Size"]
				row.iops = volume["Iops"]
				row.device = volume["Attachments"][0]["Device"]
				attached_devices.append(row.device)

				if "Throughput" in volume:
					row.throughput = volume["Throughput"]

				row.idx = volume_index
				if not existing_volume:
					self.append("volumes", row)

			self.disk_size = self.get_data_volume().size
			self.root_disk_size = self.get_root_volume().size

			for volume in list(self.volumes):
				if volume.volume_id not in attached_volumes:
					self.remove(volume)

			for volume in list(self.temporary_volumes):
				if volume.device not in attached_devices:
					self.remove(volume)

			self.termination_protection = self.client().describe_instance_attribute(
				InstanceId=self.instance_id, Attribute="disableApiTermination"
			)["DisableApiTermination"]["Value"]

			instance_type_response = self.client().describe_instance_types(InstanceTypes=[self.machine_type])
			self.ram = instance_type_response["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"]
			self.vcpu = instance_type_response["InstanceTypes"][0]["VCpuInfo"]["DefaultVCpus"]
		else:
			self.status = "Terminated"
		self.save()
		self.update_servers()

	def get_root_volume(self):
		if len(self.volumes) == 1:
			return self.volumes[0]

		ROOT_VOLUME_FILTERS = {
			"AWS EC2": lambda v: v.device == "/dev/sda1",
			"OCI": lambda v: ".bootvolume." in v.volume_id,
		}
		root_volume_filter = ROOT_VOLUME_FILTERS.get(self.cloud_provider)
		volume = find(self.volumes, root_volume_filter)
		if volume:  # Un-provisioned machines might not have any volumes
			return volume
		return frappe._dict({"size": 0})

	def get_data_volume(self):
		if not self.has_data_volume:
			return self.get_root_volume()

		if len(self.volumes) == 1:
			return self.volumes[0]

		temporary_volume_devices = [x.device for x in self.temporary_volumes]

		DATA_VOLUME_FILTERS = {
			"AWS EC2": lambda v: v.device != "/dev/sda1" and v.device not in temporary_volume_devices,
			"OCI": lambda v: ".bootvolume." not in v.volume_id and v.device not in temporary_volume_devices,
		}
		data_volume_filter = DATA_VOLUME_FILTERS.get(self.cloud_provider)
		volume = find(self.volumes, data_volume_filter)
		if volume:  # Un-provisioned machines might not have any volumes
			return volume
		return frappe._dict({"size": 0})

	def update_servers(self):
		status_map = {
			"Pending": "Pending",
			"Running": "Active",
			"Terminated": "Archived",
			"Stopped": "Pending",
		}
		for doctype in server_doctypes:
			server = frappe.get_all(doctype, {"virtual_machine": self.name}, pluck="name")
			if server:
				server = server[0]
				frappe.db.set_value(doctype, server, "ip", self.public_ip_address)
				if doctype in ["Server", "Database Server"]:
					frappe.db.set_value(doctype, server, "ram", self.ram)
				if self.public_ip_address and self.has_value_changed("public_ip_address"):
					frappe.get_doc(doctype, server).create_dns_record()
				frappe.db.set_value(doctype, server, "status", status_map[self.status])

	def update_name_tag(self, name):
		if self.cloud_provider == "AWS EC2":
			self.client().create_tags(
				Resources=[self.instance_id],
				Tags=[
					{"Key": "Name", "Value": name},
				],
			)

	@frappe.whitelist()
	def create_image(self, public=True):
		image = frappe.get_doc(
			{
				"doctype": "Virtual Machine Image",
				"virtual_machine": self.name,
				"public": public,
				"has_data_volume": self.has_data_volume,
			}
		).insert()
		return image.name

	@frappe.whitelist()
	def create_snapshots(self, exclude_boot_volume=False, physical_backup=False, rolling_snapshot=False):
		"""
		exclude_boot_volume is applicable only for Servers with data volume
		"""
		if not self.has_data_volume:
			exclude_boot_volume = False

		# Store the newly created snapshots reference in the flags
		# So that, we can get the correct reference of snapshots created in current session
		self.flags.created_snapshots = []
		if self.cloud_provider == "AWS EC2":
			self._create_snapshots_aws(exclude_boot_volume, physical_backup, rolling_snapshot)
		elif self.cloud_provider == "OCI":
			self._create_snapshots_oci(exclude_boot_volume)

	def _create_snapshots_aws(self, exclude_boot_volume: bool, physical_backup: bool, rolling_snapshot: bool):
		temporary_volume_ids = self.get_temporary_volume_ids()
		instance_specification = {"InstanceId": self.instance_id, "ExcludeBootVolume": exclude_boot_volume}
		if temporary_volume_ids:
			instance_specification["ExcludeDataVolumeIds"] = temporary_volume_ids

		response = self.client().create_snapshots(
			InstanceSpecification=instance_specification,
			Description=f"Frappe Cloud - {self.name} - {frappe.utils.now()}",
			TagSpecifications=[
				{
					"ResourceType": "snapshot",
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - {frappe.utils.now()}"}],
				},
			],
		)
		for snapshot in response.get("Snapshots", []):
			try:
				doc = frappe.get_doc(
					{
						"doctype": "Virtual Disk Snapshot",
						"virtual_machine": self.name,
						"snapshot_id": snapshot["SnapshotId"],
						"physical_backup": physical_backup,
						"rolling_snapshot": rolling_snapshot,
					}
				).insert()
				self.flags.created_snapshots.append(doc.name)
			except Exception:
				log_error(title="Virtual Disk Snapshot Error", virtual_machine=self.name, snapshot=snapshot)

	def _create_snapshots_oci(self, exclude_boot_volume: bool):
		for volume in self.volumes:
			try:
				if ".bootvolume." in volume.volume_id:
					if exclude_boot_volume:
						continue
					snapshot = (
						self.client(BlockstorageClient)
						.create_boot_volume_backup(
							CreateBootVolumeBackupDetails(
								boot_volume_id=volume.volume_id,
								type="INCREMENTAL",
								display_name=f"Frappe Cloud - {self.name} - {volume.name} - {frappe.utils.now()}",
							)
						)
						.data
					)
				else:
					snapshot = (
						self.client(BlockstorageClient)
						.create_volume_backup(
							CreateVolumeBackupDetails(
								volume_id=volume.volume_id,
								type="INCREMENTAL",
								display_name=f"Frappe Cloud - {self.name} - {volume.name} - {frappe.utils.now()}",
							)
						)
						.data
					)
				doc = frappe.get_doc(
					{
						"doctype": "Virtual Disk Snapshot",
						"virtual_machine": self.name,
						"snapshot_id": snapshot.id,
					}
				).insert()
				self.flags.created_snapshots.append(doc.name)
			except TransientServiceError:
				# We've hit OCI rate limit for creating snapshots
				# Let's try again later
				pass
			except Exception:
				log_error(title="Virtual Disk Snapshot Error", virtual_machine=self.name, snapshot=snapshot)

	def get_temporary_volume_ids(self) -> list[str]:
		tmp_volume_ids = set()
		tmp_volumes_devices = [x.device for x in self.temporary_volumes]

		def get_volume_id_by_device(device):
			for volume in self.volumes:
				if volume.device == device:
					return volume.volume_id
			return None

		for device in tmp_volumes_devices:
			volume_id = get_volume_id_by_device(device)
			if volume_id:
				tmp_volume_ids.add(volume_id)
		return list(tmp_volume_ids)

	@frappe.whitelist()
	def disable_termination_protection(self):
		if self.cloud_provider == "AWS EC2":
			self.client().modify_instance_attribute(
				InstanceId=self.instance_id, DisableApiTermination={"Value": False}
			)
			self.sync()

	@frappe.whitelist()
	def enable_termination_protection(self):
		if self.cloud_provider == "AWS EC2":
			self.client().modify_instance_attribute(
				InstanceId=self.instance_id, DisableApiTermination={"Value": True}
			)
			self.sync()

	@frappe.whitelist()
	def start(self):
		if self.cloud_provider == "AWS EC2":
			self.client().start_instances(InstanceIds=[self.instance_id])
		elif self.cloud_provider == "OCI":
			self.client().instance_action(instance_id=self.instance_id, action="START")
		self.sync()

	@frappe.whitelist()
	def stop(self, force=False):
		if self.cloud_provider == "AWS EC2":
			self.client().stop_instances(InstanceIds=[self.instance_id], Force=bool(force))
		elif self.cloud_provider == "OCI":
			self.client().instance_action(instance_id=self.instance_id, action="STOP")
		self.sync()

	@frappe.whitelist()
	def force_stop(self):
		self.stop(force=True)

	@frappe.whitelist()
	def force_terminate(self):
		if not frappe.conf.developer_mode:
			return
		if self.cloud_provider == "AWS EC2":
			self.client().modify_instance_attribute(
				InstanceId=self.instance_id, DisableApiTermination={"Value": False}
			)
			self.client().terminate_instances(InstanceIds=[self.instance_id])

	@frappe.whitelist()
	def terminate(self):
		if self.cloud_provider == "AWS EC2":
			self.client().terminate_instances(InstanceIds=[self.instance_id])
		elif self.cloud_provider == "OCI":
			self.client().terminate_instance(instance_id=self.instance_id)

	@frappe.whitelist()
	def resize(self, machine_type):
		if self.cloud_provider == "AWS EC2":
			self.client().modify_instance_attribute(
				InstanceId=self.instance_id,
				InstanceType={"Value": machine_type},
			)
		elif self.cloud_provider == "OCI":
			vcpu, ram_in_gbs = map(int, machine_type.split("x"))
			self.client().update_instance(
				self.instance_id,
				UpdateInstanceDetails(
					shape_config=UpdateInstanceShapeConfigDetails(
						ocpus=vcpu // 2, vcpus=vcpu, memory_in_gbs=ram_in_gbs
					)
				),
			)
		self.machine_type = machine_type
		self.save()

	@frappe.whitelist()
	def get_ebs_performance(self):
		if self.cloud_provider == "AWS EC2":
			volume = self.volumes[0]
			return volume.iops, volume.throughput
		return None

	@frappe.whitelist()
	def update_ebs_performance(self, volume_id, iops, throughput):
		if self.cloud_provider == "AWS EC2":
			volume = find(self.volumes, lambda v: v.volume_id == volume_id)
			new_iops = int(iops) or volume.iops
			new_throughput = int(throughput) or volume.throughput
			self.client().modify_volume(
				VolumeId=volume.volume_id,
				Iops=new_iops,
				Throughput=new_throughput,
			)
		self.sync()

	@frappe.whitelist()
	def get_oci_volume_performance(self):
		if self.cloud_provider == "OCI":
			volume = self.volumes[0]
			return ((volume.iops / volume.size) - 45) / 1.5
		return None

	@frappe.whitelist()
	def update_oci_volume_performance(self, vpus):
		if self.cloud_provider == "OCI":
			volume = self.volumes[0]
			if ".bootvolume." in volume.volume_id:
				self.client(BlockstorageClient).update_boot_volume(
					boot_volume_id=volume.volume_id,
					update_boot_volume_details=UpdateBootVolumeDetails(vpus_per_gb=int(vpus)),
				)
			else:
				self.client(BlockstorageClient).update_volume(
					volume_id=volume.volume_id,
					update_volume_details=UpdateVolumeDetails(vpus_per_gb=int(vpus)),
				)
		self.sync()

	def client(self, client_type=None):
		cluster = frappe.get_doc("Cluster", self.cluster)
		if self.cloud_provider == "AWS EC2":
			return boto3.client(
				client_type or "ec2",
				region_name=self.region,
				aws_access_key_id=cluster.aws_access_key_id,
				aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
			)
		if self.cloud_provider == "OCI":
			return (client_type or ComputeClient)(cluster.get_oci_config())
		if self.cloud_provider == "Hetzner":
			settings = frappe.get_single("Press Settings")
			api_token = settings.get_password("hetzner_api_token")
			return Client(token=api_token)

		return None

	@frappe.whitelist()
	def create_server(self):
		document = {
			"doctype": "Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"team": self.team,
		}

		if self.virtual_machine_image:
			document["is_server_prepared"] = True
			document["is_server_setup"] = True
			document["is_server_renamed"] = True
			document["is_upstream_setup"] = True

		return frappe.get_doc(document).insert()

	@frappe.whitelist()
	def create_database_server(self):
		document = {
			"doctype": "Database Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"server_id": self.index,
			"is_primary": True,
			"team": self.team,
		}

		if self.virtual_machine_image:
			document["is_server_prepared"] = True
			document["is_server_setup"] = True
			document["is_server_renamed"] = True
			document["mariadb_root_password"] = frappe.get_doc(
				"Virtual Machine Image", self.virtual_machine_image
			).get_password("mariadb_root_password")

		return frappe.get_doc(document).insert()

	@frappe.whitelist()
	def create_proxy_server(self):
		document = {
			"doctype": "Proxy Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"team": self.team,
		}
		if self.virtual_machine_image:
			document["is_server_setup"] = True

		return frappe.get_doc(document).insert()

	@frappe.whitelist()
	def create_monitor_server(self):
		document = {
			"doctype": "Monitor Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"team": self.team,
		}
		if self.virtual_machine_image:
			document["is_server_setup"] = True

		return frappe.get_doc(document).insert()

	@frappe.whitelist()
	def create_log_server(self):
		document = {
			"doctype": "Log Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"team": self.team,
		}
		if self.virtual_machine_image:
			document["is_server_setup"] = True

		return frappe.get_doc(document).insert()

	@frappe.whitelist()
	def create_registry_server(self):
		document = {
			"doctype": "Registry Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": "AWS EC2",
			"virtual_machine": self.name,
			"team": self.team,
		}
		if self.virtual_machine_image:
			document["is_server_setup"] = True

		return frappe.get_doc(document).insert()

	def get_security_groups(self):
		groups = [self.security_group_id]
		if self.series == "n":
			groups.append(frappe.db.get_value("Cluster", self.cluster, "proxy_security_group_id"))
		return groups

	@frappe.whitelist()
	def get_serial_console_credentials(self):
		client = self.client("ec2-instance-connect")
		client.send_serial_console_ssh_public_key(
			InstanceId=self.instance_id,
			SSHPublicKey=frappe.db.get_value("SSH Key", self.ssh_key, "public_key"),
		)
		serial_console_endpoint = AWS_SERIAL_CONSOLE_ENDPOINT_MAP[self.region]
		username = f"{self.instance_id}.port0"
		host = serial_console_endpoint["endpoint"]
		return {
			"username": username,
			"host": host,
			"fingerprint": serial_console_endpoint["fingerprint"],
			"command": f"ssh {username}@{host}",
		}

	@frappe.whitelist()
	def reboot_with_serial_console(self):
		if self.cloud_provider == "AWS EC2":
			self.get_server().reboot_with_serial_console()
		self.sync()

	@classmethod
	def bulk_sync_aws(cls):
		for cluster in frappe.get_all(
			"Virtual Machine",
			["cluster", "cloud_provider", "max(`index`) as max_index"],
			{
				"status": ("not in", ("Terminated", "Draft")),
				"cloud_provider": "AWS EC2",
			},
			group_by="cluster",
		):
			CHUNK_SIZE = 25  # Each call will pick up ~50 machines (2 x CHUNK_SIZE)
			# Generate closed bounds for 25 indexes at a time
			# (1, 25), (26, 50), (51, 75), ...
			# We might have uneven chunks because of missing indexes
			chunks = [(ii, ii + CHUNK_SIZE - 1) for ii in range(1, cluster.max_index, CHUNK_SIZE)]
			for start, end in chunks:
				# Pick a random machine
				# TODO: This probably should be a method on the Cluster
				machines = cls._get_active_machines_within_chunk_range(
					cluster.cloud_provider, cluster.cluster, start, end
				)
				if not machines:
					# There might not be any running machines in the chunk range
					continue

				frappe.enqueue_doc(
					"Virtual Machine",
					machines[0].name,
					method="bulk_sync_aws_cluster",
					start=start,
					end=end,
					queue="sync",
					job_id=f"bulk_sync_aws:{cluster.cluster}:{start}-{end}",
					deduplicate=True,
				)

	def bulk_sync_aws_cluster(self, start, end):
		client = self.client()
		machines = self.__class__._get_active_machines_within_chunk_range(
			self.cloud_provider, self.cluster, start, end
		)
		instance_ids = [machine.instance_id for machine in machines]
		response = client.describe_instances(Filters=[{"Name": "instance-id", "Values": instance_ids}])
		for reservation in response["Reservations"]:
			for instance in reservation["Instances"]:
				machine: VirtualMachine = frappe.get_doc(
					"Virtual Machine", {"instance_id": instance["InstanceId"]}
				)
				try:
					machine.sync({"Reservations": [{"Instances": [instance]}]})
					frappe.db.commit()  # release lock
				except Exception:
					log_error("Virtual Machine Sync Error", virtual_machine=machine.name)
					frappe.db.rollback()

	@classmethod
	def _get_active_machines_within_chunk_range(cls, provider, cluster, start, end):
		return frappe.get_all(
			"Virtual Machine",
			fields=["name", "instance_id"],
			filters=[
				["status", "not in", ("Terminated", "Draft")],
				["cloud_provider", "=", provider],
				["cluster", "=", cluster],
				["instance_id", "is", "set"],
				["index", ">=", start],
				["index", "<=", end],
			],
		)

	@classmethod
	def bulk_sync_oci(cls):
		for cluster in frappe.get_all(
			"Virtual Machine",
			["cluster", "cloud_provider", "max(`index`) as max_index"],
			{
				"status": ("not in", ("Terminated", "Draft")),
				"cloud_provider": "OCI",
			},
			group_by="cluster",
		):
			CHUNK_SIZE = 15  # Each call will pick up ~30 machines (2 x CHUNK_SIZE)
			# Generate closed bounds for 15 indexes at a time
			# (1, 15), (16, 30), (31, 45), ...
			# We might have uneven chunks because of missing indexes
			chunks = [(ii, ii + CHUNK_SIZE - 1) for ii in range(1, cluster.max_index, CHUNK_SIZE)]
			for start, end in chunks:
				# Pick a random machine
				# TODO: This probably should be a method on the Cluster
				machines = cls._get_active_machines_within_chunk_range(
					cluster.cloud_provider, cluster.cluster, start, end
				)
				if not machines:
					# There might not be any running machines in the chunk range
					continue

				frappe.enqueue_doc(
					"Virtual Machine",
					machines[0].name,
					method="bulk_sync_oci_cluster",
					start=start,
					end=end,
					queue="sync",
					job_id=f"bulk_sync_oci:{cluster.cluster}:{start}-{end}",
					deduplicate=True,
				)

	def bulk_sync_oci_cluster(self, start, end):
		cluster = frappe.get_doc("Cluster", self.cluster)
		machines = self.__class__._get_active_machines_within_chunk_range(
			self.cloud_provider, self.cluster, start, end
		)
		instance_ids = set([machine.instance_id for machine in machines])
		response = self.client().list_instances(compartment_id=cluster.oci_tenancy).data
		for instance in response:
			if instance.id not in instance_ids:
				continue
			machine: VirtualMachine = frappe.get_doc("Virtual Machine", {"instance_id": instance.id})
			if has_job_timeout_exceeded():
				return
			try:
				machine.sync(instance)
				frappe.db.commit()  # release lock
			except rq.timeouts.JobTimeoutException:
				return
			except Exception:
				log_error("Virtual Machine Sync Error", virtual_machine=machine.name)
				frappe.db.rollback()

	def disable_delete_on_termination_for_all_volumes(self):
		attached_volumes = self.client().describe_instance_attribute(
			InstanceId=self.instance_id, Attribute="blockDeviceMapping"
		)

		modified_volumes = []
		for volume in attached_volumes["BlockDeviceMappings"]:
			volume["Ebs"]["DeleteOnTermination"] = False
			volume["Ebs"].pop("AttachTime", None)
			volume["Ebs"].pop("Status", None)
			modified_volumes.append(volume)

		self.client().modify_instance_attribute(
			InstanceId=self.instance_id, BlockDeviceMappings=modified_volumes
		)

	@frappe.whitelist()
	def convert_to_arm(self, virtual_machine_image, machine_type):
		return frappe.new_doc(
			"Virtual Machine Migration",
			virtual_machine=self.name,
			virtual_machine_image=virtual_machine_image,
			machine_type=machine_type,
		).insert()

	@frappe.whitelist()
	def attach_new_volume(self, size, iops=None, throughput=None):
		if self.cloud_provider != "AWS EC2":
			return None
		volume_options = {
			"AvailabilityZone": self.availability_zone,
			"Size": size,
			"VolumeType": "gp3",
			"TagSpecifications": [
				{
					"ResourceType": "volume",
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name}"}],
				},
			],
		}
		if iops:
			volume_options["Iops"] = iops
		if throughput:
			volume_options["Throughput"] = throughput
		volume_id = self.client().create_volume(**volume_options)["VolumeId"]
		self.wait_for_volume_to_be_available(volume_id)
		self.attach_volume(volume_id)
		return volume_id

	def wait_for_volume_to_be_available(self, volume_id):
		# AWS EC2 specific
		while self.get_state_of_volume(volume_id) != "available":
			time.sleep(1)

	def get_state_of_volume(self, volume_id):
		if self.cloud_provider != "AWS EC2":
			raise NotImplementedError
		try:
			# AWS EC2 specific
			# https://docs.aws.amazon.com/ebs/latest/userguide/ebs-describing-volumes.html
			return self.client().describe_volumes(VolumeIds=[volume_id])["Volumes"][0]["State"]
		except botocore.exceptions.ClientError as e:
			if e.response.get("Error", {}).get("Code") == "InvalidVolume.NotFound":
				return "deleted"

	def get_volume_modifications(self, volume_id):
		if self.cloud_provider != "AWS EC2":
			raise NotImplementedError

		# AWS EC2 specific https://docs.aws.amazon.com/ebs/latest/userguide/monitoring-volume-modifications.html

		try:
			return self.client().describe_volumes_modifications(VolumeIds=[volume_id])[
				"VolumesModifications"
			][0]
		except botocore.exceptions.ClientError as e:
			if e.response.get("Error", {}).get("Code") == "InvalidVolumeModification.NotFound":
				return None

	def attach_volume(self, volume_id, is_temporary_volume: bool = False) -> str:
		"""
		temporary_volumes: If you are attaching a volume to an instance just for temporary use, then set this to True.

		Then, snapshot and other stuff will be ignored for this volume.
		"""
		if self.cloud_provider != "AWS EC2":
			raise NotImplementedError
		# Attach a volume to the instance and return the device name
		device_name = self.get_next_volume_device_name()
		self.client().attach_volume(
			Device=device_name,
			InstanceId=self.instance_id,
			VolumeId=volume_id,
		)
		if is_temporary_volume:
			# add the volume to the list of temporary volumes
			self.append("temporary_volumes", {"device": device_name})
		self.save()
		# sync
		self.sync()
		return device_name

	def get_next_volume_device_name(self):
		# Hold the lock, so that we dont allocate same device name to multiple volumes
		frappe.db.get_value(self.doctype, self.name, "status", for_update=True)
		# First volume starts from /dev/sdf
		used_devices = {v.device for v in self.volumes} | {v.device for v in self.temporary_volumes}
		for i in range(5, 26):  # 'f' to 'z'
			device_name = f"/dev/sd{chr(ord('a') + i)}"
			if device_name not in used_devices:
				return device_name
		frappe.throw("No device name available for new volume")
		return None

	@frappe.whitelist()
	def detach(self, volume_id):
		volume = find(self.volumes, lambda v: v.volume_id == volume_id)
		if not volume:
			return False
		self.client().detach_volume(
			Device=volume.device, InstanceId=self.instance_id, VolumeId=volume.volume_id
		)
		self.sync()
		return True

	@frappe.whitelist()
	def delete_volume(self, volume_id):
		if self.detach(volume_id):
			self.wait_for_volume_to_be_available(volume_id)
			self.client().delete_volume(VolumeId=volume_id)
			self.sync()


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Virtual Machine")


@frappe.whitelist()
def sync_virtual_machines():
	VirtualMachine.bulk_sync_aws()
	VirtualMachine.bulk_sync_oci()


def snapshot_virtual_machines():
	machines = frappe.get_all("Virtual Machine", {"status": "Running", "skip_automated_snapshot": 0})
	for machine in machines:
		# Skip if a snapshot has already been created today
		if frappe.get_all(
			"Virtual Disk Snapshot",
			{
				"virtual_machine": machine.name,
				"physical_backup": 0,
				"rolling_snapshot": 0,
				"creation": (">=", frappe.utils.today()),
			},
			limit=1,
		):
			continue
		try:
			frappe.get_doc("Virtual Machine", machine.name).create_snapshots()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Virtual Machine Snapshot Error", virtual_machine=machine.name)


def rolling_snapshot_database_server_virtual_machines():
	# For now, let's keep it specific to database servers having physical backup enabled
	virtual_machines = frappe.get_all(
		"Database Server",
		filters={
			"status": "Active",
			"enable_physical_backup": 1,
		},
		pluck="name",
	)

	# Find out virtual machines with snapshot explicitly skipped
	ignorable_virtual_machines = set(
		frappe.get_all("Virtual Machine", {"skip_automated_snapshot": 1}, pluck="name")
	)

	start_time = time.time()
	for virtual_machine_name in virtual_machines:
		if has_job_timeout_exceeded():
			return

		# Don't spend more than 10 minutes in snapshotting
		if time.time() - start_time > 900:
			break

		if virtual_machine_name in ignorable_virtual_machines:
			continue

		# Skip if a valid snapshot has already existed within last 2 hours
		if frappe.get_all(
			"Virtual Disk Snapshot",
			{
				"status": [
					"in",
					["Pending", "Completed"],
				],
				"virtual_machine": virtual_machine_name,
				"physical_backup": 0,
				"rolling_snapshot": 1,
				"creation": (">=", frappe.utils.add_to_date(None, hours=-2)),
			},
			limit=1,
		):
			continue

		try:
			# Also, if vm has multiple volumes, then exclude boot volume
			frappe.get_doc("Virtual Machine", virtual_machine_name).create_snapshots(
				exclude_boot_volume=True, rolling_snapshot=True
			)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()


AWS_SERIAL_CONSOLE_ENDPOINT_MAP = {
	"us-east-2": {
		"endpoint": "serial-console.ec2-instance-connect.us-east-2.aws",
		"fingerprint": "SHA256:EhwPkTzRtTY7TRSzz26XbB0/HvV9jRM7mCZN0xw/d/0",
	},
	"us-east-1": {
		"endpoint": "serial-console.ec2-instance-connect.us-east-1.aws",
		"fingerprint": "SHA256:dXwn5ma/xadVMeBZGEru5l2gx+yI5LDiJaLUcz0FMmw",
	},
	"us-west-1": {
		"endpoint": "serial-console.ec2-instance-connect.us-west-1.aws",
		"fingerprint": "SHA256:OHldlcMET8u7QLSX3jmRTRAPFHVtqbyoLZBMUCqiH3Y",
	},
	"us-west-2": {
		"endpoint": "serial-console.ec2-instance-connect.us-west-2.aws",
		"fingerprint": "SHA256:EMCIe23TqKaBI6yGHainqZcMwqNkDhhAVHa1O2JxVUc",
	},
	"af-south-1": {
		"endpoint": "ec2-serial-console.af-south-1.api.aws",
		"fingerprint": "SHA256:RMWWZ2fVePeJUqzjO5jL2KIgXsczoHlz21Ed00biiWI",
	},
	"ap-east-1": {
		"endpoint": "ec2-serial-console.ap-east-1.api.aws",
		"fingerprint": "SHA256:T0Q1lpiXxChoZHplnAkjbP7tkm2xXViC9bJFsjYnifk",
	},
	"ap-south-2": {
		"endpoint": "ec2-serial-console.ap-south-2.api.aws",
		"fingerprint": "SHA256:WJgPBSwV4/shN+OPITValoewAuYj15DVW845JEhDKRs",
	},
	"ap-southeast-3": {
		"endpoint": "ec2-serial-console.ap-southeast-3.api.aws",
		"fingerprint": "SHA256:5ZwgrCh+lfns32XITqL/4O0zIfbx4bZgsYFqy3o8mIk",
	},
	"ap-southeast-4": {
		"endpoint": "ec2-serial-console.ap-southeast-4.api.aws",
		"fingerprint": "SHA256:Avaq27hFgLvjn5gTSShZ0oV7h90p0GG46wfOeT6ZJvM",
	},
	"ap-south-1": {
		"endpoint": "serial-console.ec2-instance-connect.ap-south-1.aws",
		"fingerprint": "SHA256:oBLXcYmklqHHEbliARxEgH8IsO51rezTPiSM35BsU40",
	},
	"ap-northeast-3": {
		"endpoint": "ec2-serial-console.ap-northeast-3.api.aws",
		"fingerprint": "SHA256:Am0/jiBKBnBuFnHr9aXsgEV3G8Tu/vVHFXE/3UcyjsQ",
	},
	"ap-northeast-2": {
		"endpoint": "serial-console.ec2-instance-connect.ap-northeast-2.aws",
		"fingerprint": "SHA256:FoqWXNX+DZ++GuNTztg9PK49WYMqBX+FrcZM2dSrqrI",
	},
	"ap-southeast-1": {
		"endpoint": "serial-console.ec2-instance-connect.ap-southeast-1.aws",
		"fingerprint": "SHA256:PLFNn7WnCQDHx3qmwLu1Gy/O8TUX7LQgZuaC6L45CoY",
	},
	"ap-southeast-2": {
		"endpoint": "serial-console.ec2-instance-connect.ap-southeast-2.aws",
		"fingerprint": "SHA256:yFvMwUK9lEUQjQTRoXXzuN+cW9/VSe9W984Cf5Tgzo4",
	},
	"ap-northeast-1": {
		"endpoint": "serial-console.ec2-instance-connect.ap-northeast-2.aws",
		"fingerprint": "SHA256:RQfsDCZTOfQawewTRDV1t9Em/HMrFQe+CRlIOT5um4k",
	},
	"ca-central-1": {
		"endpoint": "serial-console.ec2-instance-connect.ca-central-1.aws",
		"fingerprint": "SHA256:P2O2jOZwmpMwkpO6YW738FIOTHdUTyEv2gczYMMO7s4",
	},
	"cn-north-1": {
		"endpoint": "ec2-serial-console.cn-north-1.api.amazonwebservices.com.cn",
		"fingerprint": "SHA256:2gHVFy4H7uU3+WaFUxD28v/ggMeqjvSlgngpgLgGT+Y",
	},
	"cn-northwest-1": {
		"endpoint": "ec2-serial-console.cn-northwest-1.api.amazonwebservices.com.cn",
		"fingerprint": "SHA256:TdgrNZkiQOdVfYEBUhO4SzUA09VWI5rYOZGTogpwmiM",
	},
	"eu-central-1": {
		"endpoint": "serial-console.ec2-instance-connect.eu-central-1.aws",
		"fingerprint": "SHA256:aCMFS/yIcOdOlkXvOl8AmZ1Toe+bBnrJJ3Fy0k0De2c",
	},
	"eu-west-1": {
		"endpoint": "serial-console.ec2-instance-connect.eu-west-1.aws",
		"fingerprint": "SHA256:h2AaGAWO4Hathhtm6ezs3Bj7udgUxi2qTrHjZAwCW6E",
	},
	"eu-west-2": {
		"endpoint": "serial-console.ec2-instance-connect.eu-west-2.aws",
		"fingerprint": "SHA256:a69rd5CE/AEG4Amm53I6lkD1ZPvS/BCV3tTPW2RnJg8",
	},
	"eu-south-1": {
		"endpoint": "ec2-serial-console.eu-south-1.api.aws",
		"fingerprint": "SHA256:lC0kOVJnpgFyBVrxn0A7n99ecLbXSX95cuuS7X7QK30",
	},
	"eu-west-3": {
		"endpoint": "serial-console.ec2-instance-connect.eu-west-3.aws",
		"fingerprint": "SHA256:q8ldnAf9pymeNe8BnFVngY3RPAr/kxswJUzfrlxeEWs",
	},
	"eu-south-2": {
		"endpoint": "ec2-serial-console.eu-south-2.api.aws",
		"fingerprint": "SHA256:GoCW2DFRlu669QNxqFxEcsR6fZUz/4F4n7T45ZcwoEc",
	},
	"eu-north-1": {
		"endpoint": "serial-console.ec2-instance-connect.eu-north-1.aws",
		"fingerprint": "SHA256:tkGFFUVUDvocDiGSS3Cu8Gdl6w2uI32EPNpKFKLwX84",
	},
	"eu-central-2": {
		"endpoint": "ec2-serial-console.eu-central-2.api.aws",
		"fingerprint": "SHA256:8Ppx2mBMf6WdCw0NUlzKfwM4/IfRz4OaXFutQXWp6mk",
	},
	"me-south-1": {
		"endpoint": "ec2-serial-console.me-south-1.api.aws",
		"fingerprint": "SHA256:nPjLLKHu2QnLdUq2kVArsoK5xvPJOMRJKCBzCDqC3k8",
	},
	"me-central-1": {
		"endpoint": "ec2-serial-console.me-central-1.api.aws",
		"fingerprint": "SHA256:zpb5duKiBZ+l0dFwPeyykB4MPBYhI/XzXNeFSDKBvLE",
	},
	"sa-east-1": {
		"endpoint": "ec2-serial-console.sa-east-1.api.aws",
		"fingerprint": "SHA256:rd2+/32Ognjew1yVIemENaQzC+Botbih62OqAPDq1dI",
	},
	"us-gov-east-1": {
		"endpoint": "serial-console.ec2-instance-connect.us-gov-east-1.amazonaws.com",
		"fingerprint": "SHA256:tIwe19GWsoyLClrtvu38YEEh+DHIkqnDcZnmtebvF28",
	},
	"us-gov-west-1": {
		"endpoint": "serial-console.ec2-instance-connect.us-gov-west-1.amazonaws.com",
		"fingerprint": "SHA256:kfOFRWLaOZfB+utbd3bRf8OlPf8nGO2YZLqXZiIw5DQ",
	},
}
