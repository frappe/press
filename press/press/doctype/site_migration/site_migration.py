# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import functools
from time import sleep

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

	def wait_for_job(self, job: AgentJob) -> bool:
		"""
		Wait for async agent job and return True if successful.

		CAN go on forever!
		- Update steps when status changes
		"""
		while True:
			sleep(6)
			job.reload()
			self.steps[-1].status = job.status
			if job.status == "Success":
				ret = True
				break
			elif job.status == "Failure":
				ret = False
				break
			self.save()
		return ret

	def sequential_step(func):
		"""Create child table entry and wait for result."""

		@functools.wraps(func)
		def wrapper(self, *args, **kwargs) -> bool:
			job = func(self, *args, **kwargs)
			self.append("steps", {"step_type": job.doctype, "step_name": job.name})
			self.save()
			return self.wait_for_job(job)

		return wrapper

	def add_steps_for_inter_cluster_migration(self):
		(
			self.backup_source_site()
			and self.remove_site_from_source_proxy()
			and self.restore_site_on_destination()
			and self.archive_site_on_source()  # without rename and other process archive job
			and self.update_site_record_fields()
		)  # update press values for site
		# TODO: domains <03-05-21, Balamurali M> #
		# DNS record
		# might be automatically handled?

	@sequential_step
	def backup_source_site(self) -> AgentJob:
		agent = Agent(self.source_server)
		site = frappe.get_doc("Site", self.site)
		return agent.backup_site(site, with_files=True, offsite=True)

	# def deactivate_on_source_proxy(self):
	# 	site = frappe.get_doc("Site", self.site)
	# 	return site.update_site_status_on_proxy()

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
