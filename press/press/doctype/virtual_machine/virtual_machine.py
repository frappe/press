# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

import boto3
from frappe.model.document import Document


class VirtualMachine(Document):
	def validate(self):
		if not self.machine_image:
			self.machine_image = self.get_latest_ubuntu_image()

	def after_insert(self):
		self.provision()

	def provision(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		client = boto3.client(
			"ec2",
			region_name=self.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)

		response = client.run_instances(
			BlockDeviceMappings=[
				{
					"DeviceName": "/dev/sda1",
					"Ebs": {
						"DeleteOnTermination": True,
						"VolumeSize": self.disk_size,  # This in GB. Fucking AWS!
						"VolumeType": "gp2",
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
		cluster = frappe.get_doc("Cluster", self.cluster)
		client = boto3.client(
			"ssm",
			region_name=self.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)

		return client.get_parameter(
			Name="/aws/service/canonical/ubuntu/server/20.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
		)["Parameter"]["Value"]

	def reboot(self):
		cluster = frappe.get_doc("Cluster", self.cluster)
		client = boto3.client(
			"ec2",
			region_name=self.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)

		client.reboot_instances(InstanceIds=[self.aws_instance_id])

	def increase_disk_size(self, increment=50):
		cluster = frappe.get_doc("Cluster", self.cluster)
		client = boto3.client(
			"ec2",
			region_name=self.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)

		response = client.describe_volumes(
			Filters=[{"Name": "attachment.instance-id", "Values": [self.aws_instance_id]}]
		)
		volume = response["Volumes"][0]
		self.disk_size = volume["Size"] + increment
		client.modify_volume(VolumeId=volume["VolumeId"], Size=self.disk_size)
		self.save()


@frappe.whitelist()
def poll_pending_machines():
	machines = frappe.get_all("Virtual Machine", {"status": "Pending"})
	for machine in machines:
		machine = frappe.get_doc("Virtual Machine", machine.name)
		cluster = frappe.get_doc("Cluster", machine.cluster)
		client = boto3.client(
			"ec2",
			region_name=machine.region,
			aws_access_key_id=cluster.aws_access_key_id,
			aws_secret_access_key=cluster.get_password("aws_secret_access_key"),
		)
		response = client.describe_instances(InstanceIds=[machine.aws_instance_id])

		instance = response["Reservations"][0]["Instances"][0]
		if instance["State"]["Name"] != "pending":
			machine.status = machine.get_status_map()[instance["State"]["Name"]]

			machine.public_ip_address = instance.get("PublicIpAddress")
			machine.private_ip_address = instance.get("PrivateIpAddress")

			machine.public_dns_name = instance.get("PublicDnsName")
			machine.private_dns_name = instance.get("PrivateDnsName")
			machine.save()
