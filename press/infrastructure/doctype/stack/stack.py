# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
import shlex
import subprocess
import tempfile


class Stack(Document):
	def validate(self):
		if self.compose and not self.services:
			self.create_services_from_compose()

		if not self.vxlan_id:
			# Use the last 3 bytes of the name as the VXLAN ID
			self.vxlan_id = int(self.name[-6:], 16)
		service_volumes = set()
		for service in self.services:
			service = frappe.get_doc("Service", service.service)
			service_volumes |= set(mount.volume for mount in service.mounts)

		stack_volumes = set(volume.volume for volume in self.volumes)
		if service_volumes != stack_volumes:
			self.volumes = []
			for volume in service_volumes:
				self.append("volumes", {"volume": volume})

	@frappe.whitelist()
	def deploy(self):
		deployment = frappe.new_doc("Deployment")
		deployment.stack = self.name
		deployment.insert()

	def on_trash(self):
		deployments = frappe.get_all("Deployment", filters={"stack": self.name})
		for deployment in deployments:
			frappe.get_doc("Deployment", deployment.name).delete()

	@classmethod
	def parse_compose(kls, compose):
		loaded = {}
		with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
			file.write(compose)
			file.flush()
			command = f"docker compose -f {file.name} config --format json"
			loaded = json.loads(subprocess.check_output(shlex.split(command)).decode())

		parsed = []
		for service_name, service in loaded["services"].items():
			short = service["image"].split(":")[0]
			image = short
			if "/" not in image:
				image = f"library/{image}"
			if "." not in image.split("/")[0]:
				image = f"docker.io/{image}"

			parsed_service = frappe._dict(
				{
					"image": image,
					"title": service_name,
					"tag": service["image"].split(":")[1],
				}
			)
			# for port in service.get("expose", []):
			# 	parsed_service.setdefault("ports", []).append({"port": port})

			for port in service.get("ports", []):
				parsed_service.setdefault("ports", []).append(
					{"port": port["published"], "protocol": port["protocol"]}
				)

			for key, value in service.get("environment", {}).items():
				parsed_service.setdefault("environment_variables", []).append(
					{"key": key, "required": True, "default_value": value}
				)

			for volume in service.get("volumes", []):
				if volume["type"] == "volume":
					parsed_service.setdefault("mounts", []).append(
						{"volume": volume["source"], "source": "data", "destination": volume["target"]}
					)

			parsed.append(parsed_service)
		return parsed

	def create_services_from_compose(self):
		parsed = self.__class__.parse_compose(self.compose)
		for service in parsed:
			service.doctype = "Service"
			doc = frappe.get_doc(service)
			doc.insert()
			self.append("services", {"service": doc.name})

	@frappe.whitelist()
	def deploy_information(self):
		out = frappe._dict(update_available=False)

		last_deployment = frappe.get_all("Deployment", {"stack": self.name}, "*")
		if last_deployment:
			last_deployment = last_deployment[0]
			out.update_available = False
		else:
			out.update_available = True

		out.last_deploy = last_deployment
		out.deploy_in_progress = bool(
			last_deployment and last_deployment.status in ("Pending", "Running")
		)
		return out
