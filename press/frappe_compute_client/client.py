from frappe import _dict

from press.frappe_compute_client.frappe_press_client import FrappePressClient


class Client:
	def __init__(self, url, api_key: str, api_secret: str):
		self.client = FrappePressClient(url, api_key=api_key, api_secret=api_secret)

	def validate(self):
		return self.client.get_api("frappe.auth.get_logged_user") == "Administrator"

	def provision_cluster(self, name: str, cidr_block):
		return self.client.post_api(
			"orchestrator.api.private_network.create_private_network",
			params={"name": name, "range": cidr_block},
		)

	def provision_virtual_machine(
		self,
		name: str,
		machine_type: str,
		virtual_machine_image: str,
		root_disk_size: str,
		ssh_key: str,
		cloud_init: str,
		vpc_id: str,
		private_ip_address: str,
		assign_public_ip: bool,
	):
		return self.client.post_api(
			"orchestrator.api.virtual_machine.new",
			params={
				"name": name,
				"machine_type": machine_type,
				"virtual_machine_image": virtual_machine_image,
				"root_disk_size": root_disk_size,
				"ssh_key": ssh_key,
				"cloud_init": cloud_init,
				"private_network": vpc_id,
				"private_ip_address": private_ip_address,
				"assign_public_ip": assign_public_ip,
			},
		)

	def check_machine_availability(self, machine_type, instance_id: str | None = None):
		return self.client.get_api(
			"orchestrator.api.utils.check_machine_availability",
			{"machine_type": machine_type, "instance_id": instance_id},
		)

	def sync_virtual_machine(self, instance_id: str):
		return self.client.get_api("orchestrator.api.virtual_machine.sync", {"instance_id": instance_id})

	def stop_virtual_machine(self, instance_id: str, force: bool = False):
		return self.client.post_api(
			"orchestrator.api.virtual_machine.stop", {"instance_id": instance_id, "force": force}
		)

	def start_virtual_machine(self, instance_id: str):
		return self.client.post_api("orchestrator.api.virtual_machine.start", {"instance_id": instance_id})

	def resize_virtual_machine(self, instance_id: str, machine_type: str, upgrade_disk: bool = False):
		return self.client.post_api(
			"orchestrator.api.virtual_machine.resize",
			{"instance_id": instance_id, "machine_type": machine_type, "resize_disk": upgrade_disk},
		)

	def terminate_virtual_machine(self, instance_id: str):
		return self.client.post_api(
			"orchestrator.api.virtual_machine.terminate", {"instance_id": instance_id}
		)

	def reboot_virtual_machine(self, instance_id: str):
		return self.client.post_api("orchestrator.api.virtual_machine.reboot", {"instance_id": instance_id})

	def remove_public_ip_from_virtual_machine(self, instance_id: str):
		return self.client.post_api(
			"orchestrator.api.virtual_machine.remove_public_ip", {"instance_id": instance_id}
		)

	def create_snapshot(self, instance_id: str):
		return self.client.post_api("orchestrator.api.snapshot.new", {"instance_id": instance_id})

	def sync_snapshot(self, snapshot_id: str):
		return _dict(self.client.get_api("orchestrator.api.snapshot.sync", {"snapshot_id": snapshot_id}))

	def delete_snapshot(self, snapshot_id: str):
		return self.client.post_api("orchestrator.api.snapshot.delete", {"snapshot_id": snapshot_id})

	def create_virtual_machine_image(self, instance_id: str):
		return self.client.post_api(
			"orchestrator.api.virtual_machine_image.new", {"instance_id": instance_id}
		)

	def sync_virtual_machine_image(self, image_id: str):
		return _dict(
			self.client.get_api("orchestrator.api.virtual_machine_image.sync", {"image_id": image_id})
		)

	def increase_disk_size(self, volume_id: str, size: int):
		return self.client.post_api(
			"orchestrator.api.disk.increase_disk_size", {"volume_id": volume_id, "size": size}
		)
