# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.core.utils import find
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.site_backup.site_backup import process_backup_site_job_update
from press.utils import log_error


def get_ongoing_migration(site: str):
	"""Return ongoing Site Migration for site."""
	return frappe.db.exists(
		"Site Migration", {"site": site, "status": ("in", ["Pending", "Running"])}
	)


class SiteMigration(Document):
	def before_insert(self):
		if get_ongoing_migration(self.site):
			frappe.throw("Ongoing Site Migration for that site exists.")
		self.check_for_existing_agent_jobs()

	def after_insert(self):
		self.set_migration_type()
		self.add_steps()
		self.save()
		if not self.scheduled_time:
			self.start()

	def start(self):
		self.db_set("status", "Pending")
		frappe.db.commit()
		self.run_next_step()

	def check_for_existing_agent_jobs(self):
		if frappe.db.exists(
			"Agent Job", {"status": ("in", ["Pending", "Running"]), "site": self.site}
		):
			frappe.throw("Ongoing Agent Job for site exists")

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
			self.add_steps_for_cluster_migration()
			self.add_steps_for_domains()
		elif self.migration_type == "Server":
			self.add_steps_for_server_migration()
		else:
			# TODO: Call site update for bench only migration with popup with link to site update job
			raise NotImplementedError

	def remove_domain_hosts_from_source(self):
		"""Remove domain hosts from source"""
		domains = frappe.get_all("Site Domain", {"site": self.site}, pluck="name")

		proxy_server = frappe.db.get_value("Server", self.source_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")

		for domain in domains:
			site_domain = frappe.get_doc("Site Domain", domain)
			agent.remove_host(site_domain)

	def _add_remove_host_from_source_proxy_step(self, domain: str):
		step = {
			"step_title": f"Remove host {domain} from source proxy",
			"status": "Pending",
			"method_name": self.remove_host_from_source_proxy.__name__,
			"method_arg": domain,
		}
		self.append("steps", step)

	def _add_add_host_to_destination_proxy_step(self, domain: str):
		step = {
			"step_title": f"Add host {domain} to destination proxy",
			"status": "Pending",
			"method_name": self.add_host_to_destination_proxy.__name__,
			"method_arg": domain,
		}
		self.append("steps", step)

	def add_host_to_destination_proxy(self, domain):
		site_domain = frappe.get_doc("Site Domain", domain)
		proxy_server = frappe.db.get_value("Server", self.destination_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.new_host(site_domain)

	def remove_host_from_source_proxy(self, domain):
		site_domain = frappe.get_doc("Site Domain", domain)
		proxy_server = frappe.db.get_value("Server", self.source_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.remove_host(site_domain)

	def _add_setup_redirects_step(self):
		step = {
			"step_title": self.setup_redirects.__doc__,
			"status": "Pending",
			"method_name": self.setup_redirects.__name__,
		}
		self.append("steps", step)

	def setup_redirects(self):
		"""Setup redirects of site in proxy"""
		site = frappe.get_doc("Site", self.site)
		ret = site._update_redirects_for_all_site_domains()
		if ret:
			# could be no jobs
			return ret
		self.update_next_step_status("Skipped")
		self.run_next_step()

	def add_steps_for_domains(self):
		domains = frappe.get_all("Site Domain", {"site": self.site}, pluck="name")
		for domain in domains:
			site_domain = frappe.get_doc("Site Domain", domain)
			if site_domain.default:
				continue
			self._add_remove_host_from_source_proxy_step(domain)
			self._add_add_host_to_destination_proxy_step(domain)
		if len(domains) > 1:
			self._add_setup_redirects_step()

	@property
	def next_step(self):
		"""Get next step to execute or update."""
		return find(self.steps, lambda step: step.status in ["Pending", "Running"])

	@frappe.whitelist()
	def run_next_step(self):
		self.status = "Running"

		next_step = self.next_step
		if not next_step:
			self.succeed()
			return
		next_method: str = next_step.method_name
		# right now only single argument possible
		method_arg: str = next_step.method_arg
		method = getattr(self, next_method)

		if method_arg:
			next_step.step_job = getattr(method(method_arg), "name", None)
		else:
			next_step.step_job = getattr(method(), "name", None)
		self.save()

	def update_next_step_status(self, status: str):
		self.next_step.status = status
		self.save()

	def fail(self):
		self.status = "Failure"
		self.save()

	def succeed(self):
		self.status = "Success"
		self.save()

	def add_steps_for_cluster_migration(self):
		steps = [
			{
				"step_title": self.deactivate_site_on_source_server.__doc__,
				"method_name": self.deactivate_site_on_source_server.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.backup_source_site.__doc__,
				"method_name": self.backup_source_site.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.restore_site_on_destination_server.__doc__,
				"method_name": self.restore_site_on_destination_server.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.restore_site_on_destination_proxy.__doc__,
				"method_name": self.restore_site_on_destination_proxy.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.remove_site_from_source_proxy.__doc__,
				"method_name": self.remove_site_from_source_proxy.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.archive_site_on_source.__doc__,
				"method_name": self.archive_site_on_source.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.update_site_record_fields.__doc__,
				"method_name": self.update_site_record_fields.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.reset_site_status_on_destination.__doc__,
				"method_name": self.reset_site_status_on_destination.__name__,
				"status": "Pending",
			},
		]
		for step in steps:
			self.append("steps", step)

	def add_steps_for_server_migration(self):
		steps = [
			{
				"step_title": self.deactivate_site_on_source_server.__doc__,
				"method_name": self.deactivate_site_on_source_server.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.backup_source_site.__doc__,
				"method_name": self.backup_source_site.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.archive_site_on_source.__doc__,
				"method_name": self.archive_site_on_source.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.remove_site_from_source_proxy.__doc__,
				"method_name": self.remove_site_from_source_proxy.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.restore_site_on_destination_server.__doc__,
				"method_name": self.restore_site_on_destination_server.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.restore_site_on_destination_proxy.__doc__,
				"method_name": self.restore_site_on_destination_proxy.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.update_site_record_fields.__doc__,
				"method_name": self.update_site_record_fields.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.reset_site_status_on_destination.__doc__,
				"method_name": self.reset_site_status_on_destination.__name__,
				"status": "Pending",
			},
		]
		for step in steps:
			self.append("steps", step)

	def deactivate_site_on_source_server(self):
		"""Deactivate site on source"""
		site = frappe.get_doc("Site", self.site)
		site.status_before_update = site.status
		site.status = "Inactive"
		return site.update_site_config({"maintenance_mode": 1})  # saves doc

	def deactivate_site_on_source_proxy(self):
		"""Deactivate site on source proxy"""
		site = frappe.get_doc("Site", self.site)
		return site.update_site_status_on_proxy("deactivated")

	def backup_source_site(self):
		"""Backup site on source"""
		site = frappe.get_doc("Site", self.site)

		backup = site.backup(with_files=True, offsite=True)
		backup.reload()
		self.backup = backup.name
		self.save()

		return frappe.get_doc("Agent Job", backup.job)

	def restore_site_on_destination_server(self):
		"""Restore site on destination"""
		agent = Agent(self.destination_server)
		site = frappe.get_doc("Site", self.site)
		backup = frappe.get_doc("Site Backup", self.backup)
		site.remote_database_file = backup.remote_database_file
		site.remote_public_file = backup.remote_public_file
		site.remote_private_file = backup.remote_private_file
		site.bench = self.destination_bench
		site.cluster = self.destination_cluster
		site.server = self.destination_server
		if self.migration_type == "Cluster":
			site.create_dns_record()
			domain = frappe.get_doc("Root Domain", site.domain)
			if self.destination_cluster == domain.default_cluster:
				source_proxy = frappe.db.get_value("Server", self.source_server, "proxy_server")
				site.remove_dns_record(domain, source_proxy)
		return agent.new_site_from_backup(site)

	def restore_site_on_destination_proxy(self):
		"""Restore site on destination proxy"""
		proxy_server = frappe.db.get_value("Server", self.destination_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.new_upstream_site(self.destination_server, self.site)

	def remove_site_from_source_proxy(self):
		"""Remove site from source proxy"""
		proxy_server = frappe.db.get_value("Server", self.source_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.remove_upstream_site(self.source_server, self.site)

	def archive_site_on_source(self):
		"""Archive site on source"""
		agent = Agent(self.source_server)
		site = frappe.get_doc("Site", self.site)
		return agent.archive_site(site)

	def update_site_record_fields(self):
		"""Update fields of original site record"""
		site = frappe.get_doc("Site", self.site)
		site.db_set("bench", self.destination_bench)
		site.db_set("server", self.destination_server)
		site.db_set("cluster", self.destination_cluster)
		self.update_next_step_status("Success")
		self.run_next_step()

	def reset_site_status_on_destination(self):
		"""Reset site status on destination"""
		site = frappe.get_doc("Site", self.site)
		if site.status_before_update in ["Inactive", "Suspended"]:
			self.update_next_step_status("Skipped")
			self.run_next_step()
			job = None
		else:
			job = site.update_site_config({"maintenance_mode": 0})
		site.reload()
		site.status = site.status_before_update
		site.status_before_update = None
		site.save()
		return job

	def activate_site_on_destination_proxy(self):
		"""Activate site on destination proxy"""
		site = frappe.get_doc("Site", self.site)
		return site.update_site_status_on_proxy("activated")


def process_required_job_callbacks(job):
	if job.job_type == "Backup Site":
		process_backup_site_job_update(job)


def process_site_migration_job_update(job, site_migration_name: str):
	site_migration = frappe.get_doc("Site Migration", site_migration_name)
	if job.name == site_migration.next_step.step_job:
		process_required_job_callbacks(job)
		site_migration.update_next_step_status(job.status)
		if job.status == "Success":
			try:
				site_migration.run_next_step()
			except Exception:
				log_error("Site Migration Step Error")
		elif job.status == "Failure":
			site_migration.fail()
	else:
		log_error("Extra Job found during Site Migration", job=job.as_dict())


def run_scheduled_migrations():
	migrations = frappe.get_all(
		"Site Migration",
		{"scheduled_time": ("<=", frappe.utils.now()), "status": "Scheduled"},
	)
	for migration in migrations:
		site_migration = frappe.get_doc("Site Migration", migration)
		site_migration.start()


def on_doctype_update():
	frappe.db.add_index("Site Migration", ["site"])
