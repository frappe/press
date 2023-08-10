# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.runner import Ansible
from press.utils import log_error
import ipaddress
import json


class WireguardPeer(Document):
	def after_insert(self):
		self.next_ip_address()
		self.peer_config = self.generate_config()

	def validate(self):
		self.allowed_ips = f"{self.peer_ip},{self.peer_private_network}"

	def next_ip_address(self):
		if self.is_new() and not self.peer_ip:
			network_address = ipaddress.ip_network(self.wireguard_network)
			ips = frappe.get_list(
				"Wireguard Peer",
				filters={"wireguard_network": self.wireguard_network},
				pluck="peer_ip",
				fields=["peer_ip"],
			)
			if not ips:
				self.peer_ip = str(network_address[2])
				self.save()
				return
			last_ip_address = ipaddress.ip_address(max(ips))
			next_ip_addr = last_ip_address + 1
			while next_ip_addr not in network_address:
				next_ip_addr += 1
			self.peer_ip = next_ip_addr

	@frappe.whitelist()
	def setup_wireguard(self):
		frappe.enqueue_doc("Wireguard Peer", self.name, "_setup_peer_wg")

	@frappe.whitelist()
	def ping_peer(self):
		try:
			ansible = Ansible(
				playbook="ping.yml",
				server=self,
			)
			play = ansible.run()
			if play.status == "Success":
				if not self.peer_private_network:
					self.fetch_peer_private_network(play)
		except Exception:
			log_error("Server Ping Exception", server=self.as_dict())

	@frappe.whitelist()
	def fetch_peer_private_network(self, play=None):
		if not play:
			play = frappe.get_last_doc(
				"Ansible Play", {"status": "Success", "server": self.name, "play": "Ping Server"}
			)
		res = frappe.get_last_doc(
			"Ansible Task", {"status": "Success", "play": play.name, "task": "Gather Facts"}
		).result
		facts = json.loads(res)["ansible_facts"]
		self.private_ip = facts["eth1"]["ipv4"]["address"]
		self.peer_private_network = str(
			ipaddress.IPv4Network(
				f'{facts["eth1"]["ipv4"]["address"]}/{facts["eth1"]["ipv4"]["netmask"]}',
				strict=False,
			)
		)
		self.save()

	def _setup_peer_wg(self):
		proxy = frappe.get_doc("Proxy Server", self.upstream_proxy)
		try:
			ansible = Ansible(
				playbook="wireguard.yml",
				server=self,
				variables={
					"wireguard_port": proxy.wireguard_port,
					"interface_id": proxy.private_ip_interface_id,
					"wireguard_network": self.peer_ip + "/" + self.wireguard_network.split("/")[1],
					"wireguard_private_key": self.get_password("private_key")
					if self.private_key
					else False,
					"wireguard_public_key": self.get_password("public_key")
					if self.public_key
					else False,
					"peers": json.dumps(
						[
							{
								"public_key": proxy.get_password("wireguard_public_key"),
								"allowed_ips": self.wireguard_network,
								"peer_ip": proxy.name,
							}
						]
					),
				},
			)
			play = ansible.run()
			if play.status == "Success":
				self.reload()
				self.is_wireguard_setup = True
				try:
					if not self.private_key and not self.public_key:
						self.private_key = frappe.get_doc(
							"Ansible Task", {"play": play.name, "task": "Generate Wireguard Private Key"}
						).output
						self.public_key = frappe.get_doc(
							"Ansible Task", {"play": play.name, "task": "Generate Wireguard Public Key"}
						).output
				except Exception:
					log_error("Wireguard Key Save error", server=self.as_dict())
				if not self.peer_private_network:
					self.peer_private_network = frappe.get_doc(
						"Ansible Task", {"play": play.name, "task": "Get Subnet Mask of eth1"}
					).output
				self.save()
				proxy.reload_wireguard()
		except Exception:
			log_error("Wireguard Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def generate_config(self):
		proxy = frappe.get_doc("Proxy Server", self.upstream_proxy)
		variables = {
			"wireguard_network": self.peer_ip + "/" + self.wireguard_network.split("/")[1],
			"wireguard_private_key": "",
			"wireguard_port": proxy.wireguard_port,
			"peers": [
				{
					"public_key": proxy.get_password("wireguard_public_key"),
					"allowed_ips": self.wireguard_network,
					"peer_ip": proxy.name,
				}
			],
		}
		outputText = frappe.render_template(
			"press/doctype/wireguard_peer/templates/wg0.conf", variables, is_path=True
		)
		return outputText

	@frappe.whitelist()
	def download_config(self):
		frappe.local.response.filename = f"{self.name}.conf"
		frappe.local.response.filecontent = self.peer_config
		frappe.local.response.type = "download"
