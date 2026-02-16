# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
from frappe.core.utils import find
from frappe.model.document import Document

from press.agent import Agent
from press.exceptions import (
	ActiveDomainsForStandalone,
	CannotChangePlan,
	InactiveDomains,
	InsufficientSpaceOnServer,
	MissingAppsInBench,
	OngoingAgentJob,
	SiteAlreadyArchived,
	SiteUnderMaintenance,
)
from press.press.doctype.press_notification.press_notification import (
	create_new_notification,
)
from press.press.doctype.site.site import Site
from press.press.doctype.site_backup.site_backup import (
	SiteBackup,
	process_backup_site_job_update,
)
from press.utils import log_error

if TYPE_CHECKING:
	from frappe.types.DF import Link

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.cluster.cluster import Cluster
	from press.press.doctype.server.server import Server
	from press.press.doctype.site_domain.site_domain import SiteDomain


def get_ongoing_migration(site: Link | None, scheduled=False) -> str:
	"""
	Return ongoing Site Migration for site.

	Used to redirect agent job callbacks
	"""
	ongoing_statuses = ["Pending", "Running"]
	if scheduled:
		ongoing_statuses.append("Scheduled")
	return frappe.db.exists("Site Migration", {"site": site, "status": ("in", ongoing_statuses)})


