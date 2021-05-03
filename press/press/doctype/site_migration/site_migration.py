# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob


class SiteMigration(Document):
	def validate(self):
		self.check_existing()
		self.set_migration_type()

	def check_existing(self):
		"""Throw err if running/pending migration job for the same site exists."""
		# TODO:  <03-05-21, Balamurali M> #
		pass

	def set_migration_type(self):
		if self.source_cluster != self.destination_cluster:
			migration_type = "Cluster"
		elif self.source_server != self.destination_server:
			migration_type = "Server"
		else:
			migration_type = "Bench"
		self.migration_type = migration_type

	def after_insert(self):
		self.add_steps()

	def add_steps(self):
		"""Populate steps child table with steps for migration."""
		if self.migration_type == "Cluster":
			self.add_steps_for_inter_cluster_migration()
		else:
			self.add_steps_for_in_cluster_migration()
		# TODO: add simpler steps for in bench migration <03-05-21, Balamurali M> #

	def add_steps_for_inter_cluster_migration(self):
		self.backup_source_site()
		self.remove_site_from_source_proxy()
		self.restore_site_on_destination()
		self.archive_site_on_source()
		# without rename and other process archive job
		self.update_site_record_fields()  # update press values for site
		# TODO: domains <03-05-21, Balamurali M> #
		# DNS record
		# might be automatically handled?

	def backup_source_site(self) -> AgentJob:
		agent = Agent(self.source_server)
		return agent.backup_site(self.site, with_files=True, offsite=True)

	# def deactivate_on_source_proxy(self):
	# 	site = frappe.get_doc("Site", self.site)
	# 	return site.update_site_status_on_proxy()

	def restore_site_on_destination(self):
		agent = Agent(self.destination_server)
		agent.new_site_from_backup(self)
		# TODO: block process new site <03-05-21, Balamurali M> #
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.new_upstream_site(self.destination_server, self.site)

	def remove_site_from_source_proxy(self):
		proxy_server = frappe.db.get_value("Server", self.source_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		# TODO: block process archive site job update <03-05-21, Balamurali M> #
		return agent.remove_upstream_site()

	def archive_site_on_source(self):
		agent = Agent(self.server)
		return agent.archive_site(self.site)
		# TODO: maybe remove domains here <03-05-21, Balamurali M> #
		# TODO: block rename of records <03-05-21, Balamurali M> #
	
	def update_site_record_fields(self):
		site = frappe.get_doc("Site", self.site)
		site.bench = self.destination_bench
		site.server = self.destination_server
		site.save()

