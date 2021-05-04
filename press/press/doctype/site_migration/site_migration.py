# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob


def get_existing_migration(site: str):
	"""Return ongoing Site Migration for site if it exists."""
	return frappe.db.exists("Site Migration", {"site": "self.site"})


class SiteMigration(Document):
	def validate(self):
		if get_existing_migration(self.site):
			frappe.throw("Ongoing Site Migration for that site exists.")
		self.set_migration_type()

	def after_insert(self):
		self.add_steps()

	def set_migration_type(self):
		if self.source_cluster != self.destination_cluster:
			migration_type = "Cluster"
		elif self.source_server != self.destination_server:
			migration_type = "Server"
		else:
			migration_type = "Bench"
		self.migration_type = migration_type

	def add_steps(self):
		"""Populate steps child table with steps for migration."""
		if self.migration_type == "Cluster":
			self.add_steps_for_inter_cluster_migration()
		else:
			self.add_steps_for_in_cluster_migration()
		self.run_next_step()
		# TODO: Call site update for bench only migration with popup with link to site update job

	@property
	def next_step(self) -> str:
		for step in self.steps:
			if step.status == "Pending":
				return step

	def run_next_step(self):
		next_method = self.next_step.method
		if not next_method:
			self.succeed()
			return
		job = getattr(self, next_method)
		self.next_step.step_name = job(self)
		self.save()

	def update_step_status(self, status: str):
		self.next_step.status = status
		self.save()

	def fail(self):
		self.status = "Failure"
		self.save()

	def succeed(self):
		self.status = "Success"
		self.save()

	def add_steps_for_inter_cluster_migration(self):
		steps = [
			{"step_type": "Agent Job", "method_name": "backup_source_site"},
			{"step_type": "Agent Job", "method_name": "remove_site_from_source_proxy"},
			{"step_type": "Agent Job", "method_name": "restore_site_on_destination"},
			{"step_type": "Agent Job", "method_name": "archive_site_on_source"},
			# without rename
			{"step_type": "Data", "method_name": "update_site_record_fields"},
		]
		for step in steps:
			self.append("steps", step)
		# TODO: domains <03-05-21, Balamurali M> #
		# DNS record
		# might be automatically handled?

	def backup_source_site(self) -> AgentJob:
		agent = Agent(self.source_server)
		site = frappe.get_doc("Site", self.site)
		return agent.backup_site(site, with_files=True, offsite=True)

	def restore_site_on_destination(self):
		agent = Agent(self.destination_server)
		agent.new_site_from_backup(self)
		# TODO: block process new site <03-05-21, Balamurali M> #
		proxy_server = frappe.db.get_value("Server", self.source_server, "proxy_server")
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


def process_site_migration_job_update(job, site_migration: SiteMigration):
	site_migration.update_step_status(job.status)
	if job.status == "Success":
		site_migration.run_next_step()
	elif job.status == "Failure":
		site_migration.fail()
