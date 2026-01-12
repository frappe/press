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
		machine_type: str,
		private_ip_address: str,
		private_network: str,
		ssh_key: str,
		cloud_init: str,
		root_disk_size: int,
	):
		url = urljoin(
			self.base_url, "/api/method/agent.agent.doctype.virtual_machine.virtual_machine.new_vm_from_image"
		)

		params = {
			"name": name,
			"image": image,
			"machine_type": machine_type,
			"private_ip_address": private_ip_address,
			"private_network": private_network,
			"ssh_key": ssh_key,
			"cloud_init": cloud_init,
			"root_disk_size": root_disk_size,
		}

		response = self._send_request(url, "POST", params)
		data = json.loads(response.text)
		if "message" in data:
			return data["message"]
		raise APIError(data)

	def start_vm(self, name):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/start"))
		return self._send_request(url, "POST", {})

	def stop_vm(self, name, force):
		if force:
			url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/stop"))
		else:
			url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/shutdown"))
		return self._send_request(url, "POST", {})

	def reboot_vm(self, name):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/reboot"))
		return self._send_request(url, "POST", {})

	def terminate_vm(self, name):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}"))
		return self._send_request(url, "DELETE", {})

	def attach_volumes(self, name, volumes):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/attach_volumes"))
		return self._send_request(url, "POST", {"volumes": volumes}).json()

	def create_vpc(self, name, cidr_block):
		url = urljoin(self.base_url, quote("/api/v2/document/Private Network/"))
		return self._send_request(url, "POST", {"name": name, "cidr_block": cidr_block}).json()["data"]

	def get_volumes(self, name):
		url = urljoin(self.base_url, quote(f"/api/v2/document/Virtual Machine/{name}/method/get_volumes"))
		return self._send_request(url, "GET", {}).json()["data"]

	def get_vm_info(self, instance_id):
		url = urljoin(
			self.base_url,
			quote(
				"/api/method/agent.agent.doctype.virtual_machine.virtual_machine.get_vm_details_from_instance_id"
			),
		)
		resp = self._send_request(url, "GET", {"instance_id": instance_id}).json()
		if "message" not in resp:
			if "exc_type" in resp:
				raise APIError(resp, resp["exc_type"])
			raise APIError(resp)
		return frappe._dict(resp["message"])

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
			case "DELETE":
				request_func = requests.delete
			case _:
				frappe.throw("Method not implemented yet.")

		if method == "GET":
			return request_func(url, params=data, headers=headers)

		return request_func(url, json=data, headers=headers)

	def get_all_images(self):
		return [{"id": "Ubuntu"}]


class APIError(Exception):
	def __init__(self, message, exception_code=None):
		super().__init__(message)
		self.exception_code = exception_code
