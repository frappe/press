# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import ipaddress
import json
import random
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date

from press.runner import Ansible

if TYPE_CHECKING:
	from press.press.doctype.cluster.cluster import Cluster
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

WIREGUARD_DEFAULT_PORT = 51820


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
		cluster: DF.Link
		database_base_directory: DF.Data
		database_server: DF.Link
		database_server_wireguard_private_ip: DF.Data | None
		database_server_wireguard_private_key: DF.Password | None
		database_server_wireguard_public_key: DF.Data | None
		db_lsyncd_started_on: DF.Datetime | None
		db_lsyncd_stop_at: DF.Datetime | None
		enabled: DF.Check
		firewall_id: DF.Data | None
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
		team: DF.Link
		wireguard_network: DF.Data | None
		wireguard_port: DF.Int
	# end: auto-generated types

	@property
	def app_server_doc(self) -> Server:
		return frappe.get_cached_doc("Server", self.app_server)

	@property
	def database_server_doc(self) -> DatabaseServer:
		return frappe.get_cached_doc("Database Server", self.database_server)

	def before_insert(self):
		self._set_default_wireguard_port()
		self._set_default_wireguard_network()
		self._set_app_server_configuration()
		self._set_database_server_configuration()
		self._set_on_prem_server_configuration()

	def after_insert(self):
		self._create_firewall()

	def on_update(self):
		if self.has_value_changed("enabled") and not self.enabled:
			self.is_app_server_wireguard_setup = False
			self.is_db_server_wireguard_setup = False
			self.is_app_server_failover_setup = False
			self.is_db_server_failover_setup = False
			self.is_on_prem_server_reachable_from_app_server = False
			self.is_on_prem_server_ssh_from_app_server_working = False
			self.is_on_prem_server_reachable_from_db_server = False
			self.is_on_prem_server_ssh_from_db_server_working = False
			self.is_lsyncd_running_for_db = False
			self.db_lsyncd_started_on = None
			self.db_lsyncd_stop_at = None
			self.save()

	def setup_wireguard_on_app_server(self):
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
		else:
			frappe.throw(
				"Failed to setup WireGuard on the App Server. Please check the Ansible playbook execution logs for more details."
			)

	def setup_wireguard_on_database_server(self):
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
		else:
			frappe.throw(
				"Failed to setup WireGuard on the Database Server. Please check the Ansible playbook execution logs for more details."
			)

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
		keys = []

		def _find_root_public_key(server_doc):
			# If the server already has a root public key, return it directly
			if server_doc.root_public_key:
				return server_doc.root_public_key

			# If server was created from a VM, it might not have a root key
			# so check the associated Virtual Machine
			vm_name = server_doc.virtual_machine
			if not vm_name:
				return None

			vm = frappe.get_doc("Virtual Machine", vm_name)

			# If the VM was created from a Virtual Machine Image (VMI),
			# trace back to the original VM used to create that image
			vmi_name = vm.virtual_machine_image
			if not vmi_name:
				return None

			vm_of_vmi = frappe.get_value("Virtual Machine Image", vmi_name, "virtual_machine")
			if not vm_of_vmi:
				return None

			# Fetch the original VM and its server
			vm = frappe.get_doc("Virtual Machine", vm_of_vmi)
			server = vm.get_server()

			# Return the root public key if available
			return getattr(server, "root_public_key", None) if server else None

		if key := _find_root_public_key(self.app_server_doc):
			keys.append(key)

		if key := _find_root_public_key(self.database_server_doc):
			keys.append(key)

		valid_keys = [key + " fc-dr" for key in keys if key]
		return "\n".join(valid_keys)

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

	@frappe.whitelist()
	def setup_failover(self):
		server = self.app_server_doc
		frappe.get_doc(
			{
				"doctype": "Press Job",
				"job_type": "Setup On-Prem Failover",
				"server_type": server.doctype,
				"server": server.name,
				"virtual_machine": server.virtual_machine,
				"arguments": json.dumps(
					{
						"failover": self.name,
					},
					indent=2,
					sort_keys=True,
				),
			}
		).insert(ignore_permissions=True)

	@frappe.whitelist()
	def teardown_failover(self):
		server = self.app_server_doc
		frappe.get_doc(
			{
				"doctype": "Press Job",
				"job_type": "Remove On-Prem Failover",
				"server_type": server.doctype,
				"server": server.name,
				"virtual_machine": server.virtual_machine,
				"arguments": json.dumps(
					{
						"failover": self.name,
					},
					indent=2,
					sort_keys=True,
				),
			}
		).insert(ignore_permissions=True)

	@frappe.whitelist()
	def setup_db_lsync_for_initial_sync(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_db_lsync_for_initial_sync", timeout=1800, queue="long"
		)

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
			self.reload()

			self.is_lsyncd_running_for_db = True
			self.db_lsyncd_started_on = frappe.utils.now_datetime()

			# TODO: Perform network testing and setup db_lsyncd_stop_at accordingly
			try:
				usage: dict = self.database_server_doc.get_storage_usage()
				disk_usage = usage.get("disk_used", 0)
				# Assuming 5 MB/s transfer speed for estimation
				estimated_seconds = disk_usage / (5 * 1024 * 1024)
				self.db_lsyncd_stop_at = add_to_date(self.db_lsyncd_started_on, seconds=estimated_seconds)
			except Exception:
				self.db_lsyncd_stop_at = add_to_date(self.db_lsyncd_started_on, hours=1)

			self.save()
		else:
			frappe.throw(
				"Failed to setup lsyncd for initial database synchronization. Please check the Ansible playbook execution logs for more details."
			)

	def setup_db_rsync_for_final_sync(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_db_rsync_for_final_sync", timeout=3600, queue="long"
		)

	def _setup_db_rsync_for_final_sync(self):
		ansible = Ansible(
			playbook="setup_on_prem_failover_db_final_sync.yml",
			server=self.database_server_doc,
			variables={
				"on_prem_ip": self.on_prem_server_wireguard_private_ip,
				"database_base_directory": self.database_base_directory,
				"mariadb_bind_address": "0.0.0.0",
				"mariadb_root_password": self.database_server_doc.get_password("mariadb_root_password"),
			},
		)
		play = ansible.run()

		if play.status != "Success":
			frappe.throw("Failed to perform the final database sync.")

	def setup_and_configure_database_replica(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_and_configure_database_replica", timeout=3600, queue="long"
		)

	def _setup_and_configure_database_replica(self):
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

	def setup_app_server_replica(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_app_server_replica", timeout=3600, queue="long")

	def _setup_app_server_replica(self):
		ansible = Ansible(
			playbook="setup_on_prem_failover_app_sync.yml",
			server=self.app_server_doc,
			variables={
				"on_prem_ip": self.on_prem_server_wireguard_private_ip,
				"app_server_base_directory": self.benches_base_directory,
			},
		)
		play = ansible.run()

		if play.status != "Success":
			frappe.throw("Failed to setup App Server replica synchronization on the on-premise server.")

	def stop_replication_from_app_server(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_stop_replication_from_app_server", timeout=1800, queue="long"
		)

	def _stop_replication_from_app_server(self):
		ansible = Ansible(
			playbook="stop_on_prem_failover_app_replication.yml",
			server=self.app_server_doc,
			variables={},
		)
		play = ansible.run()
		if play.status != "Success":
			frappe.throw("Failed to stop replication on the App Server.")

	def stop_replication_from_db_server(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_stop_replication_from_db_server", timeout=300, queue="long"
		)

	def _stop_replication_from_db_server(self):
		ansible = Ansible(
			playbook="stop_on_prem_failover_db_replication.yml",
			server=self.database_server_doc,
			variables={},
		)
		play = ansible.run()
		if play.status != "Success":
			frappe.throw("Failed to stop replication on the Database Server.")

	# Internal methods

	def _set_default_wireguard_port(self):
		if not self.wireguard_port:
			self.wireguard_port = WIREGUARD_DEFAULT_PORT

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

	def _create_firewall(self):
		cluster: Cluster = frappe.get_doc("Cluster", self.cluster)
		self.firewall_id = cluster.create_firewall(
			rules=[[self.wireguard_port, "udp"]],
			is_ingress=True,
			description=f"Firewall for On-Prem Failover {self.name}",
		)
		self.save()

	def delete_firewall(self):
		if not self.firewall_id:
			return
		cluster: Cluster = frappe.get_doc("Cluster", self.cluster)
		cluster.delete_firewall(self.firewall_id)
		self.firewall_id = None
		self.save()

	def add_app_server_to_firewall(self):
		if not self.firewall_id:
			return
		vm: VirtualMachine = frappe.get_doc("Virtual Machine", self.app_server_doc.virtual_machine)
		vm.attach_to_firewall(self.firewall_id)

	def remove_app_server_from_firewall(self):
		if not self.firewall_id:
			return
		vm: VirtualMachine = frappe.get_doc("Virtual Machine", self.app_server_doc.virtual_machine)
		vm.detach_from_firewall(self.firewall_id)

	def add_db_server_to_firewall(self):
		if not self.firewall_id:
			return
		vm: VirtualMachine = frappe.get_doc("Virtual Machine", self.database_server_doc.virtual_machine)
		vm.attach_to_firewall(self.firewall_id)

	def remove_db_server_from_firewall(self):
		if not self.firewall_id:
			return
		vm: VirtualMachine = frappe.get_doc("Virtual Machine", self.database_server_doc.virtual_machine)
		vm.detach_from_firewall(self.firewall_id)

	def _add_value_in_ip_address(self, ip: str, value: int) -> str:
		ip_obj = ipaddress.IPv4Address(ip.split("/")[0])
		new_ip = ip_obj + value
		return str(new_ip)

	def _generate_wireguard_keys(self) -> tuple[str, str]:
		import subprocess

		private_key = subprocess.check_output(["wg", "genkey"]).strip()
		public_key = subprocess.check_output(["wg", "pubkey"], input=private_key).strip()

		return private_key.decode(), public_key.decode()
