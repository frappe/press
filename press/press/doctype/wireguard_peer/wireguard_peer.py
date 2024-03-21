# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.runner import Ansible
from press.utils import log_error
import ipaddress
import json
import subprocess


class WireguardPeer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allowed_ips: DF.Data | None
		ip: DF.Data | None
		is_wireguard_setup: DF.Check
		peer_config: DF.Code | None
		peer_ip: DF.Data | None
		peer_name: DF.Data
		peer_private_network: DF.Data | None
		private_ip: DF.Data | None
		private_key: DF.Password | None
		public_key: DF.Data | None
		server_name: DF.DynamicLink
		server_type: DF.Literal["Server", "Database Server"]
		status: DF.Literal["Active", "Broken", "Archived"]
		upstream_proxy: DF.Link
		wireguard_network: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.next_ip_address()
		if not self.private_ip:
			self.allowed_ips = self.peer_ip
		else:
			self.allowed_ips = f"{self.peer_ip},{self.peer_private_network}"

	def next_ip_address(self):
		try:
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
					return
				last_ip_address = ipaddress.ip_address(max(ips))
				next_ip_addr = last_ip_address + 1
				while next_ip_addr not in network_address:
					next_ip_addr += 1
				self.peer_ip = str(next_ip_addr)
		except Exception:
			log_error("Wireguard Peer IP Exception", server=self.as_dict())
			frappe.throw("Invalid Wireguard Network")

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
		if not self.private_key or not self.public_key:
			self.private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
			self.public_key = (
				subprocess.check_output([f"echo '{self.private_key}' | wg pubkey"], shell=True)
				.decode()
				.strip()
			)
			self.save()
		proxy = frappe.get_doc("Proxy Server", self.upstream_proxy)
		variables = {
			"wireguard_network": self.peer_ip + "/" + self.wireguard_network.split("/")[1],
			"wireguard_private_key": self.get_password("private_key"),
			"wireguard_port": proxy.wireguard_port,
			"peers": [
				{
					"public_key": proxy.get_password("wireguard_public_key"),
					"endpoint": proxy.name + ":" + str(proxy.wireguard_port),
					"allowed_ips": self.wireguard_network,
					"peer_ip": proxy.name,
				}
			],
		}
		outputText = frappe.render_template(
			"press/doctype/wireguard_peer/templates/wg0.conf", variables, is_path=True
		)
		self.peer_config = outputText
		self.save()
		proxy.reload_wireguard()

	@frappe.whitelist()
	def download_config(self):
		frappe.local.response.filename = f"{self.name}.conf"
		frappe.local.response.filecontent = self.peer_config
		frappe.local.response.type = "download"
