# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import secrets
import string
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
		browser_port: DF.Int
		codeserver_password: DF.Data | None
		codeserver_port: DF.Int
		container_id: DF.Data | None
		cpu_cores: DF.Int
		database_volume_size: DF.Data | None
		disk_mb: DF.Int
		domain: DF.Link | None
		home_volume_size: DF.Data | None
		initialized: DF.Check
		is_destroyed: DF.Check
		ram: DF.Int
		server: DF.Link
		status: DF.Literal["Pending", "Starting", "Paused", "Running", "Archived", "Exited"]
		subdomain: DF.Data
		vnc_password: DF.Data | None
		vnc_port: DF.Int
		websockify_port: DF.Int
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
	def destroy_devbox(self):
		devbox = self
		reverse_proxy = frappe.db.get_value(doctype="Server", filters=devbox.server, fieldname="proxy_server")
		proxy_agent = Agent(server_type="Proxy Server", server=reverse_proxy)
		server_private_ip = frappe.db.get_value(
			doctype="Server", filters=devbox.server, fieldname="private_ip"
		)
		proxy_agent.create_agent_job(
			"Remove Site from Upstream",
			path=f"/proxy/upstreams/{server_private_ip}/sites/{devbox.name}",
			data={"name": devbox.name},
			devbox=devbox.name,
			method="DELETE",
		)
		server_agent = Agent(server_type="Server", server=devbox.server)
		server_agent.create_agent_job(
			"Destroy Devbox",
			path=f"/devboxes/{devbox.name}/destroy",
			devbox=devbox.name,
		)

	@frappe.whitelist()
	def initialize_devbox(self):
		devbox = self
		devbox.vnc_password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
		devbox.codeserver_password = "".join(
			secrets.choice(string.ascii_letters + string.digits) for _ in range(8)
		)
		devbox.save()
		server_agent = Agent(server_type="Server", server=devbox.server)
		server_agent.create_agent_job(
			"New Devbox",
			path="devboxes",
			data={
				"devbox_name": devbox.name,
				"vnc_password": devbox.vnc_password,
				"codeserver_password": devbox.codeserver_password,
			},
			devbox=devbox.name,
		)
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
	def start_devbox(self):
		devbox = self
		server_agent = Agent(server_type="Server", server=devbox.server)
		server_agent.create_agent_job(
			"Start Devbox",
			path=f"devboxes/{devbox.name}/start",
			data={
				"vnc_password": devbox.vnc_password,
				"codeserver_password": devbox.codeserver_password,
				"websockify_port": devbox.websockify_port,
				"vnc_port": devbox.vnc_port,
				"codeserver_port": devbox.codeserver_port,
				"browser_port": devbox.browser_port,
			},
			devbox=devbox.name,
		)

	@frappe.whitelist()
	def stop_devbox(self):
		devbox = self
		server_agent = Agent(server_type="Server", server=devbox.server)
		server_agent.create_agent_job(
			"Stop Devbox",
			path=f"devboxes/{devbox.name}/stop",
			devbox=devbox.name,
		)

	@frappe.whitelist()
	def sync_devbox_status(self):
		agent = Agent(server_type="Server", server=self.server)
		result = agent.post(f"devboxes/{self.name}/status")
		status = result.get("output").title()
		# hoping this is a error. I know this is shit code.
		if len(status) > 10:
			status = "Exited"
		frappe.db.set_value(dt="Devbox", dn=self.name, field="status", val=status)

	@frappe.whitelist()
	def sync_devbox_docker_volumes_size(self):
		agent = Agent(server_type="Server", server=self.server)
		parsed_result = agent.post(f"devboxes/{self.name}/docker_volumes_size")["message"]

		for field in ["database_volume_size", "home_volume_size"]:
			frappe.db.set_value(dt="Devbox", dn=self.name, field=field, val=parsed_result.get(field))


def process_new_devbox_job_update(job: AgentJob):
	if job.job_type == "New Devbox" and job.status == "Success":
		data = json.loads(job.data)["message"]
		update_fields = {
			"initialized": True,
			"websockify_port": data["websockify_port"],
			"vnc_port": data["vnc_port"],
			"codeserver_port": data["codeserver_port"],
			"browser_port": data["browser_port"],
		}
		frappe.db.set_value("Devbox", job.devbox, update_fields)

	if job.job_type == "Destroy Devbox" and job.status == "Success":
		update_fields = {
			"is_destroyed": True,
		}
		frappe.db.set_value("Devbox", job.devbox, update_fields)

	if job.job_type == "Add Site to Upstream" and job.status == "Success":
		frappe.db.set_value(dt="Devbox", dn=job.devbox, field="add_site_to_upstream", val=True)

	if job.job_type == "Start Devbox" and job.status == "Success":
		devbox = frappe.get_doc("Devbox", job.devbox)
		devbox.sync_devbox_status()

	if job.job_type == "Stop Devbox" and job.status == "Success":
		frappe.db.set_value(dt="Devbox", dn=job.devbox, field="status", val="Exited")

	status = frappe.db.get_value("Devbox", job.devbox, ["initialized", "add_site_to_upstream"], as_dict=True)

	if status.initialized and status.add_site_to_upstream:
		frappe.db.set_value(dt="Devbox", dn=job.devbox, field="status", val="Starting")
