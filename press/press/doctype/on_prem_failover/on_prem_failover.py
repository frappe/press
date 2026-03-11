# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import ipaddress
import random

from frappe.model.document import Document


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
		enabled: DF.Check
		is_app_server_failover_setup: DF.Check
		is_db_server_failover_setup: DF.Check
		on_prem_server_wireguard_private_ip: DF.Data | None
		on_prem_server_wireguard_private_key: DF.Password | None
		on_prem_server_wireguard_public_key: DF.Data | None
		wireguard_interface: DF.Data | None
		wireguard_network: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		self.set_default_wireguard_network()
		self.set_app_server_configuration()
		self.set_database_server_configuration()
		self.set_on_prem_server_configuration()

	def set_default_wireguard_network(self):
		if self.wireguard_network:
			ipaddress.IPv4Network(self.wireguard_network)  # validate the network
			return

		self.wireguard_network = ipaddress.IPv4Network(f"172.16.{random.randint(0, 255)}.0/24").with_prefixlen

	def set_app_server_configuration(self):
		self.app_server_wireguard_private_ip = self._add_value_in_ip_address(self.wireguard_network, 1)
		self.app_server_wireguard_private_key, self.app_server_wireguard_public_key = (
			self._generate_wireguard_keys()
		)

	def set_database_server_configuration(self):
		self.database_server_wireguard_private_ip = self._add_value_in_ip_address(self.wireguard_network, 2)
		self.database_server_wireguard_private_key, self.database_server_wireguard_public_key = (
			self._generate_wireguard_keys()
		)

	def set_on_prem_server_configuration(self):
		self.on_prem_server_wireguard_private_ip = self._add_value_in_ip_address(self.wireguard_network, 3)
		self.on_prem_server_wireguard_private_key, self.on_prem_server_wireguard_public_key = (
			self._generate_wireguard_keys()
		)

	# Internal methods

	def _add_value_in_ip_address(self, ip: str, value: int) -> str:
		ip_obj = ipaddress.IPv4Address(ip.split("/")[0])
		new_ip = ip_obj + value
		return str(new_ip)

	def _generate_wireguard_keys(self) -> tuple[str, str]:
		import subprocess

		private_key = subprocess.check_output(["wg", "genkey"]).strip()
		public_key = subprocess.check_output(["wg", "pubkey"], input=private_key).strip()

		return private_key.decode(), public_key.decode()
