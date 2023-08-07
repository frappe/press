# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt


import frappe
from press.runner import Ansible
from press.utils import log_error

from press.press.doctype.server.server import BaseServer


class Node(BaseServer):
	@frappe.whitelist()
	def setup(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_setup", queue="long", timeout=2400)

	def _setup(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		certificate = self.get_certificate()
		log_server, kibana_password = self.get_log_server()

		try:
			ansible = Ansible(
				playbook="node.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"server": self.name,
					"private_ip": self.private_ip,
					"workers": "2",
					"agent_password": agent_password,
					"agent_repository_url": agent_repository_url,
					"monitoring_password": self.get_monitoring_password(),
					"certificate_private_key": certificate.private_key,
					"certificate_full_chain": certificate.full_chain,
					"certificate_intermediate_chain": certificate.intermediate_chain,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Server Setup Exception", server=self.as_dict())
		self.save()
