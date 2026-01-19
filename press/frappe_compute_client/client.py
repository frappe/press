import json
from urllib.parse import quote, urljoin

import frappe
import requests


# state transfer from the orchestrator to the agent
class FrappeComputeClient:
	def __init__(self, orchestrator_base_url, api_key):
		self.base_url = orchestrator_base_url
		self.api_key = api_key

	@frappe.whitelist()
	def create_vm(
		self,
		name: str,
		image: str,
		memory: int,
		number_of_vcpus: int,
		cloud_init: str,
		mac_address: str,
		ip_address: str,
		private_network: str,
		ssh_key: str,
	):
		url = urljoin(
			self.base_url, "/api/method/agent.agent.doctype.virtual_machine.virtual_machine.new_vm_from_image"
		)

		params = {
			"name": name,
			"image": image,
			"memory": memory,
			"number_of_vcpus": number_of_vcpus,
			"cloud_init": cloud_init,
			"mac_address": mac_address,
			"ip_address": ip_address,
			"private_network": private_network,
			"ssh_key": ssh_key,
		}

		response = self._send_request(url, "POST", params)
		return json.loads(response.text)

	def start_vm(self, name):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/start"))
		return self._send_request(url, "POST", {})

	def stop_vm(self, name):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/stop"))
		return self._send_request(url, "POST", {})

	def reboot_vm(self, name):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/reboot"))
		return self._send_request(url, "POST", {})

	def attach_volumes(self, name, volumes):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/attach_volumes"))
		return self._send_request(url, "POST", {"volumes": volumes}).json()

	def create_vpc(self, name, cidr_block):
		url = urljoin(self.base_url, quote("/api/v2/document/Private Network/"))
		return self._send_request(url, "POST", {"name": name, "cidr_block": cidr_block}).json()["data"]

	def get_volumes(self, name):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/get_volumes"))
		return self._send_request(url, "GET", {}).json()["data"]

	def _send_request(self, url, method, data):
		headers = {"Authorization": f"token {self.api_key}", "Content-Type": "application/json"}

		method = method.upper()

		match method:
			case "GET":
				request_func = requests.get
			case "POST":
				request_func = requests.post
			case "PUT":
				request_func = requests.put
			case _:
				frappe.throw("Method not implemented yet.")

		return request_func(url, json=data, headers=headers)

	def get_all_images(self):
		return [{"id": "Ubuntu"}]
