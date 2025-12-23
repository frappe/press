from ipaddress import ip_address
import frappe
import requests
from urllib.parse import urljoin
import json

# state transfer from the orchestrator to the agent
class FrappeComputeClient:
	def __init__(self, orchestrator_base_url, api_key):
		self.base_url = orchestrator_base_url
		self.api_key = api_key

	@frappe.whitelist()
	def create_vm(self, name, image, memory, number_of_vcpus, cloud_init, mac_address, ip_address):
		url = urljoin(self.base_url, f"/api/method/agent.agent.doctype.virtual_machine.virtual_machine.new_vm_from_image")

		params = {
			"name": name,
			"image": image,
			"memory": memory,
			"number_of_vcpus": number_of_vcpus,
			"cloud_init": cloud_init,
			"mac_address": mac_address,
			"ip_address": ip_address,
		}

		response = self._send_request(url, "POST", params)
		doc_dict = json.loads(response.text)
		frappe.throw(f"{str(doc_dict)}")

		return doc_dict

	def stop_vm(self, name):
		url = urljoin(self.base_url, f"/api/v2/document/Virtual%20Machine/{name}/method/stop")
		response = self._send_request(url, "POST", {})

		return response

	def reboot_vm(self, name):
		url = urljoin(self.base_url, f"/api/v2/document/Virtual%20Machine/{name}/method/reboot")
		response = self._send_request(url, "POST", {})

		return response

	def _send_request(self, url, method, data):
		headers = {
    		"Authorization": f"token {self.api_key}",
    		"Content-Type": "application/json"
		}

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

		response = request_func(url, json=data, headers=headers)
		return response

	def get_all_images(self):
		return [{"id": "Ubuntu"}]
