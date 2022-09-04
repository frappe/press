# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

import boto3
from frappe.model.document import Document
from frappe.core.utils import find


class VirtualMachine(Document):
	def validate(self):
		if not self.machine_image:
			self.machine_image = self.get_latest_ubuntu_image()

	def after_insert(self):
		self.provision()

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
				print(row.as_dict())
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
		self.save()

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

	@frappe.whitelist()
	def terminate(self):
		self.client().terminate_instances(InstanceIds=[self.aws_instance_id])

	def client(self, client_type="ec2"):
		cluster = frappe.get_doc("Cluster", self.cluster)
		return boto3.client(
			client_type,
			region_name=self.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)


def sync_virtual_machines():
	machines = frappe.get_all("Virtual Machine", {"status": "Pending"})
	for machine in machines:
		frappe.get_doc("Virtual Machine", machine.name).sync()
