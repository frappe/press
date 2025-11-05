# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

from press.agent import Agent

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


class AutoScaleRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		primary_server: DF.Link
		scale_down: DF.Check
		scale_up: DF.Check
		secondary_server: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		"""Set metadata attributes"""
		self.secondary_server = frappe.db.get_value("Server", self.primary_server, "secondary_server")

	def after_insert(self):
		"""Trigger auto scaling"""

		if self.scale_up:
			self.switch_to_secondary()

		if self.scale_down:
			self.switch_to_primary()

	def switch_to_secondary(self):
		"""
		Updates common site config with redis connection string and
		bench directories in all the configs.
		"""
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)
		primary_server_private_ip = frappe.db.get_value("Server", self.primary_server, "private_ip")
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")
		frappe.db.set_value("Server", self.primary_server, "scaled_up", True)

		self.setup_secondary_upstream()

		return Agent(self.secondary_server).change_bench_directory(
			redis_connection_string_ip=primary_server_private_ip,
			secondary_server_private_ip=secondary_server_private_ip,
			directory="/shared",
			is_primary=False,
			registry_settings={
				"url": settings.docker_registry_url,
				"username": settings.docker_registry_username,
				"password": settings.docker_registry_password,
			},
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.secondary_server,
		)

	def switch_to_primary(self) -> "AgentJob":
		"""
		Updates common site config with redis connection string and
		bench directories in all the configs.
		"""
		secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")
		frappe.db.set_value("Server", self.primary_server, "scaled_up", False)

		self.setup_primary_upstream()

		return Agent(self.primary_server).change_bench_directory(
			redis_connection_string_ip="localhost",
			secondary_server_private_ip=secondary_server_private_ip,
			is_primary=True,
			directory="/shared",
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

	def setup_secondary_upstream(self) -> "AgentJob":
		"""Update proxy server with secondary as upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		active_sites = frappe.get_all("Site", {"server": self.primary_server}, pluck="name")

		for site in active_sites:
			agent.new_upstream_file(server=self.secondary_server, site=site)
			frappe.db.set_value("Site", site, "server", self.secondary_server)

		frappe.db.commit()  # Commit for sanity

	def setup_primary_upstream(self) -> "AgentJob":
		"""Fallback to older primary servers upstream by removing the secondary servers upstream"""
		proxy_server = frappe.get_value("Server", self.secondary_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		active_sites = frappe.get_all("Site", {"server": self.secondary_server}, pluck="name")

		for site in active_sites:
			agent.new_upstream_file(server=self.primary_server, site=site)
			agent.remove_upstream_file(server=self.secondary_server, site=site)
			frappe.db.set_value("Site", site, "server", self.primary_server)

		frappe.db.commit()  # Commit for sanity
