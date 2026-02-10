# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import base64
import ipaddress
import time
import typing

import boto3
import botocore
import frappe
import pydo
import rq
from frappe.core.utils import find
from frappe.desk.utils import slug
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint
from frappe.utils.password import get_decrypted_password
from hcloud import APIException
from hcloud import Client as HetznerClient
from hcloud.servers.domain import ServerCreatePublicNetwork
from oci import pagination as oci_pagination
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
from press.press.doctype.server_activity.server_activity import log_server_activity
from press.utils import log_error
from press.utils.jobs import has_job_timeout_exceeded

if typing.TYPE_CHECKING:
	from press.infrastructure.doctype.virtual_machine_migration.virtual_machine_migration import (
		VirtualMachineMigration,
	)
	from press.press.doctype.cluster.cluster import Cluster
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.log_server.log_server import LogServer
	from press.press.doctype.monitor_server.monitor_server import MonitorServer
	from press.press.doctype.proxy_server.proxy_server import ProxyServer
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot import VirtualDiskSnapshot
	from press.press.doctype.virtual_machine_image.virtual_machine_image import VirtualMachineImage


server_doctypes = [
	"Server",
	"Database Server",
	"Proxy Server",
	"Monitor Server",
	"Log Server",
	"NFS Server",
	"NAT Server",
]

SERIES_TO_SERVER_TYPE = {
	"f": "Server",
	"fs": "Server",
	"u": "Server",
	"m": "Database Server",
	"n": "Proxy Server",
	"nat": "NAT Server",
	"nfs": "NFS Server",
	"p": "Monitor Server",
	"r": "Registry Server",
	"e": "Log Server",
}

