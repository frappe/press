# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class NFSServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.mount_enabled_server.mount_enabled_server import MountEnabledServer

		agent_password: DF.Password | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		hostname: DF.Data
		ip: DF.Data
		is_server_prepared: DF.Check
		is_server_setup: DF.Check
		monitoring_password: DF.Password | None
		mount_enabled_servers: DF.Table[MountEnabledServer]
		private_ip: DF.Data
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		root_public_key: DF.Code | None
		ssh_port: DF.Int
		ssh_user: DF.Data | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		tls_certificate_renewal_failed: DF.Check
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def _setup_server(self):
		try:
			ansible = Ansible(
				playbook="nfs_server.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Agent Sentry Setup Exception", server=self.as_dict())
