# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import ipaddress
import boto3
from frappe.model.document import Document
from frappe.core.utils import find
from frappe.model.naming import make_autoname
from frappe.desk.utils import slug
from press.overrides import get_permission_query_conditions_for_doctype

USER_DATA = """#!/bin/bash
rm -rf /etc/ssh/ssh_host_*
ssh-keygen -A
"""


class VirtualMachine(Document):
	def autoname(self):
		series = f"{self.series}-{slug(self.cluster)}.#####"
		self.index = int(make_autoname(series)[-5:])
		self.name = f"{self.series}{self.index}-{slug(self.cluster)}.{self.domain}"

	def validate(self):
		if not self.machine_image:
			self.machine_image = self.get_latest_ubuntu_image()
		if not self.private_ip_address:
			ip = ipaddress.IPv4Interface(self.subnet_cidr_block).ip
			index = self.index + 356
			if self.series == "n":
				self.private_ip_address = str(ip + index)
			else:
				offset = ["f", "m"].index(self.series)
				self.private_ip_address = str(
					ip + 256 * (2 * (index // 256) + offset) + (index % 256)
				)
		if self.virtual_machine_image:
			self.disk_size = max(
				self.disk_size,
				frappe.db.get_value("Virtual Machine Image", self.virtual_machine_image, "size"),
			)

	@frappe.whitelist()
	def provision(self):
		response = self.client().run_instances(
			BlockDeviceMappings=[
				{
					"DeviceName": "/dev/sda1",
					"Ebs": {
						"DeleteOnTermination": True,
						"VolumeSize": self.disk_size,  # This in GB. Fucking AWS!
						"VolumeType": "gp3",
					},
				},
			],
			ImageId=self.machine_image,
			InstanceType=self.machine_type,
			KeyName=self.ssh_key,
			MaxCount=1,
			MinCount=1,
			Monitoring={"Enabled": False},
			Placement={"AvailabilityZone": self.availability_zone, "Tenancy": "default"},
			NetworkInterfaces=[
				{
					"AssociatePublicIpAddress": True,
					"DeleteOnTermination": True,
					"DeviceIndex": 0,
					"PrivateIpAddress": self.private_ip_address,
					"Groups": [self.aws_security_group_id],
					"SubnetId": self.aws_subnet_id,
				},
			],
			DisableApiTermination=True,
			InstanceInitiatedShutdownBehavior="stop",
			TagSpecifications=[
				{
					"ResourceType": "instance",
					"Tags": [{"Key": "Name", "Value": f"Frappe Cloud - {self.name}"}],
				},
			],
			UserData=USER_DATA,
		)

		self.aws_instance_id = response["Instances"][0]["InstanceId"]
		self.status = self.get_status_map()[response["Instances"][0]["State"]["Name"]]
		self.save()

	def get_status_map(self):
		return {
			"pending": "Pending",
			"running": "Running",
			"shutting-down": "Pending",
			"stopping": "Pending",
			"stopped": "Stopped",
			"terminated": "Terminated",
		}

	def get_latest_ubuntu_image(self):
		return self.client("ssm").get_parameter(
			Name="/aws/service/canonical/ubuntu/server/20.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
		)["Parameter"]["Value"]

	@frappe.whitelist()
	def reboot(self):
		self.client().reboot_instances(InstanceIds=[self.aws_instance_id])

	def increase_disk_size(self, increment=50):
		volume = self.volumes[0]
		volume.size += increment
		self.disk_size = volume.size
		self.client().modify_volume(VolumeId=volume.aws_volume_id, Size=volume.size)
		self.save()

	def get_volumes(self):
		response = self.client().describe_volumes(
			Filters=[{"Name": "attachment.instance-id", "Values": [self.aws_instance_id]}]
		)
		return response["Volumes"]

	def convert_to_gp3(self):
		for volume in self.volumes:
			if volume.volume_type != "gp3":
				volume.volume_type = "gp3"
				volume.iops = max(3000, volume.iops)
				volume.throughput = 250 if volume.size > 340 else 125
				self.client().modify_volume(
					VolumeId=volume.aws_volume_id,
					VolumeType=volume.volume_type,
					Iops=volume.iops,
					Throughput=volume.throughput,
				)
				self.save()

	@frappe.whitelist()
	def sync(self):
		response = self.client().describe_instances(InstanceIds=[self.aws_instance_id])
		instance = response["Reservations"][0]["Instances"][0]

		self.status = self.get_status_map()[instance["State"]["Name"]]
		self.machine_type = instance.get("InstanceType")

		self.public_ip_address = instance.get("PublicIpAddress")
		self.private_ip_address = instance.get("PrivateIpAddress")

		self.public_dns_name = instance.get("PublicDnsName")
		self.private_dns_name = instance.get("PrivateDnsName")

		for volume in self.get_volumes():
			existing_volume = find(self.volumes, lambda v: v.aws_volume_id == volume["VolumeId"])
			if existing_volume:
				row = existing_volume
			else:
				row = frappe._dict()
			row.aws_volume_id = volume["VolumeId"]
			row.volume_type = volume["VolumeType"]
			row.size = volume["Size"]
			row.iops = volume["Iops"]
			if "Throughput" in volume:
				row.throughput = volume["Throughput"]

			if not existing_volume:
				self.append("volumes", row)

		self.disk_size = self.volumes[0].size

		self.termination_protection = self.client().describe_instance_attribute(
			InstanceId=self.aws_instance_id, Attribute="disableApiTermination"
		)["DisableApiTermination"]["Value"]
		self.save()
		self.update_servers()

	def update_servers(self):
		status_map = {
			"Pending": "Pending",
			"Running": "Active",
			"Terminated": "Archived",
			"Stopped": "Archived",
		}
		for doctype in ["Server", "Database Server", "Proxy Server"]:
			server = frappe.get_all(doctype, {"virtual_machine": self.name}, pluck="name")
			if server:
				server = server[0]
				frappe.db.set_value(doctype, server, "ip", self.public_ip_address)
				if self.public_ip_address:
					frappe.get_doc(doctype, server).create_dns_record()
				frappe.db.set_value(doctype, server, "status", status_map[self.status])

	def update_name_tag(self, name):
		self.client().create_tags(
			Resources=[self.aws_instance_id],
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
	def disable_termination_protection(self):
		self.client().modify_instance_attribute(
			InstanceId=self.aws_instance_id, DisableApiTermination={"Value": False}
		)
		self.sync()

	@frappe.whitelist()
	def enable_termination_protection(self):
		self.client().modify_instance_attribute(
			InstanceId=self.aws_instance_id, DisableApiTermination={"Value": True}
		)
		self.sync()

	@frappe.whitelist()
	def start(self):
		self.client().start_instances(InstanceIds=[self.aws_instance_id])

	@frappe.whitelist()
	def stop(self):
		self.client().stop_instances(InstanceIds=[self.aws_instance_id])

	@frappe.whitelist()
	def terminate(self):
		self.client().terminate_instances(InstanceIds=[self.aws_instance_id])

	@frappe.whitelist()
	def resize(self, machine_type):
		self.client().modify_instance_attribute(
			InstanceId=self.aws_instance_id,
			InstanceType={"Value": machine_type},
		)
		self.machine_type = machine_type
		self.save()

	def client(self, client_type="ec2"):
		cluster = frappe.get_doc("Cluster", self.cluster)
		return boto3.client(
			client_type,
			region_name=self.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)

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
			document["is_server_setup"] = True

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
			document["is_server_setup"] = True

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


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Virtual Machine"
)


def sync_virtual_machines():
	machines = frappe.get_all(
		"Virtual Machine", {"status": ("not in", ("Terminated", "Draft"))}
	)
	for machine in machines:
		try:
			frappe.get_doc("Virtual Machine", machine.name).sync()
			frappe.db.commit()
		except Exception:
			import traceback

			traceback.print_exc()


def terminate_virtual_machines():
	machines = frappe.get_all(
		"Virtual Machine",
		{"status": ("not in", ("Terminated", "Draft")), "series": ("in", ["m", "f"])},
	)
	for machine in machines:
		try:
			print(machine)
			machine = frappe.get_doc("Virtual Machine", machine.name)
			machine.sync()
			machine.disable_termination_protection()
			machine.terminate()
			frappe.db.commit()
		except Exception:
			import traceback

			traceback.print_exc()
