# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import base64
import ipaddress
import boto3
from oci.core import ComputeClient, BlockstorageClient, VirtualNetworkClient
from oci.core.models import (
	LaunchInstanceShapeConfigDetails,
	UpdateInstanceShapeConfigDetails,
	LaunchInstancePlatformConfig,
	CreateVnicDetails,
	LaunchInstanceDetails,
	UpdateInstanceDetails,
	InstanceSourceViaImageDetails,
	InstanceOptions,
	UpdateBootVolumeDetails,
	UpdateVolumeDetails,
	CreateBootVolumeBackupDetails,
	CreateVolumeBackupDetails,
)


from frappe.model.document import Document
from frappe.core.utils import find
from frappe.model.naming import make_autoname
from frappe.desk.utils import slug
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import log_error


class VirtualMachine(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.virtual_machine_volume.virtual_machine_volume import (
			VirtualMachineVolume,
		)

		availability_zone: DF.Data
		cloud_provider: DF.Literal["", "AWS EC2", "OCI"]
		cluster: DF.Link
		disk_size: DF.Int
		domain: DF.Link
		index: DF.Int
		instance_id: DF.Data | None
		machine_image: DF.Data | None
		machine_type: DF.Data
		private_dns_name: DF.Data | None
		private_ip_address: DF.Data | None
		public_dns_name: DF.Data | None
		public_ip_address: DF.Data | None
		ram: DF.Int
		region: DF.Link
		security_group_id: DF.Data | None
		series: DF.Literal["n", "f", "m", "c", "p", "e", "r"]
		ssh_key: DF.Link
		status: DF.Literal["Draft", "Pending", "Running", "Stopped", "Terminated"]
		subnet_cidr_block: DF.Data | None
		subnet_id: DF.Data | None
		team: DF.Link | None
		termination_protection: DF.Check
		vcpu: DF.Int
		virtual_machine_image: DF.Link | None
		volumes: DF.Table[VirtualMachineVolume]
	# end: auto-generated types

	server_doctypes = [
		"Server",
		"Database Server",
		"Proxy Server",
		"Monitor Server",
		"Log Server",
	]

	def autoname(self):
		series = f"{self.series}-{slug(self.cluster)}.#####"
		self.index = int(make_autoname(series)[-5:])
		self.name = f"{self.series}{self.index}-{slug(self.cluster)}.{self.domain}"

	def validate(self):
		if self.virtual_machine_image:
			self.disk_size = max(
				self.disk_size,
				frappe.db.get_value("Virtual Machine Image", self.virtual_machine_image, "size"),
			)
			self.machine_image = frappe.db.get_value(
				"Virtual Machine Image", self.virtual_machine_image, "image_id"
			)
		if not self.machine_image:
			self.machine_image = self.get_latest_ubuntu_image()
		if not self.private_ip_address:
			ip = ipaddress.IPv4Interface(self.subnet_cidr_block).ip
			index = self.index + 356
			if self.series == "n":
				self.private_ip_address = str(ip + index)
			else:
				offset = ["f", "m", "c", "p", "e", "r"].index(self.series)
				self.private_ip_address = str(
					ip + 256 * (2 * (index // 256) + offset) + (index % 256)
				)

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

	@frappe.whitelist()
	def provision(self):
		if self.cloud_provider == "AWS EC2":
			return self._provision_aws()
		elif self.cloud_provider == "OCI":
			return self._provision_oci()

	def _provision_aws(self):
		options = {
			"BlockDeviceMappings": [
				{
					"DeviceName": "/dev/sda1",
					"Ebs": {
						"DeleteOnTermination": True,
						"VolumeSize": self.disk_size,  # This in GB. Fucking AWS!
						"VolumeType": "gp3",
					},
				},
			],
			"ImageId": self.machine_image,
			"InstanceType": self.machine_type,
			"KeyName": self.ssh_key,
			"MaxCount": 1,
			"MinCount": 1,
			"Monitoring": {"Enabled": False},
			"Placement": {"AvailabilityZone": self.availability_zone, "Tenancy": "default"},
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
			options["CreditSpecification"] = {
				"CpuCredits": "unlimited" if self.series == "n" else "standard"
			}
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
						boot_volume_size_in_gbs=max(self.disk_size, 50),
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
						"user_data": base64.b64encode(self.get_cloud_init().encode()).decode()
						if self.virtual_machine_image
						else "",
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
				"ansible_memtotal_mb": frappe.db.get_value("Server Plan", server.plan, "memory")
				or 1024,
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
					"mariadb_exporter_config": frappe.render_template(
						"press/playbooks/roles/mysqld_exporter/templates/mysqld_exporter.service",
						mariadb_context,
						is_path=True,
					),
				}
			)

		init = frappe.render_template(cloud_init_template, context, is_path=True)
		return init

	def get_server(self):
		for doctype in self.server_doctypes:
			server = frappe.db.get_value(doctype, {"virtual_machine": self.name}, "name")
			if server:
				return frappe.get_doc(doctype, server)

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
			return self.client("ssm").get_parameter(
				Name="/aws/service/canonical/ubuntu/server/20.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
			)["Parameter"]["Value"]
		elif self.cloud_provider == "OCI":
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

	@frappe.whitelist()
	def reboot(self):
		if self.cloud_provider == "AWS EC2":
			self.client().reboot_instances(InstanceIds=[self.instance_id])
		elif self.cloud_provider == "OCI":
			self.client().instance_action(instance_id=self.instance_id, action="RESET")
		self.sync()

	@frappe.whitelist()
	def increase_disk_size(self, increment=50):
		volume = self.volumes[0]
		volume.size += int(increment or 50)
		self.disk_size = volume.size
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
		elif self.cloud_provider == "OCI":
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
	def sync(self):
		if self.cloud_provider == "AWS EC2":
			return self._sync_aws()
		elif self.cloud_provider == "OCI":
			return self._sync_oci()

	def _sync_oci(self):
		instance = self.client().get_instance(instance_id=self.instance_id).data
		if instance and instance.lifecycle_state != "TERMINATED":
			cluster = frappe.get_doc("Cluster", self.cluster)

			self.status = self.get_oci_status_map()[instance.lifecycle_state]

			self.ram = instance.shape_config.memory_in_gbs * 1024
			self.vcpu = instance.shape_config.vcpus
			self.machine_type = f"{int(self.vcpu)}x{int(instance.shape_config.memory_in_gbs)}"

			for vnic_attachment in (
				self.client()
				.list_vnic_attachments(
					compartment_id=cluster.oci_tenancy, instance_id=self.instance_id
				)
				.data
			):
				try:
					vnic = (
						self.client(VirtualNetworkClient).get_vnic(vnic_id=vnic_attachment.vnic_id).data
					)
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
						volume = (
							self.client(BlockstorageClient).get_volume(volume_id=volume.volume_id).data
						)
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
				self.disk_size = self.volumes[0].size

			for volume in list(self.volumes):
				if volume.volume_id not in available_volumes:
					self.remove(volume)

		else:
			self.status = "Terminated"
		self.save()
		self.update_servers()

	def _sync_aws(self, response=None):
		if not response:
			response = self.client().describe_instances(InstanceIds=[self.instance_id])
		if response["Reservations"]:
			instance = response["Reservations"][0]["Instances"][0]

			self.status = self.get_aws_status_map()[instance["State"]["Name"]]
			self.machine_type = instance.get("InstanceType")

			self.public_ip_address = instance.get("PublicIpAddress")
			self.private_ip_address = instance.get("PrivateIpAddress")

			self.public_dns_name = instance.get("PublicDnsName")
			self.private_dns_name = instance.get("PrivateDnsName")

			attached_volumes = []
			for volume in self.get_volumes():
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
				if "Throughput" in volume:
					row.throughput = volume["Throughput"]

				if not existing_volume:
					self.append("volumes", row)

			self.disk_size = self.volumes[0].size if self.volumes else self.disk_size

			for volume in list(self.volumes):
				if volume.volume_id not in attached_volumes:
					self.remove(volume)

			self.termination_protection = self.client().describe_instance_attribute(
				InstanceId=self.instance_id, Attribute="disableApiTermination"
			)["DisableApiTermination"]["Value"]

			instance_type_response = self.client().describe_instance_types(
				InstanceTypes=[self.machine_type]
			)
			self.ram = instance_type_response["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"]
			self.vcpu = instance_type_response["InstanceTypes"][0]["VCpuInfo"]["DefaultVCpus"]
		else:
			self.status = "Terminated"
		self.save()
		self.update_servers()

	def update_servers(self):
		status_map = {
			"Pending": "Pending",
			"Running": "Active",
			"Terminated": "Archived",
			"Stopped": "Archived",
		}
		for doctype in self.server_doctypes:
			server = frappe.get_all(doctype, {"virtual_machine": self.name}, pluck="name")
			if server:
				server = server[0]
				frappe.db.set_value(doctype, server, "ip", self.public_ip_address)
				if doctype in ["Server", "Database Server"]:
					frappe.db.set_value(doctype, server, "ram", self.ram)
				if self.public_ip_address:
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
	def create_image(self):
		image = frappe.get_doc(
			{"doctype": "Virtual Machine Image", "virtual_machine": self.name}
		).insert()
		return image.name

	@frappe.whitelist()
	def create_snapshots(self):
		if self.cloud_provider == "AWS EC2":
			self._create_snapshots_aws()
		elif self.cloud_provider == "OCI":
			self._create_snapshots_oci()

	def _create_snapshots_aws(self):
		response = self.client().create_snapshots(
			InstanceSpecification={"InstanceId": self.instance_id},
			Description=f"Frappe Cloud - {self.name} - {frappe.utils.now()}",
			TagSpecifications=[
				{
					"ResourceType": "snapshot",
					"Tags": [
						{"Key": "Name", "Value": f"Frappe Cloud - {self.name} - {frappe.utils.now()}"}
					],
				},
			],
		)
		for snapshot in response.get("Snapshots", []):
			try:
				frappe.get_doc(
					{
						"doctype": "Virtual Disk Snapshot",
						"virtual_machine": self.name,
						"snapshot_id": snapshot["SnapshotId"],
					}
				).insert()
			except Exception:
				log_error(
					title="Virtual Disk Snapshot Error", virtual_machine=self.name, snapshot=snapshot
				)

	def _create_snapshots_oci(self):
		for volume in self.volumes:
			if ".bootvolume." in volume.volume_id:
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
				self.client(BlockstorageClient).create_volume_backup(
					CreateVolumeBackupDetails(
						volume_id=volume.volume_id,
						type="INCREMENTAL",
						display_name=f"Frappe Cloud - {self.name} - {volume.name} - {frappe.utils.now()}",
					)
				).data
			try:
				frappe.get_doc(
					{
						"doctype": "Virtual Disk Snapshot",
						"virtual_machine": self.name,
						"snapshot_id": snapshot.id,
					}
				).insert()
			except Exception:
				log_error(
					title="Virtual Disk Snapshot Error", virtual_machine=self.name, snapshot=snapshot
				)

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
	def stop(self):
		if self.cloud_provider == "AWS EC2":
			self.client().stop_instances(InstanceIds=[self.instance_id])
		elif self.cloud_provider == "OCI":
			self.client().instance_action(instance_id=self.instance_id, action="STOP")
		self.sync()

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

	@frappe.whitelist()
	def update_ebs_performance(self, iops, throughput):
		if self.cloud_provider == "AWS EC2":
			volume = self.volumes[0]
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
			vpus = ((volume.iops / volume.size) - 45) / 1.5
			return vpus

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
		elif self.cloud_provider == "OCI":
			return (client_type or ComputeClient)(cluster.get_oci_config())

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
			groups.append(
				frappe.db.get_value("Cluster", self.cluster, "proxy_security_group_id")
			)
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
			["cluster"],
			{"status": ("not in", ("Terminated", "Draft")), "cloud_provider": "AWS EC2"},
			group_by="cluster",
			pluck="cluster",
		):
			# Pick a random machine
			# TODO: This probably should be a method on the Cluster
			machine = frappe.get_doc(
				"Virtual Machine",
				{
					"status": ("not in", ("Terminated", "Draft")),
					"cloud_provider": "AWS EC2",
					"cluster": cluster,
				},
			)
			frappe.enqueue_doc(
				machine.doctype,
				machine.name,
				method="bulk_sync_aws_cluster",
				queue="sync",
				job_id=f"bulk_sync_aws:{machine.cluster}",
			)

	def bulk_sync_aws_cluster(self):
		client = self.client()
		instance_ids = frappe.get_all(
			"Virtual Machine",
			filters={
				"status": ("not in", ("Terminated", "Draft")),
				"cloud_provider": "AWS EC2",
				"cluster": self.cluster,
			},
			pluck="instance_id",
		)
		response = client.describe_instances(InstanceIds=instance_ids)
		for reservation in response["Reservations"]:
			for instance in reservation["Instances"]:
				machine = frappe.get_doc("Virtual Machine", {"instance_id": instance["InstanceId"]})
				try:
					machine._sync_aws({"Reservations": [{"Instances": [instance]}]})
					frappe.db.commit()
				except Exception:
					log_error("Virtual Machine Sync Error", virtual_machine=machine.name)
					frappe.db.rollback()

	@classmethod
	def bulk_sync_oci(cls):
		machines = frappe.get_all(
			"Virtual Machine",
			{"status": ("not in", ("Terminated", "Draft")), "cloud_provider": "OCI"},
		)
		for machine in machines:
			try:
				frappe.get_doc("Virtual Machine", machine.name).sync()
				frappe.db.commit()
			except Exception:
				log_error("Virtual Machine Sync Error", virtual_machine=machine.name)
				frappe.db.rollback()


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Virtual Machine"
)


@frappe.whitelist()
def sync_virtual_machines():
	VirtualMachine.bulk_sync_aws()
	VirtualMachine.bulk_sync_oci()


def snapshot_virtual_machines():
	machines = frappe.get_all("Virtual Machine", {"status": "Running"})
	for machine in machines:
		try:
			frappe.get_doc("Virtual Machine", machine.name).create_snapshots()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Virtual Machine Snapshot Error", virtual_machine=machine.name)


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