HETZNER_ROOT_DISK_ID = "hetzner-root-disk"
DIGITALOCEAN_ROOT_DISK_ID = "digital-ocean-root-disk"
HETZNER_ACTION_RETRIES = 60  # retry count; try to keep it lower so that it doesn't surpass than default RQ job timeout of 300 seconds


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
		cloud_provider: DF.Literal["", "AWS EC2", "OCI", "Hetzner", "DigitalOcean"]
		cluster: DF.Link
		data_disk_snapshot: DF.Link | None
		data_disk_snapshot_attached: DF.Check
		data_disk_snapshot_volume_id: DF.Data | None
		disable_server_snapshot: DF.Check
		disk_size: DF.Int
		domain: DF.Link
		has_data_volume: DF.Check
		index: DF.Int
		instance_id: DF.Data | None
		is_static_ip: DF.Check
		kms_key_id: DF.Data | None
		machine_image: DF.Data | None
		machine_type: DF.Data
		platform: DF.Literal["x86_64", "arm64"]
		private_dns_name: DF.Data | None
		private_ip_address: DF.Data | None
		public_dns_name: DF.Data | None
		public_ip_address: DF.Data | None
		ram: DF.Int
		ready_for_conversion: DF.Check
		region: DF.Link
		root_disk_size: DF.Int
		secondary_private_ip: DF.Data | None
		security_group_id: DF.Data | None
		series: DF.Literal["n", "f", "m", "c", "p", "e", "r", "u", "t", "nfs", "fs", "nat"]
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

	@property
	def is_database_server(self) -> bool:
		if self.series == "m":
			return True

		return frappe.db.exists("Database Server", {"virtual_machine": self.name})

	def autoname(self):
		series = f"{self.series}-{slug(self.cluster)}.#####"
		self.index = int(make_autoname(series)[-5:])
		self.name = f"{self.series}{self.index}-{slug(self.cluster)}.{self.domain}"

	def after_insert(self):
		if self.virtual_machine_image:
			image: VirtualMachineImage = frappe.get_doc("Virtual Machine Image", self.virtual_machine_image)
			if image.has_data_volume:
				# We have two separate volumes for root and data
				# Copy their sizes correctly
				self.disk_size = max(self.disk_size, image.size)
				self.root_disk_size = max(self.root_disk_size, image.root_size)
				self.has_data_volume = True
			else:
				# We have only one volume. Both root and data are the same
				self.disk_size = max(self.disk_size, image.size)
				self.root_disk_size = self.disk_size
				self.has_data_volume = False

			self.machine_image = image.image_id

			# If data disk snapshot is provided, that will attach as second disk
			# Regardless of VMI supporting data disk or not
			if self.data_disk_snapshot:
				self.has_data_volume = True
				self.root_disk_size = image.root_size
				self.disk_size = max(
					self.disk_size,
					frappe.db.get_value("Virtual Disk Snapshot", self.data_disk_snapshot, "size"),
				)

		if not self.machine_image:
			self.machine_image = self.get_latest_ubuntu_image()
		self.save()

	def get_private_ip(self) -> str:
		ip = ipaddress.IPv4Interface(self.subnet_cidr_block).ip
		index = self.index + 356

		if self.series == "n":
			return str(ip + index)

		window = 2 if self.series == "nat" else 1  # reserve 2 IPs for nat servers
		additional_offset = int(self.series == "nat" and bool(self.private_ip_address))

		offset = ["n", "f", "m", "c", "p", "e", "r", "u", "t", "nfs", "fs", "nat"].index(self.series)
		return str(ip + (256 * (2 * (index // 256) + offset) + (index % 256)) * window + additional_offset)

	def validate(self):
		# Digital ocean does not support custom private IPs in a vpc
		if not self.private_ip_address and self.cloud_provider != "DigitalOcean":
			self.private_ip_address = self.get_private_ip()

		self.validate_data_disk_snapshot()

		if self.series == "nat" and self.cloud_provider != "AWS EC2":
			frappe.throw("NAT Servers are only supported on AWS EC2")

	def validate_data_disk_snapshot(self):
		if not self.is_new() or not self.data_disk_snapshot:
			return

		if self.cloud_provider != "AWS EC2":
			frappe.throw("Server Creation with Data Disk Snapshot is only supported on AWS EC2.")

		# Ensure the disk snapshot is Completed
		snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.data_disk_snapshot)
		if snapshot.status != "Completed":
			frappe.throw("Disk Snapshot is not available.")

		if snapshot.region != frappe.get_value("Cluster", self.cluster, "region"):
			frappe.throw("Disk Snapshot is not available in the same region as the cluster")

		if not self.virtual_machine_image:
			frappe.throw("Virtual Machine Image is required to create a VM with Data Disk Snapshot")

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
		server = self.get_server()

		if self.has_value_changed("has_data_volume") and server:
			server.has_data_volume = self.has_data_volume
			server.save()

		if self.has_value_changed("disk_size") and self.should_bill_addon_storage():
			self.update_subscription_for_addon_storage()

	def check_and_attach_data_disk_snapshot_volume(self):
		if not self.data_disk_snapshot_volume_id:
			frappe.throw("Data Disk Snapshot Volume ID is not set.")

		volume_state = self.get_state_of_volume(self.data_disk_snapshot_volume_id)
		if volume_state == "available":
			self.attach_volume(self.data_disk_snapshot_volume_id)
			self.data_disk_snapshot_attached = True
			self.status = "Pending"
			self.save()
			return True

		if volume_state == "deleted":
			self.data_disk_snapshot_volume_id = None

		self.status = "Pending"
		self.save()
		return False

	def ensure_no_data_disk_attached_before_attaching_snapshot_disk(self):  # noqa: C901
		"""
		returns status: bool
			- True, if parent function should assume this function has did it's part
			- False, parent function should call it again

		"""
		if (
			not self.data_disk_snapshot  # vm doesn't have dependency on disk snapshot, so no point of dont this check
			# These two below checks are there to prevent
			# Any accidental call to this function
			or self.data_disk_snapshot_volume_id  # volume from snapshot has been created
			or self.data_disk_snapshot_attached  # data disk attached already
		):
			"""
			Sanity Check

			In dual disk (root + data) VMIs, we can't create the machine with the root disk only

			So, once the VM spawned the first task is to detach and delete the extra disk
			Once, that's done we can move ahead.

			As it dealing with disk deletion, this check serve as a safeguard.

			!!NOTE!! : Don't remove until unless we have stricter check somewhere else
			"""
			return

		if len(self.volumes) == 0:
			frappe.throw("Sync the VM before checking data disk for snapshot recovery")

		if len(self.volumes) == 1:
			return

		# For more volumes, found out other volume ids
		additional_volume_ids = []
		for volume_id in self.volumes:
			if volume_id.device in ["/dev/xvda1", "/dev/sda1"]:
				continue
			if volume_id.volume_id == self.data_disk_snapshot_volume_id:
				continue
			additional_volume_ids.append(volume_id.volume_id)

		for volume_id in additional_volume_ids:
			# Don't do syncing multiple times
			self.delete_volume(volume_id, sync=False)

		if len(additional_volume_ids):
			self.sync()

	def create_data_disk_volume_from_snapshot(self):
		try:
			self.ensure_no_data_disk_attached_before_attaching_snapshot_disk()
			datadisk_snapshot: VirtualDiskSnapshot = frappe.get_doc(
				"Virtual Disk Snapshot", self.data_disk_snapshot
			)
			snapshot_volume = datadisk_snapshot.create_volume(
				availability_zone=self.availability_zone, volume_initialization_rate=300, size=self.disk_size
			)
			self.data_disk_snapshot_volume_id = snapshot_volume
			self.status = "Pending"
			self.save()
			return True
		except Exception:
			log_error(
				title="VM Data Disk Snapshot Volume Creation Failed",
			)
			if not self.data_disk_snapshot_volume_id:
				return False
			# If it fails for any reason, try to delete the volume
			try:
				self.delete_volume(self.data_disk_snapshot_volume_id)
			except:  # noqa: E722
				log_error(
					title="VM Data Disk Snapshot Volume Cleanup Failed",
				)
			return False

	def should_bill_addon_storage(self):
		"""Check if storage addition should create/update subscription record"""
		# Increasing data volume regardless of auto or manual increment
		if not self.has_data_volume:
			return True

		if self.has_data_volume and not self.has_value_changed("root_disk_size"):
			return True

		return False

	def _handle_updated_addon_storage(self, server: Server, increment: int) -> None:
		if frappe.db.exists(
			"Subscription",
			{"document_name": server.name, "team": server.team, "plan_type": "Server Storage Plan"},
		):
			# update the existing subscription
			frappe.db.set_value(
				"Subscription",
				{
					"document_name": server.name,
					"team": server.team,
					"plan_type": "Server Storage Plan",
				},
				{
					"additional_storage": increment,
					"enabled": 1,
				},
			)
		else:
			# create a new subscription
			frappe.get_doc(
				doctype="Subscription",
				team=server.team,
				plan_type="Server Storage Plan",
				plan="Add-on Storage plan",
				document_type=server.doctype,
				document_name=server.name,
				additional_storage=increment,
				enabled=1,
			).insert()

	def _plan_change_addon_storage(self, server: Server) -> None:
		if frappe.db.exists(
			"Subscription",
			{"document_name": server.name, "team": server.team, "plan_type": "Server Storage Plan"},
		):
			frappe.db.set_value(
				"Subscription",
				{
					"document_name": server.name,
					"team": server.team,
					"plan_type": "Server Storage Plan",
				},
				"enabled",
				0,
			)

	def update_subscription_for_addon_storage(self):
		"""Update subscription record"""
		server = self.get_server()

		if not server or server.doctype == "NFS Server":
			return

		server_plan_size = frappe.db.get_value("Server Plan", server.plan, "disk")

		if server_plan_size and self.disk_size > server_plan_size:
			# Add on storage was added or updated
			increment = self.disk_size - server_plan_size
			self._handle_updated_addon_storage(server, increment)
		elif self.disk_size == server_plan_size:
			# Server was upgraded or downgraded from plan change
			# Remove the existing add-on storage subscription
			self._plan_change_addon_storage(server)
		return

	@frappe.whitelist()
	def provision(self, assign_public_ip=True):
		if self.cloud_provider == "AWS EC2":
			return self._provision_aws(assign_public_ip)
		if self.cloud_provider == "OCI":
			return self._provision_oci()
		if self.cloud_provider == "Hetzner":
			return self._provision_hetzner()
		if self.cloud_provider == "DigitalOcean":
			return self._provision_digital_ocean()

		return None

	def _get_digital_ocean_ssh_key_id(self) -> int:
		"""Get digital ocean ssh key id"""
		keys = self.client().ssh_keys.list()
		keys = keys.get("ssh_keys", [])
		existing_key = [key for key in keys if key["name"] == self.ssh_key]
		if not existing_key:
			frappe.throw(f"No SSH Key found on Digital Ocean with the name {self.ssh_key}")

		return existing_key[0]["id"]

	def _provision_digital_ocean(self):
		"""Provision a Digital Ocean Droplet"""
		if not self.machine_image:
			frappe.throw("Machine Image is required to provision Hetzner Virtual Machine.")

		cluster: Cluster = frappe.get_doc("Cluster", self.cluster)

		firewalls = self.client().firewalls.list()
		firewalls = firewalls.get("firewalls", [])
		cluster_firewall = next(fw for fw in firewalls if fw["id"] == cluster.security_group_id)

		if cluster_firewall["status"] == "failed":
			frappe.throw(f"Firewall with id {cluster.security_group_id} failed")

		try:
			droplet = self.client().droplets.create(
				{
					"name": self.name,
					"region": cluster.region,
					"size": self.machine_type,
					"image": self.machine_image,
					"ssh_keys": [self._get_digital_ocean_ssh_key_id()],
					"backups": False,
					"vpc_uuid": cluster.vpc_id,
					"user_data": self.get_cloud_init() if self.virtual_machine_image else "",
				}
			)
			self.instance_id = droplet["droplet"]["id"]
		except Exception as e:
			frappe.throw(f"Failed to provision Digital Ocean Droplet: {e!s}")

		try:
			for group in self.get_security_groups():
				self.client().firewalls.assign_droplets(group, {"droplet_ids": [self.instance_id]})
		except Exception as e:
			frappe.throw(f"Failed to assign Firewall to Digital Ocean Droplet: {e!s}")

		self.status = self.get_digital_ocean_status_map()[droplet["droplet"]["status"]]
		self.save()
		frappe.db.commit()

	def _provision_hetzner(self):
		from hcloud.firewalls.domain import Firewall
		from hcloud.images.domain import Image
		from hcloud.locations.domain import Location
		from hcloud.networks.domain import Network
		from hcloud.server_types.domain import ServerType
		from hcloud.ssh_keys.domain import SSHKey

		if not self.machine_image:
			frappe.throw("Machine Image is required to provision Hetzner Virtual Machine.")

		cluster = frappe.get_doc("Cluster", self.cluster)

		server = (
			self.client()
			.servers.create(
				name=self.name,
				server_type=ServerType(name=self.machine_type),
				image=Image(cint(self.machine_image)),
				networks=[],  # Don't attach to any network during creation
				firewalls=[
					Firewall(id=cint(security_group_id)) for security_group_id in self.get_security_groups()
				],
				location=Location(name=cluster.region),
				public_net=ServerCreatePublicNetwork(
					enable_ipv4=True,
					enable_ipv6=False,
				),
				ssh_keys=[
					SSHKey(name=self.ssh_key),
				],
				user_data=self.get_cloud_init() if self.virtual_machine_image else "",
			)
			.server
		)
		self.instance_id = server.id
		self.save()
		# To ensure, we don't lose state, because machine has been created at this point
		frappe.db.commit()

		# Attach Server to Private Network
		# Because, this allows us to provide the required private IP during network attachment
		self.client().servers.attach_to_network(
			server=server,
			network=Network(id=cint(cluster.vpc_id)),
			ip=self.private_ip_address,
		).wait_until_finished(HETZNER_ACTION_RETRIES)

		self.status = self.get_hetzner_status_map()[server.status]
		self.save()

		# Enqueue enable protection separately to avoid any issue
		frappe.enqueue_doc(self.doctype, self.name, "enable_termination_protection", sync=False)

	def _provision_aws(self, assign_public_ip=True):  # noqa: C901
		additional_volumes = []
		if self.virtual_machine_image:
			image = frappe.get_doc("Virtual Machine Image", self.virtual_machine_image)
			if image.has_data_volume:
				volume = image.get_data_volume()
				data = {
					"DeviceName": volume.device,
					"Ebs": {
						"DeleteOnTermination": True,
						"VolumeSize": max(self.disk_size, volume.size),
						"VolumeType": volume.volume_type,
					},
				}
				if self.kms_key_id:
					data["Ebs"]["Encrypted"] = True
					data["Ebs"]["KmsKeyId"] = self.kms_key_id

				additional_volumes.append(data)

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
			if self.kms_key_id:
				volume_options["Ebs"]["Encrypted"] = True
				volume_options["Ebs"]["KmsKeyId"] = self.kms_key_id
			additional_volumes.append(volume_options)

		if self.data_disk_snapshot:
			additional_volumes = []  # Don't attach any additional volumes if we are attaching a data disk snapshot

		if not self.machine_image:
			self.machine_image = self.get_latest_ubuntu_image()
			self.save(ignore_version=True)

		root_disk_data = {
			"DeviceName": "/dev/sda1",
			"Ebs": {
				"DeleteOnTermination": True,
				"VolumeSize": self.root_disk_size,  # This in GB. Fucking AWS!
				"VolumeType": "gp3",
			},
		}

		if self.kms_key_id:
			root_disk_data["Ebs"]["Encrypted"] = True
			root_disk_data["Ebs"]["KmsKeyId"] = self.kms_key_id

		options = {
			"BlockDeviceMappings": [
				*[root_disk_data],
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
					"AssociatePublicIpAddress": bool(assign_public_ip),
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

		if self.series == "nat":
			# Disable Source/Dest Check for NAT instances
			self.disable_source_dest_check()

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

	def get_mariadb_context(
		self, server: Server | DatabaseServer, memory: int
	) -> dict[str, str | int] | None:
		if server.doctype == "Database Server":
			return {
				"server_id": server.server_id,
				"private_ip": self.private_ip_address or "__PRIVATE_IP__",
				"ansible_memtotal_mb": memory,
				"mariadb_root_password": server.get_password("mariadb_root_password"),
				"db_port": server.db_port or 3306,
			}
		if server.doctype == "Server" and server.is_unified_server:
			database_server: DatabaseServer = frappe.get_doc("Database Server", server.database_server)
			return {
				"server_id": database_server.server_id,
				"private_ip": self.private_ip_address or "__PRIVATE_IP__",
				"ansible_memtotal_mb": memory,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
				"db_port": database_server.db_port or 3306,
			}

		return None

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
				{
					"private_ip": self.private_ip_address or "__PRIVATE_IP__"
				},  # Replace inside cloudinit in case of DigitalOcean
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
			"is_unified_server": getattr(server, "is_unified_server", False),
		}
		if server.doctype == "Database Server" or getattr(server, "is_unified_server", False):
			memory = frappe.db.get_value("Server Plan", server.plan, "memory") or 1024
			if memory < 1024:
				frappe.throw("MariaDB cannot be installed on a server plan with less than 1GB RAM.")

			mariadb_context = self.get_mariadb_context(server, memory)

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

	def get_digital_ocean_status_map(self):
		return {
			"new": "Pending",
			"active": "Running",
			"off": "Stopped",
			"archive": "Terminated",
		}

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
			if images:
				return images[0].id
		if self.cloud_provider == "Hetzner":
			images = self.client().images.get_all(
				name="ubuntu-22.04",
				architecture="x86" if self.platform == "x86_64" else "arm",
				sort="created:desc",
				type="system",
			)
			if images and len(images) > 0:
				return images[0].id

		if self.cloud_provider == "DigitalOcean":
			images = self.client().images.list(type="distribution", private=False)
			images = images["images"]
			ubuntu_images = [image for image in images if "22.04" in image["name"]]

			if not ubuntu_images:
				frappe.throw("No image available for Ubuntu 22.04")

			return ubuntu_images[0]["id"]

		return None

	@frappe.whitelist()
	def reboot(self):
		if self.cloud_provider == "AWS EC2":
			self.client().reboot_instances(InstanceIds=[self.instance_id])
		elif self.cloud_provider == "OCI":
			self.client().instance_action(instance_id=self.instance_id, action="RESET")
		elif self.cloud_provider == "Hetzner":
			self.client().servers.reboot(self.get_hetzner_server_instance(fetch_data=False))
		elif self.cloud_provider == "DigitalOcean":
			self.client().droplet_actions.post(self.instance_id, {"type": "reboot"})

		if server := self.get_server():
			log_server_activity(self.series, server.name, action="Reboot")

		self.sync()

	@frappe.whitelist()
	def increase_disk_size(self, volume_id=None, increment=50):  # noqa: C901
		if not increment:
			return
		if not volume_id:
			volume_id = self.volumes[0].volume_id

		volume = find(self.volumes, lambda v: v.volume_id == volume_id)
		volume.size += int(increment)
		self.disk_size = self.get_data_volume().size
		self.root_disk_size = self.get_root_volume().size
		is_root_volume = self.get_root_volume().volume_id == volume.volume_id
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
		elif self.cloud_provider == "Hetzner":
			if volume_id == HETZNER_ROOT_DISK_ID:
				frappe.throw("Cannot increase disk size for hetzner root disk.")

			from hcloud.volumes.domain import Volume

			self.client().volumes.resize(Volume(volume_id), volume.size)

		elif self.cloud_provider == "DigitalOcean":
			if volume_id == DIGITALOCEAN_ROOT_DISK_ID:
				frappe.throw("Cannot increase disk size for Digital Ocean root disk.")

			self.client().volumes.resize(
				volume_id,
				{
					"size_gigabytes": volume.size,
					"region": frappe.get_value("Cluster", self.cluster, "region"),
				},
			)

		if server := self.get_server():
			log_server_activity(
				self.series,
				server=server.name,
				action="Disk Size Change",
				reason=f"{'Root' if is_root_volume else 'Data'} volume increased by {increment} GB",
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
		if self.cloud_provider == "Hetzner":
			instance = self.get_hetzner_server_instance(fetch_data=True)
			volumes = []
			for v in instance.volumes:
				volumes.append(
					frappe._dict(
						{
							"id": v.id,
							"device": v.linux_device,
							"size": v.size,
						}
					)
				)

			# This is a dummy/mock representation to make the code compatible
			# with root_volume code.
			volumes.append(
				frappe._dict(
					{
						"id": HETZNER_ROOT_DISK_ID,
						"device": "/dev/sda",
						"size": instance.primary_disk_size,
					}
				)
			)

			return volumes

		if self.cloud_provider == "DigitalOcean":
			attached_volumes = []
			instance = self.get_digital_ocean_server_instance()["droplet"]
			volume_ids = instance["volume_ids"]  # List of attached volume IDs
			if volume_ids:
				volumes = self.client().volumes.list()["volumes"]
				volumes = [v for v in volumes if v["id"] in volume_ids]
			else:
				volumes = []

			for v in volumes:
				attached_volumes.append(
					frappe._dict(
						{
							"id": v.id,
							"size": v.size_gigabytes,
						}
					)
				)

			volumes.append(
				frappe._dict(
					{
						"id": DIGITALOCEAN_ROOT_DISK_ID,
						"device": "/dev/sda",
						"size": instance["disk"],
					}
				)
			)
			return volumes
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
		if self.cloud_provider == "DigitalOcean":
			return self._sync_digital_ocean(*args, **kwargs)
		return None

	def _update_volume_info_after_sync(self):
		attached_volumes = []
		attached_devices = []

		for volume_index, volume in enumerate(self.get_volumes(), start=1):
			existing_volume = find(self.volumes, lambda v: v.volume_id == volume.id)
			row = existing_volume if existing_volume else frappe._dict()
			row.volume_id = volume.id
			attached_volumes.append(row.volume_id)
			row.size = volume.size
			row.device = volume.device
			attached_devices.append(row.device)

			row.idx = volume_index
			if not existing_volume:
				self.append("volumes", row)

		for volume in list(self.volumes):
			if volume.volume_id not in attached_volumes:
				self.remove(volume)

		for volume in list(self.temporary_volumes):
			if volume.device not in attached_devices:
				self.remove(volume)

		if self.volumes:
			self.disk_size = self.get_data_volume().size
			self.root_disk_size = self.get_root_volume().size

	def _sync_digital_ocean(self, *args, **kwargs):
		server_instance = self.get_digital_ocean_server_instance()

		if server_instance.get("id", None) == "not_found":
			self.status = "Terminated"
			self.save()
			self.update_servers()
			return

		server_instance = server_instance.get("droplet", {})

		self.status = self.get_digital_ocean_status_map()[server_instance["status"]]
		self.machine_type = server_instance["size"]["slug"]
		self.vcpu = server_instance["size"]["vcpus"]
		self.ram = server_instance["size"]["memory"]

		self.private_ip_address = ""
		self.public_ip_address = ""

		if len(server_instance["networks"]["v4"]) > 0:
			private_network = next(
				(net for net in server_instance["networks"]["v4"] if net["type"] == "private"), None
			)
			public_network = next(
				(net for net in server_instance["networks"]["v4"] if net["type"] == "public"), None
			)

			if private_network:
				self.private_ip_address = private_network.get("ip_address", "")

			if public_network:
				self.public_ip_address = public_network.get("ip_address", "")

		# We don't have volume support yet for digital ocean droplets
		self.root_disk_size = server_instance["disk"]
		self.disk_size = server_instance["disk"]

		self._update_volume_info_after_sync()

		self.save()
		self.update_servers()

	def _sync_hetzner(self, server_instance=None):
		if not server_instance:
			try:
				server_instance = self.get_hetzner_server_instance(fetch_data=True)
			except APIException as e:
				if e.code == "not_found":
					self.status = "Terminated"
					self.save()
				else:
					raise

		if not server_instance:
			# If server not found, mark it as terminated
			# Update status at server side as well
			if self.status == "Terminated":
				self.update_servers()
			return

		self.status = self.get_hetzner_status_map()[server_instance.status]
		self.machine_type = server_instance.server_type.name
		self.vcpu = server_instance.server_type.cores
		self.ram = server_instance.server_type.memory * 1024

		self.private_ip_address = server_instance.private_net[0].ip if server_instance.private_net else ""
		self.public_ip_address = server_instance.public_net.ipv4.ip

		self.termination_protection = server_instance.protection.get("delete", False)

		self._update_volume_info_after_sync()

		self.save()
		self.update_servers()

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

	def has_static_ip(self, instance) -> bool:
		sip = False
		try:
			ip_owner_id = instance["NetworkInterfaces"][0]["Association"]["IpOwnerId"]
			sip = ip_owner_id.lower() != "amazon"
		except (KeyError, IndexError):
			pass
		return sip

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
			self.is_static_ip = self.has_static_ip(instance)

			if instance.get("NetworkInterfaces"):
				self.secondary_private_ip = next(
					(
						x["PrivateIpAddress"]
						for x in instance["NetworkInterfaces"][0]["PrivateIpAddresses"]
						if not x["Primary"]
					),
					None,
				)

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
			"Hetzner": lambda v: v.device == "/dev/sda",
			"DigitalOcean": lambda v: v.device == "/dev/sda",
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
			"Hetzner": lambda v: v.device != "/dev/sda" and v.device not in temporary_volume_devices,
			"DigitalOcean": lambda v: v.device != "/dev/sda" and v.device not in temporary_volume_devices,
		}
		data_volume_filter = DATA_VOLUME_FILTERS.get(self.cloud_provider)
		volume = find(self.volumes, data_volume_filter)
		if volume:  # Un-provisioned machines might not have any volumes
			return volume
		return frappe._dict({"size": 0})

	def update_servers(self):  # noqa: C901
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
				frappe.db.set_value(doctype, server, "private_ip", self.private_ip_address)
				if doctype in ["Server", "Proxy Server"]:
					frappe.db.set_value(doctype, server, "is_static_ip", self.is_static_ip)
				if doctype in ["Server", "Database Server"]:
					frappe.db.set_value(doctype, server, "ram", self.ram)
				if doctype in ("NAT Server",):
					frappe.db.set_value(doctype, server, "secondary_private_ip", self.secondary_private_ip)
				if self.public_ip_address:
					if frappe.flags.force_update_dns or self.has_value_changed("public_ip_address"):
						frappe.get_doc(doctype, server).create_dns_record()
				elif self.private_ip_address and (
					frappe.flags.force_update_dns or self.has_value_changed("private_ip_address")
				):
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
	def assign_secondary_private_ip(self):
		self.attach_secondary_private_ip()

	def attach_secondary_private_ip(self, secondary_private_ip=None):
		if self.cloud_provider != "AWS EC2":
			frappe.throw("Secondary IP assignment is currently only supported for AWS EC2 instances")

		if self.series != "nat":
			frappe.throw("Secondary IP assignment is only supported for NAT servers")

		# this is needed if we do failover and attach the secondary private ip of one instance to another
		secondary_private_ip = secondary_private_ip or self.get_private_ip()
		if frappe.db.get_value("Virtual Machine", {"secondary_private_ip": secondary_private_ip}):
			frappe.throw(f"Private IP {secondary_private_ip} is already assigned to another instance.")

		ec2 = self.client()
		instance = ec2.describe_instances(InstanceIds=[self.instance_id])
		ec2.assign_private_ip_addresses(
			NetworkInterfaceId=instance["Reservations"][0]["Instances"][0]["NetworkInterfaces"][0][
				"NetworkInterfaceId"
			],
			PrivateIpAddresses=[secondary_private_ip],
		)
		self.sync()

		return f"Assigned {self.secondary_private_ip}"

	def detach_secondary_private_ip(self):
		if self.cloud_provider != "AWS EC2":
			frappe.throw("Secondary IP detachment is currently only supported for AWS EC2 instances")

		if self.series != "nat":
			frappe.throw("Secondary IP detachment is only supported for NAT servers")

		if not self.secondary_private_ip:
			frappe.throw("No secondary private IP assigned to this instance.")

		ec2 = self.client()
		instance = ec2.describe_instances(InstanceIds=[self.instance_id])
		ec2.unassign_private_ip_addresses(
			NetworkInterfaceId=instance["Reservations"][0]["Instances"][0]["NetworkInterfaces"][0][
				"NetworkInterfaceId"
			],
			PrivateIpAddresses=[self.secondary_private_ip],
		)
		self.sync()

	def disable_source_dest_check(self):
		if self.cloud_provider != "AWS EC2":
			frappe.throw(
				"Source/Destination check modification is currently only supported for AWS EC2 instances"
			)

		ec2 = self.client()
		ec2.modify_instance_attribute(
			InstanceId=self.instance_id,
			SourceDestCheck={"Value": False},
		)

	def enable_source_dest_check(self):
		if self.cloud_provider != "AWS EC2":
			frappe.throw(
				"Source/Destination check modification is currently only supported for AWS EC2 instances"
			)

		ec2 = self.client()
		ec2.modify_instance_attribute(
			InstanceId=self.instance_id,
			SourceDestCheck={"Value": True},
		)

	@frappe.whitelist()
	def disassociate_auto_assigned_public_ip(self):
		if self.cloud_provider != "AWS EC2":
			frappe.throw("Public IP disassociation is currently only supported for AWS EC2 instances")

		if not self.public_ip_address:
			frappe.throw("No public IP associated with this instance.")

		try:
			frappe.db.get_value(self.doctype, self.name, "status", for_update=True, wait=False)
		except frappe.QueryTimeoutError:
			frappe.throw(
				"Unable to get a lock on the vm at this time. Some other process is probably underway"
			)

		ec2 = self.client()
		instance = ec2.describe_instances(InstanceIds=[self.instance_id])
		ec2.modify_network_interface_attribute(
			NetworkInterfaceId=instance["Reservations"][0]["Instances"][0]["NetworkInterfaces"][0][
				"NetworkInterfaceId"
			],
			AssociatePublicIpAddress=False,
		)
		frappe.flags.force_update_dns = True
		self.sync()

	@frappe.whitelist()
	def create_image(self, public=True):
		image = frappe.get_doc(
			{
				"doctype": "Virtual Machine Image",
				"virtual_machine": self.name,
				"public": public,
				"has_data_volume": self.has_data_volume,
				"platform": self.platform,
			}
		).insert()
		return image.name

	@frappe.whitelist()
	def create_snapshots(
		self,
		exclude_boot_volume=False,
		physical_backup=False,
		rolling_snapshot=False,
		dedicated_snapshot=False,
	):
		"""
		exclude_boot_volume is applicable only for Servers with data volume
		"""
		if not self.has_data_volume:
			exclude_boot_volume = False

		# Store the newly created snapshots reference in the flags
		# So that, we can get the correct reference of snapshots created in current session
		self.flags.created_snapshots = []
		if self.cloud_provider == "AWS EC2":
			self._create_snapshots_aws(
				exclude_boot_volume, physical_backup, rolling_snapshot, dedicated_snapshot
			)
		elif self.cloud_provider == "OCI":
			self._create_snapshots_oci(exclude_boot_volume)
		elif self.cloud_provider == "Hetzner":
			self._create_snapshots_hetzner()

	def _create_snapshots_aws(
		self,
		exclude_boot_volume: bool,
		physical_backup: bool,
		rolling_snapshot: bool,
		dedicated_snapshot: bool,
	):
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
					"Tags": [
						{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - {frappe.utils.now()}"},
						{"Key": "Physical Backup", "Value": "Yes" if physical_backup else "No"},
						{"Key": "Rolling Snapshot", "Value": "Yes" if rolling_snapshot else "No"},
						{"Key": "Dedicated Snapshot", "Value": "Yes" if dedicated_snapshot else "No"},
					],
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
						"dedicated_snapshot": dedicated_snapshot,
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

	def _create_snapshots_hetzner(self):
		server = self.get_hetzner_server_instance(fetch_data=True)
		response = server.create_image(
			type="snapshot", description=f"Frappe Cloud - {self.name} - {frappe.utils.now()}"
		)

		doc = frappe.get_doc(
			{
				"doctype": "Virtual Disk Snapshot",
				"virtual_machine": self.name,
				"snapshot_id": response.image.id,
				"volume_id": HETZNER_ROOT_DISK_ID,
			}
		).insert()
		self.flags.created_snapshots.append(doc.name)

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
	def disable_termination_protection(self, sync: bool | None = None):
		if sync is None:
			sync = False

		if self.cloud_provider == "AWS EC2":
			self.client().modify_instance_attribute(
				InstanceId=self.instance_id, DisableApiTermination={"Value": False}
			)
		elif self.cloud_provider == "Hetzner":
			self.get_hetzner_server_instance().change_protection(delete=False, rebuild=False)

		if sync:
			self.sync()

	@frappe.whitelist()
	def enable_termination_protection(self, sync: bool | None = None):
		if sync is None:
			sync = False

		if self.cloud_provider == "AWS EC2":
			self.client().modify_instance_attribute(
				InstanceId=self.instance_id, DisableApiTermination={"Value": True}
			)
		elif self.cloud_provider == "Hetzner":
			self.get_hetzner_server_instance().change_protection(delete=True, rebuild=True)

		if sync:
			self.sync()

	@frappe.whitelist()
	def start(self):
		if self.cloud_provider == "AWS EC2":
			self.client().start_instances(InstanceIds=[self.instance_id])
		elif self.cloud_provider == "OCI":
			self.client().instance_action(instance_id=self.instance_id, action="START")
		elif self.cloud_provider == "Hetzner":
			self.client().servers.power_on(self.get_hetzner_server_instance(fetch_data=False))
		elif self.cloud_provider == "DigitalOcean":
			self.client().droplet_actions.post(self.instance_id, {"type": "power_on"})

		# Digital Ocean `start` takes some time therefore this sync is useless for DO.
		self.sync()

	@frappe.whitelist()
	def stop(self, force=False):
		if self.cloud_provider == "AWS EC2":
			self.client().stop_instances(InstanceIds=[self.instance_id], Force=bool(force))
		elif self.cloud_provider == "OCI":
			self.client().instance_action(instance_id=self.instance_id, action="STOP")
		elif self.cloud_provider == "Hetzner":
			self.client().servers.shutdown(self.get_hetzner_server_instance(fetch_data=False))
		elif self.cloud_provider == "DigitalOcean":
			self.client().droplet_actions.post(self.instance_id, {"type": "power_off"})
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
	def terminate(self):  # noqa: C901
		if self.cloud_provider == "AWS EC2":
			self.client().terminate_instances(InstanceIds=[self.instance_id])

		elif self.cloud_provider == "OCI":
			self.client().terminate_instance(instance_id=self.instance_id)

		elif self.cloud_provider == "Hetzner":
			for volume in self.volumes:
				if volume.volume_id == HETZNER_ROOT_DISK_ID:
					continue
				self.delete_volume(volume.volume_id, sync=False)
			self.client().servers.delete(
				self.get_hetzner_server_instance(fetch_data=False)
			).wait_until_finished(HETZNER_ACTION_RETRIES)

		elif self.cloud_provider == "DigitalOcean":
			for volume in self.volumes:
				if volume.volume_id == DIGITALOCEAN_ROOT_DISK_ID:
					continue
				self.delete_volume(volume.volume_id, sync=False)

			self.client().droplets.destroy(self.instance_id)

		if server := self.get_server():
			log_server_activity(self.series, server.name, action="Terminated")

	def _wait_for_digital_ocean_resize_action_completion(self, action_id: int):
		"""Wait for resize to complete before starting the droplet."""
		if self.cloud_provider == "DigitalOcean" and action_id:
			time.sleep(2)  # Wait for some time before checking the action status
			action = self.client().actions.get(action_id)
			if action["action"]["status"] == "completed":
				self.start()
			else:
				frappe.enqueue_doc(
					"Virtual Machine",
					self.name,
					"_wait_for_digital_ocean_resize_action_completion",
					action_id=action_id,
					queue="long",
				)

	@frappe.whitelist()
	def resize(self, machine_type, upgrade_disk: bool = False):
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
		elif self.cloud_provider == "Hetzner":
			from hcloud.server_types.domain import ServerType

			self.client().servers.change_type(
				self.get_hetzner_server_instance(fetch_data=False),
				server_type=ServerType(name=machine_type),
				upgrade_disk=upgrade_disk,
			)

		elif self.cloud_provider == "DigitalOcean":
			resize_action = self.client().droplet_actions.post(
				droplet_id=self.instance_id,
				body={
					"type": "resize",
					"size": machine_type,
					"disk": upgrade_disk,
				},
			)
			action_id = resize_action["action"]["id"]
			frappe.enqueue_doc(
				"Virtual Machine",
				self.name,
				"_wait_for_digital_ocean_resize_action_completion",
				action_id=action_id,
				queue="long",
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
			api_token = cluster.get_password("hetzner_api_token")
			return HetznerClient(token=api_token)

		if self.cloud_provider == "DigitalOcean":
			api_token = cluster.get_password("digital_ocean_api_token")
			return pydo.Client(token=api_token)

		return None

	@frappe.whitelist()
	def create_unified_server(self) -> tuple[Server, DatabaseServer]:
		"""Virtual machines of series U will create a u series app server and u series database server"""

		if self.series != "u":
			frappe.throw("Only virtual machines of series 'u' can create unified servers.")

		server_document = {
			"doctype": "Server",
			"hostname": f"u{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"team": self.team,
			"is_primary": True,
			"platform": self.platform,
			"is_unified_server": True,
		}

		if self.virtual_machine_image:
			server_document["is_server_prepared"] = True
			server_document["is_server_setup"] = True
			server_document["is_server_renamed"] = True
			server_document["is_upstream_setup"] = True

		else:
			server_document["is_provisioning_press_job_completed"] = True

		common_agent_password = frappe.generate_hash(length=32)

		server = frappe.get_doc(server_document)
		server.agent_password = common_agent_password
		server = server.insert()

		database_server_document = {
			"doctype": "Database Server",
			"hostname": f"u{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"server_id": self.index,
			"is_primary": True,
			"team": self.team,
			"is_unified_server": True,
		}

		if self.virtual_machine_image:
			database_server_document["is_server_prepared"] = True
			database_server_document["is_server_setup"] = True
			database_server_document["is_server_renamed"] = True
			if self.data_disk_snapshot:
				database_server_document["mariadb_root_password"] = get_decrypted_password(
					"Virtual Disk Snapshot", self.data_disk_snapshot, "mariadb_root_password"
				)
			else:
				database_server_document["mariadb_root_password"] = get_decrypted_password(
					"Virtual Machine Image", self.virtual_machine_image, "mariadb_root_password"
				)

			if not database_server_document["mariadb_root_password"]:
				frappe.throw(
					f"Virtual Machine Image {self.virtual_machine_image} does not have a MariaDB root password set."
				)
		else:
			database_server_document["is_provisioning_press_job_completed"] = True

		database_server = frappe.get_doc(database_server_document)
		database_server.agent_password = common_agent_password
		database_server = database_server.insert()

		return server, database_server

	@frappe.whitelist()
	def create_server(self, is_secondary: bool = False, primary: str | None = None) -> Server:
		document = {
			"doctype": "Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"team": self.team,
			"is_primary": not is_secondary,
			"is_secondary": is_secondary,
			"platform": self.platform,
			"primary": primary,
		}

		if self.virtual_machine_image:
			document["is_server_prepared"] = True
			document["is_server_setup"] = True
			document["is_server_renamed"] = True
			document["is_upstream_setup"] = True
		else:
			document["is_provisioning_press_job_completed"] = True

		server = frappe.get_doc(document).insert()
		frappe.msgprint(frappe.get_desk_link(server.doctype, server.name))
		return server

	@frappe.whitelist()
	def create_database_server(self) -> DatabaseServer:
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
			if self.data_disk_snapshot:
				document["mariadb_root_password"] = get_decrypted_password(
					"Virtual Disk Snapshot", self.data_disk_snapshot, "mariadb_root_password"
				)
			else:
				document["mariadb_root_password"] = get_decrypted_password(
					"Virtual Machine Image", self.virtual_machine_image, "mariadb_root_password"
				)

			if not document["mariadb_root_password"]:
				frappe.throw(
					f"Virtual Machine Image {self.virtual_machine_image} does not have a MariaDB root password set."
				)
		else:
			document["is_provisioning_press_job_completed"] = True

		server = frappe.get_doc(document).insert()
		frappe.msgprint(frappe.get_desk_link(server.doctype, server.name))
		return server

	def get_root_domains(self):
		return frappe.get_all("Root Domain", {"enabled": True}, pluck="name")

	@frappe.whitelist()
	def create_proxy_server(self) -> ProxyServer:
		document = {
			"doctype": "Proxy Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": self.cloud_provider,
			"virtual_machine": self.name,
			"team": self.team,
			"domains": [{"domain": domain} for domain in self.get_root_domains()],
		}
		if self.virtual_machine_image:
			document["is_server_setup"] = True
			document["is_primary"] = True

		server = frappe.get_doc(document).insert()
		frappe.msgprint(frappe.get_desk_link(server.doctype, server.name))
		return server

	@frappe.whitelist()
	def create_monitor_server(self) -> MonitorServer:
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

		server = frappe.get_doc(document).insert()
		frappe.msgprint(frappe.get_desk_link(server.doctype, server.name))
		return server

	@frappe.whitelist()
	def create_log_server(self) -> LogServer:
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

		server = frappe.get_doc(document).insert()
		frappe.msgprint(frappe.get_desk_link(server.doctype, server.name))
		return server

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

		server = frappe.get_doc(document).insert()
		frappe.msgprint(frappe.get_desk_link(server.doctype, server.name))
		return server

	@frappe.whitelist()
	def create_nat_server(self):
		if self.series != "nat":
			frappe.throw("Only virtual machines of series 'nat' can create NAT servers")

		document = {
			"doctype": "NAT Server",
			"hostname": f"{self.series}{self.index}-{slug(self.cluster)}",
			"domain": self.domain,
			"cluster": self.cluster,
			"provider": "AWS EC2",
			"virtual_machine": self.name,
		}
		if self.virtual_machine_image:
			document["is_server_setup"] = True

		server = frappe.get_doc(document).insert()
		frappe.msgprint(frappe.get_desk_link(server.doctype, server.name))
		return server

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

		if server := self.get_server():
			log_server_activity(
				self.series,
				server.name,
				action="Reboot",
				reason="Unable to reboot manually, rebooting with serial console",
			)

		self.sync()

	@classmethod
	def bulk_sync_aws(cls):
		try:
			clusters = frappe.get_all(
				"Virtual Machine",
				["cluster", "cloud_provider", "max(`index`) as max_index"],
				{
					"status": ("not in", ("Terminated", "Draft")),
					"cloud_provider": "AWS EC2",
				},
				group_by="cluster",
			)
		except:  # noqa E722
			clusters = frappe.get_all(
				"Virtual Machine",
				["cluster", "cloud_provider", {"MAX": "index", "as": "max_index"}],
				{
					"status": ("not in", ("Terminated", "Draft")),
					"cloud_provider": "AWS EC2",
				},
				group_by="cluster",
			)
		for cluster in clusters:
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
		for cluster in frappe.get_all("Cluster", {"cloud_provider": "OCI"}, pluck="name"):
			# pick any random non-terminated machine from the cluster
			machines = frappe.get_all(
				"Virtual Machine",
				filters={
					"status": ("not in", ("Terminated", "Draft")),
					"cloud_provider": "OCI",
					"cluster": cluster,
					"instance_id": ("is", "set"),
				},
				pluck="name",
				limit=1,
			)
			if not machines:
				continue
			frappe.enqueue_doc(
				"Virtual Machine",
				machines[0],
				method="bulk_sync_oci_cluster",
				queue="sync",
				job_id=f"bulk_sync_oci:{cluster}",
				deduplicate=True,
				cluster_name=cluster,
			)

	def bulk_sync_oci_cluster(self, cluster_name: str):
		cluster: Cluster = frappe.get_doc("Cluster", cluster_name)
		client: "ComputeClient" = self.client()

		try:
			response = oci_pagination.list_call_get_all_results(
				client.list_instances, compartment_id=cluster.oci_tenancy
			).data

			instance_ids = frappe.get_all(
				"Virtual Machine",
				filters={
					"status": ("not in", ("Terminated", "Draft")),
					"cloud_provider": "OCI",
					"cluster": cluster.name,
					"instance_id": ("is", "set"),
				},
				pluck="instance_id",
			)
			instance_ids = set(instance_ids)
			# filter out non-existing instances
			response = [instance for instance in response if instance.id in instance_ids]

			# Split into batches
			BATCH_SIZE = 15
			for i in range(0, len(response), BATCH_SIZE):
				frappe.enqueue_doc(
					"Virtual Machine",
					self.name,
					method="bulk_sync_oci_cluster_in_batch",
					queue="sync",
					job_id=f"bulk_sync_oci_batch:{cluster.name}:{i}-{i + BATCH_SIZE}",
					deduplicate=True,
					enqueue_after_commit=True,
					instances=response[i : i + BATCH_SIZE],
				)
		except Exception:
			log_error("Virtual Machine OCI Bulk Sync Error", cluster=cluster.name)
			frappe.db.rollback()

	def bulk_sync_oci_cluster_in_batch(self, instances: list[frappe._dict]):
		for instance in instances:
			machine: VirtualMachine = frappe.get_doc("Virtual Machine", {"instance_id": instance.id})
			if has_job_timeout_exceeded():
				return
			try:
				machine.sync(instance=instance)
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

	def _create_vmm(self, virtual_machine_image: str, machine_type: str) -> VirtualMachineMigration:
		return frappe.new_doc(
			"Virtual Machine Migration",
			virtual_machine=self.name,
			virtual_machine_image=virtual_machine_image,
			machine_type=machine_type,
		).insert()

	@frappe.whitelist()
	def convert_to_arm(self, virtual_machine_image, machine_type):
		if self.series == "f" and not self.ready_for_conversion:
			frappe.throw("Please complete pre-migration steps before migrating", frappe.ValidationError)

		return self._create_vmm(virtual_machine_image, machine_type)

	@frappe.whitelist()
	def convert_to_amd(self, virtual_machine_image, machine_type):
		return self._create_vmm(virtual_machine_image, machine_type)

	def attach_new_volume_aws_oci(self, size, iops=None, throughput=None, log_activity: bool = True):
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

		if self.kms_key_id:
			volume_options["Encrypted"] = True
			volume_options["KmsKeyId"] = self.kms_key_id
		volume_id = self.client().create_volume(**volume_options)["VolumeId"]
		self.wait_for_volume_to_be_available(volume_id)
		self.attach_volume(volume_id)

		if log_activity and (server := self.get_server()):
			log_server_activity(
				self.series,
				server.name,
				action="Volume",
				reason="Volume attached on server",
			)

		return volume_id

	def attach_new_volume_hetzner(self, size, iops=None, throughput=None, log_activity: bool = True):
		_ = iops
		_ = throughput

		volume_create_request = self.client().volumes.create(
			size=size,
			name=f"{self.name}-vol-{frappe.generate_hash(length=8)}",
			format="ext4",
			automount=False,
			server=self.get_hetzner_server_instance(fetch_data=False),
		)
		volume_create_request.action.wait_until_finished(HETZNER_ACTION_RETRIES)
		for action in volume_create_request.next_actions:
			action.wait_until_finished(HETZNER_ACTION_RETRIES)

		if log_activity and (server := self.get_server()):
			log_server_activity(
				self.series,
				server.name,
				action="Volume",
				reason="Volume attached on server",
			)

		return volume_create_request.volume.id

	@frappe.whitelist()
	def attach_new_volume(self, size, iops=None, throughput=None, log_activity: bool = True):
		if self.cloud_provider in ["AWS EC2", "OCI"]:
			return self.attach_new_volume_aws_oci(size, iops, throughput, log_activity)

		if self.cloud_provider == "Hetzner":
			return self.attach_new_volume_hetzner(size=size, log_activity=log_activity)

		return None

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

	def get_digital_ocean_server_instance(self):
		"""Get digital ocean droplet instance"""
		if self.cloud_provider != "DigitalOcean":
			raise NotImplementedError

		return self.client().droplets.get(self.instance_id)

	def get_hetzner_server_instance(self, fetch_data=True):
		if self.cloud_provider != "Hetzner":
			raise NotImplementedError

		if fetch_data:
			return self.client().servers.get_by_id(self.instance_id)

		from hcloud.servers.domain import Server as HetznerServer

		return HetznerServer(cint(self.instance_id))

	@frappe.whitelist()
	def attach_volume(self, volume_id, is_temporary_volume: bool = False):
		"""
		temporary_volumes: If you are attaching a volume to an instance just for temporary use, then set this to True.

		Then, snapshot and other stuff will be ignored for this volume.
		"""
		if self.cloud_provider == "AWS EC2":
			# Attach a volume to the instance and return the device name
			device_name = self.get_next_volume_device_name()
			self.client().attach_volume(
				Device=device_name,
				InstanceId=self.instance_id,
				VolumeId=volume_id,
			)

		elif self.cloud_provider == "Hetzner":
			volume = self.client().volumes.get_by_id(int(volume_id))

			"""
			This is a temporary assignment of linux_device from Hetzner API to
			device_name. linux_device is actually the mountpoint of the volume.
			Example: linux_device = /mnt/HC_Volume_103061048
			"""
			device_name = volume.linux_device
			for action in volume.get_actions():
				action.wait_until_finished(HETZNER_ACTION_RETRIES)  # wait for previous actions to finish

			self.client().volumes.attach(
				volume, self.get_hetzner_server_instance(fetch_data=False), automount=False
			)
		else:
			raise NotImplementedError

		if is_temporary_volume:
			# add the volume to the list of temporary volumes
			self.append("temporary_volumes", {"device": device_name})

		self.save()
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
	def detach(self, volume_id, sync: bool | None = None):
		if self.cloud_provider == "AWS EC2":
			volume = find(self.volumes, lambda v: v.volume_id == volume_id)
			if not volume:
				return False
			self.client().detach_volume(
				Device=volume.device, InstanceId=self.instance_id, VolumeId=volume.volume_id
			)
		elif self.cloud_provider == "OCI":
			raise NotImplementedError
		elif self.cloud_provider == "Hetzner":
			from hcloud.volumes.domain import Volume

			if volume_id == HETZNER_ROOT_DISK_ID:
				frappe.throw("Cannot detach hetzner root disk.")

			self.client().volumes.detach(Volume(id=volume_id)).wait_until_finished(HETZNER_ACTION_RETRIES)
		if sync:
			self.sync()
		return True

	@frappe.whitelist()
	def delete_volume(self, volume_id, sync: bool | None = None):  # noqa: C901
		if sync is None:
			sync = True

		if self.detach(volume_id, sync=sync):
			if self.cloud_provider == "AWS EC2":
				self.wait_for_volume_to_be_available(volume_id)
				self.client().delete_volume(VolumeId=volume_id)
				self.add_comment("Comment", f"Volume Deleted - {volume_id}")
			if self.cloud_provider == "OCI":
				raise NotImplementedError
			if self.cloud_provider == "Hetzner":
				if volume_id == HETZNER_ROOT_DISK_ID:
					frappe.throw("Cannot delete hetzner root disk.")

				from hcloud.volumes.domain import Volume

				self.client().volumes.delete(Volume(id=cint(volume_id)))

			if self.cloud_provider == "DigitalOcean":
				if volume_id == DIGITALOCEAN_ROOT_DISK_ID:
					frappe.throw("Cannot delete digitalocean root disk.")

				self.client().volumes.delete(volume_id=volume_id)

		if sync:
			self.sync()

	def detach_static_ip(self):
		if self.cloud_provider != "AWS EC2" or not self.is_static_ip:
			return

		client = self.client()
		response = client.describe_addresses(PublicIps=[self.public_ip_address])

		address_info = response["Addresses"][0]
		if "AssociationId" not in address_info:
			return

		client.disassociate_address(AssociationId=address_info["AssociationId"])
		self.sync()

	def attach_static_ip(self, static_ip):
		if self.cloud_provider != "AWS EC2":
			return

		if self.is_static_ip:
			frappe.throw("Virtual Machine already has a static IP associated.")

		client = self.client()
		response = client.describe_addresses(PublicIps=[static_ip])

		address_info = response["Addresses"][0]
		if "AssociationId" in address_info:
			frappe.throw("Static IP is already associated with another instance.")

		client.associate_address(AllocationId=address_info["AllocationId"], InstanceId=self.instance_id)
		self.sync()


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Virtual Machine")


def sync_virtual_machines_hetzner():
	for machine in frappe.get_all(
		"Virtual Machine",
		{"status": ("not in", ("Draft", "Terminated")), "cloud_provider": "Hetzner"},
		pluck="name",
	):
		if has_job_timeout_exceeded():
			return
		try:
			VirtualMachine("Virtual Machine", machine).sync()
			frappe.db.commit()  # release lock
		except Exception:
			log_error(title="Virtual Machine Sync Error", virtual_machine=machine)
			frappe.db.rollback()


@frappe.whitelist()
def sync_virtual_machines():
	VirtualMachine.bulk_sync_aws()
	VirtualMachine.bulk_sync_oci()
	sync_virtual_machines_hetzner()


def snapshot_oci_virtual_machines():
	machines = frappe.get_all(
		"Virtual Machine", {"status": "Running", "skip_automated_snapshot": 0, "cloud_provider": "OCI"}
	)
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


def snapshot_hetzner_virtual_machines():
	machines = frappe.get_all(
		"Virtual Machine", {"status": "Running", "skip_automated_snapshot": 0, "cloud_provider": "Hetzner"}
	)
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


def snapshot_aws_internal_virtual_machines():
	machines = frappe.get_all(
		"Virtual Machine",
		{
			"status": "Running",
			"skip_automated_snapshot": 0,
			"cloud_provider": "AWS EC2",
			"series": ("not in", ["f", "m"]),
		},
		pluck="name",
	)
	server_snapshot_disabled_vms = frappe.get_all(
		"Virtual Machine",
		{
			"status": "Running",
			"skip_automated_snapshot": 0,
			"cloud_provider": "AWS EC2",
			"disable_server_snapshot": 1,
			"series": ("in", ["f", "m"]),
		},
		pluck="name",
	)
	machines.extend(server_snapshot_disabled_vms)

	for machine in machines:
		# Skip if a snapshot has already been created today
		if frappe.get_all(
			"Virtual Disk Snapshot",
			{
				"virtual_machine": machine,
				"physical_backup": 0,
				"rolling_snapshot": 0,
				"creation": (">=", frappe.utils.today()),
			},
			limit=1,
		):
			continue
		try:
			frappe.get_doc("Virtual Machine", machine).create_snapshots()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Virtual Machine Snapshot Error", virtual_machine=machine)


def snapshot_aws_servers():
	servers_with_snapshot = frappe.get_all(
		"Server Snapshot",
		{
			"status": ["in", ["Pending", "Processing", "Completed"]],
			"consistent": 0,
			"free": 1,
			"creation": (">=", frappe.utils.today()),
		},
		pluck="app_server",
	)
	vms_with_snapshot = frappe.get_all(
		"Server", {"name": ("in", servers_with_snapshot)}, pluck="virtual_machine"
	)
	machines = frappe.get_all(
		"Virtual Machine",
		{
			"name": ("not in", vms_with_snapshot),
			"status": "Running",
			"skip_automated_snapshot": 0,
			"cloud_provider": "AWS EC2",
			"series": "f",
			"disable_server_snapshot": 0,
		},
		order_by="RAND()",
		pluck="name",
		limit_page_length=50,
	)
	for machine in machines:
		if has_job_timeout_exceeded():
			return
		app_server = frappe.get_value("Server", {"virtual_machine": machine}, "name")
		try:
			server: "Server" = frappe.get_doc("Server", app_server)
			servers = [
				["Server", server.name],
				["Database Server", server.database_server],
			]
			# Check if any press job is running on the server or the db server
			is_press_job_running = False
			for server_type, name in servers:
				if (
					frappe.db.count(
						"Press Job",
						filters={
							"status": ("in", ["Pending", "Running"]),
							"server_type": server_type,
							"server": name,
						},
					)
					> 0
				):
					is_press_job_running = True
					break

			# Also skip if the server was created within last 1 hour
			# to avoid snapshotting a blank server which is still being setup
			if is_press_job_running or server.creation > frappe.utils.add_to_date(None, hours=-1):
				continue

			server._create_snapshot(consistent=False, expire_at=frappe.utils.add_days(None, 2), free=True)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Server Snapshot Error", virtual_machine=machine)


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
