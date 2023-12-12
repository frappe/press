# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import base64
import ipaddress
import boto3
from oci.core import ComputeClient, BlockstorageClient, VirtualNetworkClient
from oci.core.models import (
	LaunchInstanceShapeConfigDetails,
	LaunchInstancePlatformConfig,
	CreateVnicDetails,
	LaunchInstanceDetails,
	InstanceSourceViaImageDetails,
	InstanceOptions,
)


from frappe.model.document import Document
from frappe.core.utils import find
from frappe.model.naming import make_autoname
from frappe.desk.utils import slug
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import log_error


class VirtualMachine(Document):
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
				offset = ["f", "m", "c", "p", "e"].index(self.series)
				self.private_ip_address = str(
					ip + 256 * (2 * (index // 256) + offset) + (index % 256)
				)

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
					create_vnic_details=CreateVnicDetails(private_ip=self.private_ip_address),
					subnet_id=self.subnet_id,
					instance_options=InstanceOptions(are_legacy_imds_endpoints_disabled=True),
					source_details=InstanceSourceViaImageDetails(
						image_id=self.machine_image, boot_volume_size_in_gbs=max(self.disk_size, 50)
					),
					shape="VM.Standard3.Flex",
					shape_config=LaunchInstanceShapeConfigDetails(
						ocpus=vcpu // 2, vcpus=vcpu, memory_in_gbs=ram_in_gbs
					),
					platform_config=LaunchInstancePlatformConfig(type="INTEL_VM"),
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
				"ansible_memtotal_mb": frappe.db.get_value("Plan", server.plan, "memory") or 1024,
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
		self.client().modify_volume(VolumeId=volume.volume_id, Size=volume.size)
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
				vnic = (
					self.client(VirtualNetworkClient).get_vnic(vnic_id=vnic_attachment.vnic_id).data
				)
				self.public_ip_address = vnic.public_ip

			for volume in self.get_volumes():
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

				if not existing_volume:
					self.append("volumes", row)

			self.disk_size = self.volumes[0].size
		else:
			self.status = "Terminated"
		self.save()
		self.update_servers()

	def _sync_aws(self):
		response = self.client().describe_instances(InstanceIds=[self.instance_id])
		if response["Reservations"]:
			instance = response["Reservations"][0]["Instances"][0]

			self.status = self.get_aws_status_map()[instance["State"]["Name"]]
			self.machine_type = instance.get("InstanceType")

			self.public_ip_address = instance.get("PublicIpAddress")
			self.private_ip_address = instance.get("PrivateIpAddress")

			self.public_dns_name = instance.get("PublicDnsName")
			self.private_dns_name = instance.get("PrivateDnsName")

			for volume in self.get_volumes():
				existing_volume = find(self.volumes, lambda v: v.volume_id == volume["VolumeId"])
				if existing_volume:
					row = existing_volume
				else:
					row = frappe._dict()
				row.volume_id = volume["VolumeId"]
				row.volume_type = volume["VolumeType"]
				row.size = volume["Size"]
				row.iops = volume["Iops"]
				if "Throughput" in volume:
					row.throughput = volume["Throughput"]

				if not existing_volume:
					self.append("volumes", row)

			self.disk_size = self.volumes[0].size

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

	@frappe.whitelist()
	def disable_termination_protection(self):
		self.client().modify_instance_attribute(
			InstanceId=self.instance_id, DisableApiTermination={"Value": False}
		)
		self.sync()

	@frappe.whitelist()
	def enable_termination_protection(self):
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
		self.client().modify_instance_attribute(
			InstanceId=self.instance_id,
			InstanceType={"Value": machine_type},
		)
		self.machine_type = machine_type
		self.save()

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
			"provider": "AWS EC2",
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
			"provider": "AWS EC2",
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
			"provider": "AWS EC2",
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
			"provider": "AWS EC2",
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


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Virtual Machine"
)


def sync_virtual_machines():
	machines = frappe.get_all(
		"Virtual Machine", {"status": ("not in", ("Terminated", "Draft"))}
	)
	for machine in machines:
		frappe.enqueue_doc("Virtual Machine", machine.name, "sync", queue="long")


def snapshot_virtual_machines():
	machines = frappe.get_all("Virtual Machine", {"status": "Running"})
	for machine in machines:
		try:
			frappe.get_doc("Virtual Machine", machine.name).create_snapshots()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Virtual Machine Snapshot Error", virtual_machine=machine.name)
