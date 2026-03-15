from frappe.frappeclient import FrappeClient


class Client:
	def __init__(self, url, api_key: str, api_secret: str):
		self.client = FrappeClient(url, api_key=api_key, api_secret=api_secret)

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
			},
		)

	def sync(self, instance_id: str):
		return self.client.get_api("orchestrator.api.virtual_machine.sync", {"instance_id": instance_id})

	def stop(self, instance_id: str, force: bool = False):
		return self.client.post_api(
			"orchestrator.api.virtual_machine.stop", {"instance_id": instance_id, "force": force}
		)

	def start(self, instance_id: str):
		return self.client.post_api("orchestrator.api.virtual_machine.start", {"instance_id": instance_id})

	def terminate(self, instance_id: str):
		return self.client.post_api(
			"orchestrator.api.virtual_machine.terminate", {"instance_id": instance_id}
		)
