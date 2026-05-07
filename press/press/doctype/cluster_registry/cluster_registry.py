# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# Cluster registries are utilizing harbor and therefore require
# A seperate controller model for them to address the configs along with
# Cleanup related API calls to Harbor
import typing

import frappe

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.tls_certificate.tls_certificate import TLSCertificate


class ClusterRegistry(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		build_server: DF.Link | None
		cluster: DF.Link | None
		domain: DF.Link | None
		hostname: DF.Data | None
		ip: DF.Data | None
		is_setup: DF.Check
		private_ip: DF.Data | None
		provider: DF.Data | None
		status: DF.Literal["GC", "Active", "Broken", "Pending"]
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_cluster()

	def _setup_cluster_registry(self):
		tls_certificate: TLSCertificate = frappe.get_doc(
			"TLS Certificate", {"wildcard": True, "status": "Active", "domain": self.domain}
		)

		try:
			ansible = Ansible(
				playbook="cluster_registry.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"harbor_hostname": self.name,
					"fullchain": tls_certificate.full_chain,
					"private_key": tls_certificate.private_key,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_setup = True
			else:
				self.status = "Broken"
		except Exception as e:
			self.status = "Broken"
			log_error(f"Error while provisioning cluster registry {e}")
		finally:
			self.save()

	def setup_server(self):
		self.create_dns_record()
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_setup_cluster_registry",
			queue="long",
			timeout=3600,
		)
