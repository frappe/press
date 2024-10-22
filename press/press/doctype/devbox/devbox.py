# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.agent import Agent

if TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


class Devbox(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_site_to_upstream: DF.Check
		cpu_cores: DF.Int
		disk_mb: DF.Int
		domain: DF.Link | None
		initialized: DF.Check
		ram: DF.Int
		server: DF.Link
		status: DF.Literal["Pending", "Starting", "Paused", "Running", "Archived", "Exited"]
		subdomain: DF.Data
	# end: auto-generated types
	pass

	def _get_devbox_name(self, subdomain: str):
		"""Get full devbox domain name given subdomain."""
		if not self.domain:
			self.domain = frappe.db.get_single_value("Press Settings", "domain")
		return f"{subdomain}.{self.domain}"

	def autoname(self):
		self.name = self._get_devbox_name(subdomain=self.subdomain)

	@frappe.whitelist()
	def get_available_cpu_and_ram(self):
		print("meow")

	@frappe.whitelist()
	def initialize_devbox(self):
		devbox = self
		server_agent = Agent(server_type="Server", server=devbox.server)
		server_agent.create_agent_job("New Devbox", path="devboxes", data={"devbox_name: ": devbox.name})
		reverse_proxy = frappe.db.get_value(doctype="Server", filters=devbox.server, fieldname="proxy_server")
		proxy_agent = Agent(server_type="Proxy Server", server=reverse_proxy)
		server_private_ip = frappe.db.get_value(
			doctype="Server", filters=devbox.server, fieldname="private_ip"
		)
		proxy_agent.create_agent_job(
			"Add Site to Upstream",
			path=f"proxy/upstreams/{server_private_ip}/sites",
			data={"name": devbox.name},
			upstream=devbox.server,
			devbox=devbox.name,
		)

	@frappe.whitelist()
	def pull_latest_image(self):
		print("meow")


def process_new_devbox_job_update(job: AgentJob):
	if job.status == "Success":
		frappe.db.set_value(dt="Devbox", dn=job.devbox, field="add_site_to_upstream", val=True)
