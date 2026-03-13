# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import ipaddress
import json
import random
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.runner import Ansible

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.server.server import Server


class OnPremFailover(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app_server: DF.Link
		app_server_wireguard_private_ip: DF.Data | None
		app_server_wireguard_private_key: DF.Password | None
		app_server_wireguard_public_key: DF.Data | None
		benches_base_directory: DF.Data
		database_base_directory: DF.Data
		database_server: DF.Link
		database_server_wireguard_private_ip: DF.Data | None
		database_server_wireguard_private_key: DF.Password | None
		database_server_wireguard_public_key: DF.Data | None
		db_lsyncd_started_on: DF.Datetime | None
		db_lsyncd_stop_at: DF.Datetime | None
		enabled: DF.Check
		is_app_server_failover_setup: DF.Check
		is_app_server_wireguard_setup: DF.Check
		is_db_server_failover_setup: DF.Check
		is_db_server_wireguard_setup: DF.Check
		is_lsyncd_running_for_db: DF.Check
		is_on_prem_server_reachable_from_app_server: DF.Check
		is_on_prem_server_reachable_from_db_server: DF.Check
		is_on_prem_server_ssh_from_app_server_working: DF.Check
		is_on_prem_server_ssh_from_db_server_working: DF.Check
		on_prem_server_wireguard_private_ip: DF.Data | None
		on_prem_server_wireguard_private_key: DF.Password | None
		on_prem_server_wireguard_public_key: DF.Data | None
		wireguard_interface: DF.Data | None
		wireguard_network: DF.Data | None
	# end: auto-generated types

	@property
	def app_server_doc(self) -> Server:
		return frappe.get_cached_doc("Server", self.app_server)

	@property
	def database_server_doc(self) -> DatabaseServer:
		return frappe.get_cached_doc("Database Server", self.database_server)

	def before_insert(self):
		self._set_default_wireguard_network()
		self._set_app_server_configuration()
		self._set_database_server_configuration()
		self._set_on_prem_server_configuration()

	@frappe.whitelist()
	def setup_wireguard_on_app_server(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_wireguard_on_app_server", timeout=300)

	def _setup_wireguard_on_app_server(self):
		peers = [
			{
				"public_key": self.database_server_wireguard_public_key,
				"allowed_ips": f"{self.database_server_wireguard_private_ip}/32",
				"peer_ip": self.database_server_doc.ip or self.database_server_doc.private_ip,
			},
			{
				"public_key": self.on_prem_server_wireguard_public_key,
				"allowed_ips": f"{self.on_prem_server_wireguard_private_ip}/32",
				"peer_ip": "",
			},
		]

		ansible = Ansible(
			playbook="wireguard.yml",
			server=self.app_server_doc,
			variables={
				"wireguard_port": 51820,
				"interface_id": self.wireguard_interface or "eth0",
				"wireguard_network": f"{self.app_server_wireguard_private_ip}/{self.wireguard_network.split('/')[1]}",
				"wireguard_private_key": self.get_password("app_server_wireguard_private_key"),
				"wireguard_public_key": self.app_server_wireguard_public_key,
				"peers": json.dumps(peers),
			},
		)
		play = ansible.run()
		if play.status == "Success":
			self.is_app_server_wireguard_setup = True
			self.save()

	@frappe.whitelist()
	def setup_wireguard_on_database_server(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_wireguard_on_database_server", timeout=300)

	def _setup_wireguard_on_database_server(self):
		peers = [
			{
				"public_key": self.app_server_wireguard_public_key,
				"allowed_ips": f"{self.app_server_wireguard_private_ip}/32",
				"peer_ip": self.app_server_doc.ip or self.app_server_doc.private_ip,
			},
			{
				"public_key": self.on_prem_server_wireguard_public_key,
				"allowed_ips": f"{self.on_prem_server_wireguard_private_ip}/32",
				"peer_ip": "",
			},
		]

		ansible = Ansible(
			playbook="wireguard.yml",
			server=self.database_server_doc,
			variables={
				"wireguard_port": 51820,
				"interface_id": self.wireguard_interface or "eth0",
				"wireguard_network": f"{self.database_server_wireguard_private_ip}/{self.wireguard_network.split('/')[1]}",
				"wireguard_private_key": self.get_password("database_server_wireguard_private_key"),
				"wireguard_public_key": self.database_server_wireguard_public_key,
				"peers": json.dumps(peers),
			},
		)
		play = ansible.run()
		if play.status == "Success":
			self.is_db_server_wireguard_setup = True
			self.save()

	@frappe.whitelist()
	def view_on_prem_server_wireguard_config(self):
		config = self.generate_on_prem_server_wireguard_config()
		message = f"""
			<h4>Step 1: Install WireGuard</h4>
			<p>Run the following command on your on-premise server to install WireGuard:</p>
			<pre>sudo apt update && sudo apt install -y wireguard resolvconf</pre>

			<h4>Step 2: Save the Configuration</h4>
			<p>Create a new configuration file at <code>/etc/wireguard/wg0.conf</code> and paste the following content:</p>
			<pre>{config}</pre>

			<h4>Step 3: Enable and Start WireGuard</h4>
			<p>Run the following commands to start the WireGuard interface and enable it on boot:</p>
			<pre>sudo systemctl enable --now wg-quick@wg0</pre>

			<h4>Step 4: Verify the Connection</h4>
			<p>You can check the status of your WireGuard connection with:</p>
			<pre>sudo wg show</pre>
		"""
		frappe.msgprint(message, title="On-Premise WireGuard Setup Guide", wide=True)

	@frappe.whitelist()
	def generate_on_prem_server_wireguard_config(self):
		return f"""[Interface]
Address = {self.on_prem_server_wireguard_private_ip}/{self.wireguard_network.split("/")[1]}
PrivateKey = {self.get_password("on_prem_server_wireguard_private_key")}

[Peer]
# App Server
PublicKey = {self.app_server_wireguard_public_key}
Endpoint = {self.app_server_doc.ip or self.app_server_doc.private_ip}:51820
AllowedIPs = {self.app_server_wireguard_private_ip}/32
PersistentKeepalive = 25

[Peer]
# Database Server
PublicKey = {self.database_server_wireguard_public_key}
Endpoint = {self.database_server_doc.ip or self.database_server_doc.private_ip}:51820
AllowedIPs = {self.database_server_wireguard_private_ip}/32
PersistentKeepalive = 25
"""

	@frappe.whitelist()
	def view_on_prem_server_ssh_authorized_keys(self):
		message = f"""
		<h4>Step 1: Add Authorized Keys</h4>
		<p>Run the following command on your on-premise server to add the authorized_keys:</p>
		<pre>sudo echo '{self.generate_ssh_authorized_keys_to_add()}' >> /root/.ssh/authorized_keys</pre>
		"""
		frappe.msgprint(message, title="On-Premise SSH Authorized Keys Setup Guide", wide=True)

	@frappe.whitelist()
	def generate_ssh_authorized_keys_to_add(self):
		# Add authorized_keys to on-premise server
		keys = [
			self.app_server_doc.root_public_key,
			self.app_server_doc.frappe_public_key,
			self.database_server_doc.root_public_key,
			self.database_server_doc.frappe_public_key,
		]

		valid_keys = [key for key in keys if key]
		return "\n".join(valid_keys)

	@frappe.whitelist()
	def test_connectivity_to_on_premise_server(self):
		frappe.enqueue_doc(self.doctype, self.name, "check_connectivity_to_on_premise_server", timeout=300)

	def check_connectivity_to_on_premise_server(self):
		for server_doc in [self.app_server_doc, self.database_server_doc]:
			ansible = Ansible(
				playbook="ping_on_prem.yml",
				server=server_doc,
				variables={
					"on_prem_ip": self.on_prem_server_wireguard_private_ip,
				},
			)
			play = ansible.run()

			ping_task = frappe.get_all(
				"Ansible Task",
				filters={"play": play.name, "task": "Ping on-premise server over WireGuard"},
				limit=1,
				pluck="status",
			)
			ssh_task = frappe.get_all(
				"Ansible Task",
				filters={"play": play.name, "task": "Verify SSH connectivity to on-premise server"},
				limit=1,
				pluck="status",
			)

			is_ping_reachable = bool(ping_task and ping_task[0] == "Success")
			is_ssh_reachable = bool(ssh_task and ssh_task[0] == "Success")

			if server_doc.name == self.app_server:
				self.is_on_prem_server_reachable_from_app_server = is_ping_reachable
				self.is_on_prem_server_ssh_from_app_server_working = is_ssh_reachable
			else:
				self.is_on_prem_server_reachable_from_db_server = is_ping_reachable
				self.is_on_prem_server_ssh_from_db_server_working = is_ssh_reachable

		self.save()

	def setup_replica(self):
		"""
		First Lsyncd for estimated time
		Stop Primary DB
		DB Flush + Final Rsync
		Start Primary DB -- do always
		Start Replica Setup
		"""
		pass

	@frappe.whitelist()
	def setup_db_lsync_for_initial_sync(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_db_lsync_for_initial_sync", timeout=300)

	def _setup_db_lsync_for_initial_sync(self):
		# Stop replica container on the on-prem
		if self.is_lsyncd_running_for_db:
			return

		ansible = Ansible(
			playbook="setup_on_prem_failover_db_lsync.yml",
			server=self.database_server_doc,
			variables={
				"on_prem_ip": self.on_prem_server_wireguard_private_ip,
				"database_base_directory": self.database_base_directory,
			},
		)
		play = ansible.run()

		if play.status == "Success":
			self.is_lsyncd_running_for_db = True
			self.db_lsyncd_started_on = frappe.utils.now_datetime()
			# TODO: Perform network testing and setup db_lsyncd_stop_at accordingly
			# Else, by default assume 5 MB/s transfer speed
			self.db_lsyncd_stop_at = frappe.utils.add_to_date(self.db_lsyncd_started_on, hour=1)
			self.save()

	@frappe.whitelist()
	def setup_db_rsync_for_final_sync(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_db_rsync_for_final_sync", timeout=3600)

	def _setup_db_rsync_for_final_sync(self):
		ansible = Ansible(
			playbook="setup_on_prem_failover_db_final_sync.yml",
			server=self.database_server_doc,
			variables={
				"on_prem_ip": self.on_prem_server_wireguard_private_ip,
				"database_base_directory": self.database_base_directory,
				"mariadb_bind_address": "0.0.0.0",
			},
		)
		play = ansible.run()

		if play.status != "Success":
			frappe.throw("Failed to perform the final database sync.")

	@frappe.whitelist()
	def setup_replica_on_prem(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_replica_on_prem", timeout=3600)

	def _setup_replica_on_prem(self):
		ansible = Ansible(
			playbook="setup_on_prem_failover_replica.yml",
			server=self.database_server_doc,
			variables={
				"on_prem_ip": self.on_prem_server_wireguard_private_ip,
				"database_base_directory": self.database_base_directory,
				"mariadb_root_password": self.database_server_doc.get_password("mariadb_root_password"),
				"primary_private_ip": self.database_server_wireguard_private_ip,
				"primary_db_port": 3306,
				"mariadb_bind_address": "0.0.0.0",
			},
		)
		play = ansible.run()

		if play.status != "Success":
			frappe.throw("Failed to setup replica on the on-premise server.")

	# Internal methods

	def _set_default_wireguard_network(self):
		if self.wireguard_network:
			ipaddress.IPv4Network(self.wireguard_network)  # validate the network
			return

		self.wireguard_network = ipaddress.IPv4Network(f"172.16.{random.randint(0, 255)}.0/24").with_prefixlen

	def _set_app_server_configuration(self):
		self.app_server_wireguard_private_ip = self._add_value_in_ip_address(self.wireguard_network, 1)
		self.app_server_wireguard_private_key, self.app_server_wireguard_public_key = (
			self._generate_wireguard_keys()
		)

	def _set_database_server_configuration(self):
		self.database_server_wireguard_private_ip = self._add_value_in_ip_address(self.wireguard_network, 2)
		self.database_server_wireguard_private_key, self.database_server_wireguard_public_key = (
			self._generate_wireguard_keys()
		)

	def _set_on_prem_server_configuration(self):
		self.on_prem_server_wireguard_private_ip = self._add_value_in_ip_address(self.wireguard_network, 3)
		self.on_prem_server_wireguard_private_key, self.on_prem_server_wireguard_public_key = (
			self._generate_wireguard_keys()
		)

	def _add_value_in_ip_address(self, ip: str, value: int) -> str:
		ip_obj = ipaddress.IPv4Address(ip.split("/")[0])
		new_ip = ip_obj + value
		return str(new_ip)

	def _generate_wireguard_keys(self) -> tuple[str, str]:
		import subprocess

		private_key = subprocess.check_output(["wg", "genkey"]).strip()
		public_key = subprocess.check_output(["wg", "pubkey"], input=private_key).strip()

		return private_key.decode(), public_key.decode()