class SiteMigration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.site_migration_step.site_migration_step import SiteMigrationStep

		backup: DF.Link | None
		destination_bench: DF.Link
		destination_cluster: DF.Link
		destination_server: DF.Link
		migration_type: DF.Literal["", "Bench", "Server", "Cluster"]
		scheduled_time: DF.Datetime | None
		site: DF.Link
		skip_failing_patches: DF.Check
		source_bench: DF.Link
		source_cluster: DF.Link
		source_server: DF.Link
		status: DF.Literal["Scheduled", "Pending", "Running", "Success", "Failure"]
		steps: DF.Table[SiteMigrationStep]
	# end: auto-generated types

	def before_insert(self):
		if get_ongoing_migration(self.site, scheduled=True):
			frappe.throw(f"Ongoing/Scheduled Site Migration for the site {frappe.bold(self.site)} exists.")
		site: Site = frappe.get_doc("Site", self.site)
		site.check_move_scheduled()

	def check_for_existing_domains(self):
		"""
		If destination server is standalone, custom domains need to be removed before moving the site and added afterwards.
		"""
		is_standalone = frappe.db.get_value("Server", self.destination_server, "is_standalone")
		if not is_standalone:
			return
		domains = frappe.get_all(
			"Site Domain",
			{"site": self.site, "domain": ("!=", self.site)},
			pluck="domain",
		)

		if domains:
			frappe.throw(
				f"Destination server is standalone. Please remove custom domains: ({', '.join(domains)}) before moving the site. They can be added again after the migration is complete.",
				ActiveDomainsForStandalone,
			)

	def validate_bench(self):
		if frappe.db.get_value("Bench", self.destination_bench, "status", for_update=True) != "Active":
			frappe.throw("Destination bench does not exist")

	@cached_property
	def last_backup(self) -> SiteBackup | None:
		return Site("Site", self.site).last_backup

	def check_enough_space_on_source_server(self):
		# server needs to have enough space to create backup
		try:
			backup = self.last_backup
		except frappe.DoesNotExistError:
			pass
		else:
			site = Site("Site", self.site)
			site.remote_database_file = backup.remote_database_file
			site.remote_public_file = backup.remote_public_file
			site.remote_private_file = backup.remote_private_file
			site.check_space_on_server_for_backup()

	def check_enough_space_on_destination_server(self):
		backup = self.last_backup
		if not backup:
			return
		site = Site("Site", self.site)
		site.server = self.destination_server
		site.remote_database_file = backup.remote_database_file
		site.remote_public_file = backup.remote_public_file
		site.remote_private_file = backup.remote_private_file
		site.check_space_on_server_for_restore()

	def after_insert(self):
		self.set_migration_type()
		self.add_steps()
		self.save()
		if not self.scheduled_time:
			self.start()
		else:
			self.run_validations()

	def validate_apps(self):
		site_apps = [app.app for app in Site("Site", self.site).apps]
		bench_apps = [app.app for app in frappe.get_doc("Bench", self.destination_bench).apps]

		if diff := set(site_apps) - set(bench_apps):
			frappe.throw(
				f"Bench {self.destination_bench} doesn't have some of the apps installed on {self.site}: {', '.join(diff)}",
				MissingAppsInBench,
			)

	def check_for_inactive_domains(self):
		if domains := frappe.db.get_all(
			"Site Domain", {"site": self.site, "status": ("!=", "Active")}, pluck="name"
		):
			frappe.throw(
				f"Inactive custom domains exist: {','.join(domains)}. Please remove or fix the same.",
				InactiveDomains,
			)

	def run_validations(self):
		self.validate_bench()
		self.validate_apps()
		self.check_for_inactive_domains()
		self.check_for_existing_domains()
		self.check_enough_space_on_destination_server()

	@frappe.whitelist()
	def start(self):
		self.check_for_ongoing_agent_jobs()  # has to be before setting state to pending so it gets retried
		previous_status = self.status
		self.status = "Pending"
		self.save()
		self.run_validations()
		site = Site("Site", self.site)
		try:
			site.ready_for_move()
		except SiteAlreadyArchived:
			self.status = "Failure"
			self.save()
			return
		except SiteUnderMaintenance:
			# Just ignore the error for now
			# It can be retried later once the site is out of maintenance
			self.status = previous_status
			self.save()
			return

		self.run_next_step()

	@frappe.whitelist()
	def continue_from_next_pending(self):
		self.remove_archive_on_destination_step_if_exists()
		self.run_next_step()

	def remove_archive_on_destination_step_if_exists(self):
		"""Remove Archive on Destination step if exists"""
		archive_on_destination_step = find(
			self.steps,
			lambda x: x.method_name == self.archive_site_on_destination_server.__name__,
		)
		if archive_on_destination_step:
			self.steps.remove(archive_on_destination_step)

	def check_for_ongoing_agent_jobs(self):
		if frappe.db.exists(
			"Agent Job",
			{
				"status": ("in", ["Pending", "Running"]),
				"site": self.site,
				"creation": (">", frappe.utils.add_to_date(None, hours=-24)),
			},
		):
			frappe.throw("Ongoing Agent Job for site exists", OngoingAgentJob)

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
			source_db = frappe.db.get_value("Server", self.source_server, "database_server")
			destination_db = frappe.db.get_value("Server", self.destination_server, "database_server")
			if source_db == destination_db:
				raise NotImplementedError
				# TODO: switch order of steps here (archive before restore)
			self.add_steps_for_server_migration()
			self.add_steps_for_user_defined_domains()
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
		agent.reload_nginx()

	def _add_remove_host_from_source_proxy_step(self, domain: str):
		step = {
			"step_title": f"Remove host {domain} from source proxy",
			"status": "Pending",
			"method_name": self.remove_host_from_source_proxy.__name__,
			"method_arg": domain,
		}
		self.append("steps", step)

	def _add_remove_user_defined_domain_from_source_proxy_step(self, domain: str):
		step = {
			"step_title": f"Remove user defined domain {domain} from source proxy",
			"method_name": self.remove_user_defined_domain_from_source_proxy.__name__,
			"status": "Pending",
			"method_arg": domain,
		}
		self.append("steps", step)

	def _add_restore_user_defined_domain_to_destination_proxy_step(self, domain: str):
		step = {
			"step_title": f"Restore user defined domain {domain} on destination proxy",
			"method_name": self.restore_user_defined_domain_on_destination_proxy.__name__,
			"status": "Pending",
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
		site_domain: SiteDomain = frappe.get_doc("Site Domain", domain)
		proxy_server = frappe.db.get_value("Server", self.destination_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")

		if site_domain.has_root_tls_certificate:
			return agent.add_domain_to_upstream(
				server=self.destination_server,
				site=site_domain.site,
				domain=site_domain.domain,
			)

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
		site = Site("Site", self.site)
		ret = site._update_redirects_for_all_site_domains()
		if ret:
			# could be no jobs
			return ret
		self.update_next_step_status("Skipped")
		return self.run_next_step()

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

	def add_steps_for_user_defined_domains(self):
		domains = frappe.get_all("Site Domain", {"site": self.site, "name": ["!=", self.site]}, pluck="name")
		for domain in domains:
			site_domain = frappe.get_doc("Site Domain", domain)
			if site_domain.default or not site_domain.has_root_tls_certificate:
				continue
			self._add_remove_user_defined_domain_from_source_proxy_step(domain)
			self._add_restore_user_defined_domain_to_destination_proxy_step(domain)

	@property
	def next_step(self) -> SiteMigrationStep | None:
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
		if not self.next_step:
			raise ValueError("No next step to update status for")
		self.next_step.status = status
		self.save()

	@property
	def possibly_archived_site_on_source(self) -> bool:
		return find(self.steps, lambda x: x.method_name == self.archive_site_on_source.__name__).status in [
			"Success",
			"Failure",
		]

	def set_pending_steps_to_skipped(self):
		for step in self.steps:
			if step.status == "Pending":
				step.status = "Skipped"
		self.save()

	@property
	def restore_on_destination_happened(self) -> bool:
		return find(
			self.steps,
			lambda x: x.method_name == self.restore_site_on_destination_server.__name__,
		).status in ["Success", "Failure"]

	def cleanup_if_appropriate(self):
		self.set_pending_steps_to_skipped()
		if self.possibly_archived_site_on_source or not self.restore_on_destination_happened:
			return False
		self.append(
			"steps",
			{
				"step_title": self.archive_site_on_destination_server.__doc__,
				"method_name": self.archive_site_on_destination_server.__name__,
				"status": "Pending",
			},
		)
		self.run_next_step()
		return True

	@frappe.whitelist()
	def cleanup_and_fail(self, *args, **kwargs):
		if self.cleanup_if_appropriate():
			return  # callback will trigger fail
		self.fail(*args, **kwargs)

	def fail(self, reason: str | None = None, force_activate: bool = False):
		self.status = "Failure"
		self.save()
		self.send_fail_notification(reason)
		self.activate_site_if_appropriate(force=force_activate)

	@property
	def failed_step(self):
		return find(self.steps, lambda x: x.status == "Failure")

	def activate_site_if_appropriate(self, force=False):
		site = Site("Site", self.site)
		failed_step_method_name = (self.failed_step or {}).get("method_name", "__NOT_SET__")
		if force or (
			failed_step_method_name
			in [
				self.backup_source_site.__name__,
				self.restore_site_on_destination_server.__name__,
				self.restore_site_on_destination_proxy.__name__,
			]
			and site.status_before_update != "Inactive"
		):
			site.activate()
		elif site.status_before_update == "Inactive":
			site.db_set("status", "Inactive")
		if self.is_standalone_migration:
			site.create_dns_record()
		if self.migration_type == "Cluster":
			if site.cluster == frappe.db.get_value(
				"Root Domain", site.domain, "default_cluster"
			):  # reverse the DNS record creation
				site.remove_dns_record(frappe.db.get_value("Server", self.destination_server, "proxy_server"))
			else:
				site.create_dns_record()

	def send_fail_notification(self, reason: str | None = None):
		from press.press.doctype.agent_job.agent_job_notifications import create_job_failed_notification

		site = Site("Site", self.site)
		message = f"Site Migration ({self.migration_type}) for site <b>{site.host_name}</b> failed"
		if reason:
			message += f" due to {reason}"
			agent_job_id = None

			create_new_notification(
				site.team,
				"Site Migrate",
				"Agent Job",
				agent_job_id,
				message,
			)
		else:
			agent_job_id = find(self.steps, lambda x: x.status == "Failure").get("step_job")

			job = frappe.get_doc("Agent Job", agent_job_id)
			create_job_failed_notification(job, site.team, "Site Migrate", "Site Migrate", message)

	def succeed(self):
		self.status = "Success"
		self.save()
		self.send_success_notification()

	def send_success_notification(self):
		site = Site("Site", self.site)

		message = (
			f"Site Migration ({self.migration_type}) for site <b>{site.host_name}</b> completed successfully"
		)
		agent_job_id = find(self.steps, lambda x: x.step_title == "Restore site on destination").step_job

		create_new_notification(
			site.team,
			"Site Migrate",
			"Agent Job",
			agent_job_id,
			message,
		)

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
			{
				"step_title": self.adjust_plan_if_required.__doc__,
				"method_name": self.adjust_plan_if_required.__name__,
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
				"step_title": self.restore_site_on_destination_server.__doc__,
				"method_name": self.restore_site_on_destination_server.__name__,
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
			{
				"step_title": self.adjust_plan_if_required.__doc__,
				"method_name": self.adjust_plan_if_required.__name__,
				"status": "Pending",
			},
		]
		for step in steps:
			self.append("steps", step)

	def deactivate_site_on_source_server(self):
		"""Deactivate site on source"""
		site: Site = frappe.get_doc("Site", self.site)
		site.status = "Pending"
		return site.update_site_config({"maintenance_mode": 1})  # saves doc

	def deactivate_site_on_source_proxy(self):
		"""Deactivate site on source proxy"""
		site = frappe.get_doc("Site", self.site)
		return site.update_site_status_on_proxy("deactivated")

	def backup_source_site(self):
		"""Backup site on source"""
		site = frappe.get_doc("Site", self.site)

		backup = site.backup(with_files=True, offsite=True, force=True)
		backup.reload()
		self.backup = backup.name
		self.save()

		return frappe.get_doc("Agent Job", backup.job)

	def archive_site_on_destination_server(self):
		"""Archive site on destination (case of failure)"""
		agent = Agent(self.destination_server)
		site = frappe.get_doc("Site", self.site)
		site.bench = self.destination_bench
		return agent.archive_site(site, force=True)

	def restore_site_on_destination_server(self):
		"""Restore site on destination"""
		agent = Agent(self.destination_server)
		site: Site = frappe.get_doc("Site", self.site)
		backup: SiteBackup = frappe.get_doc("Site Backup", self.backup)
		site.remote_database_file = backup.remote_database_file
		site.remote_public_file = backup.remote_public_file
		site.remote_private_file = backup.remote_private_file
		site.remote_config_file = ""  # Use site config from press only
		site.bench = self.destination_bench
		site.cluster = self.destination_cluster
		site.server = self.destination_server
		if self.migration_type == "Cluster":
			site.create_dns_record()  # won't create for default cluster
			if self.destination_cluster == frappe.db.get_value("Root Domain", site.domain, "default_cluster"):
				source_proxy = str(frappe.db.get_value("Server", self.source_server, "proxy_server"))
				site.remove_dns_record(source_proxy)
		elif self.is_standalone_migration:
			site.create_dns_record()
		return agent.new_site_from_backup(site, skip_failing_patches=self.skip_failing_patches)

	def restore_site_on_destination_proxy(self):
		"""Restore site on destination proxy"""
		proxy_server = frappe.db.get_value("Server", self.destination_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.new_upstream_file(server=self.destination_server, site=self.site)

	def restore_user_defined_domain_on_destination_proxy(self, domain: str):
		"""Restore user defined domain on destination proxy for product trial sites"""

		proxy_server = frappe.db.get_value("Server", self.destination_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		site_domain: SiteDomain = frappe.get_doc("Site Domain", domain)

		return agent.add_domain_to_upstream(
			server=self.destination_server, site=site_domain.site, domain=domain
		)

	def remove_site_from_source_proxy(self):
		"""Remove site from source proxy"""
		proxy_server = frappe.db.get_value("Server", self.source_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.remove_upstream_file(server=self.source_server, site=self.site)

	def remove_user_defined_domain_from_source_proxy(self, domain: str):
		"""Remove user defined domain from source proxy for product trial sites"""
		proxy_server = frappe.db.get_value("Server", self.source_server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.remove_upstream_file(server=self.source_server, site=self.site, site_name=domain)

	def archive_site_on_source(self):
		"""Archive site on source"""
		agent = Agent(self.source_server)
		site = frappe.get_doc("Site", self.site)
		site.bench = self.source_bench  # for sanity
		return agent.archive_site(site)

	def update_site_record_fields(self):
		"""Update fields of original site record"""
		site = frappe.get_doc("Site", self.site)
		site.db_set("bench", self.destination_bench)
		site.db_set("server", self.destination_server)
		site.db_set("cluster", self.destination_cluster)
		self.update_next_step_status("Success")
		self.run_next_step()

	@property
	def is_standalone_migration(self) -> bool:
		return frappe.db.get_value("Server", self.destination_server, "is_standalone") or frappe.db.get_value(
			"Server", self.source_server, "is_standalone"
		)

	def reset_site_status_on_destination(self):
		"""Reset site status on destination"""
		site: Site = frappe.get_doc("Site", self.site)
		if site.status_before_update in ["Inactive", "Suspended"]:
			self.update_next_step_status("Skipped")
			job = None
		else:
			job = site.update_site_config({"maintenance_mode": 0})  # will do run_next_step in callback
		site.reload()
		site.status = site.status_before_update or "Active"
		site.status_before_update = None
		site.save()
		if job:
			return job
		return self.run_next_step()

	def activate_site_on_destination_proxy(self):
		"""Activate site on destination proxy"""
		site = frappe.get_doc("Site", self.site)
		return site.update_site_status_on_proxy("activated")

	@property
	def scheduled_by_consultant(self):
		return self.owner.endswith("@erpnext.com") or self.owner.endswith("@frappe.io")

	def upgrade_plan(self, site: "Site", dest_server: Server):
		if not dest_server.public and site.team == dest_server.team and not site.is_on_dedicated_plan:
			return site.change_plan(
				"Unlimited",
				ignore_card_setup=self.scheduled_by_consultant,
			)
		return None

	def downgrade_plan(self, site: "Site", dest_server: Server):
		if dest_server.public and site.team != dest_server.team and site.is_on_dedicated_plan:
			return site.change_plan(
				"USD 100",
				ignore_card_setup=self.scheduled_by_consultant,
			)
		return None

	def adjust_plan_if_required(self):
		"""Update site plan from/to Unlimited"""
		site: "Site" = frappe.get_doc("Site", self.site)
		dest_server: Server = frappe.get_doc("Server", self.destination_server)
		plan_change = None
		try:
			plan_change = self.upgrade_plan(site, dest_server) or self.downgrade_plan(site, dest_server)
		except CannotChangePlan:
			self.update_next_step_status("Failure")

		if plan_change:
			self.update_next_step_status("Success")
		else:
			self.update_next_step_status("Skipped")
		self.run_next_step()

	def is_cleanup_done(self, job: "AgentJob") -> bool:
		return (job.job_type == "Archive Site" and job.bench == self.destination_bench) and (
			job.status == "Success"
			or (
				job.status == "Failure"
				and (
					f"KeyError: '{self.site}'" in str(job.traceback)
					or "BenchNotExistsException" in str(job.traceback)
				)
			)  # sometimes site may not even get created in destination to clean it up
		)

	def get_steps(self) -> list[dict]:
		steps = []
		for step in self.steps:
			# Now if the step has agent job expand that as well
			if step.step_job:
				job = frappe.get_doc("Agent Job", step.step_job)
				agent_steps = frappe.get_all(
					"Agent Job Step",
					{"agent_job": step.step_job},
					["name", "step_name", "status", "output"],
					order_by="creation asc",
				)
				for s in agent_steps:
					steps.append(
						{
							"name": s.name,
							"title": s.step_name,
							"status": s.status,
							"output": s.output,
							"stage": job.job_type,
						}
					)
			else:
				steps.append(
					{
						"name": step.name,
						"title": step.step_title,
						"status": step.status,
						"output": "",
						"stage": "Migrating Site",
					}
				)

		return steps


def process_required_job_callbacks(job):
	if job.job_type == "Backup Site":
		process_backup_site_job_update(job)


def job_matches_site_migration(job, site_migration_name: str):
	site_migration = SiteMigration("Site Migration", site_migration_name)
	next = site_migration.next_step
	return job.name == next.step_job if next else False


def process_site_migration_job_update(job, site_migration_name: str):
	site_migration = SiteMigration("Site Migration", site_migration_name)
	if not site_migration.next_step:
		log_error("No next step found during Site Migration", doc=site_migration)
		return
	if job.name != site_migration.next_step.step_job:
		log_error("Extra Job found during Site Migration", job=job.as_dict())
		return

	process_required_job_callbacks(job)
	site_migration.update_next_step_status(job.status)

	if site_migration.is_cleanup_done(job):
		site_migration.fail()
		return

	if job.status == "Success":
		try:
			site_migration.run_next_step()
		except Exception as e:
			log_error("Site Migration Step Error", doc=site_migration)
			site_migration.cleanup_and_fail(reason=str(e), force_activate=True)
	elif job.status in ["Failure", "Delivery Failure"]:
		site_migration.cleanup_and_fail()


def run_scheduled_migrations():
	migrations = frappe.get_all(
		"Site Migration",
		{"scheduled_time": ("<=", frappe.utils.now()), "status": "Scheduled"},
	)
	for migration in migrations:
		site_migration = SiteMigration("Site Migration", migration)
		try:
			site_migration.start()
		except OngoingAgentJob as e:
			if not site_migration.scheduled_time:
				return
			if frappe.utils.now() > site_migration.scheduled_time + timedelta(
				hours=4
			):  # don't trigger more than 4 hours later scheduled time
				site_migration.cleanup_and_fail(reason=str(e))
		except (
			MissingAppsInBench,
			InsufficientSpaceOnServer,
			InactiveDomains,
			ActiveDomainsForStandalone,
		) as e:
			site_migration.cleanup_and_fail(reason=str(e), force_activate=True)
		except Exception as e:
			log_error("Site Migration Start Error", exception=e)


def on_doctype_update():
	frappe.db.add_index("Site Migration", ["site"])
