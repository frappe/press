# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import random
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

import frappe
import frappe.utils
import pytz
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils import convert_utc_to_system_timezone
from frappe.utils.caching import site_cache
from frappe.utils.data import cint

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.exceptions import SiteAlreadyArchived, SiteUnderMaintenance
from press.press.doctype.logical_replication_backup.logical_replication_backup import (
	get_logical_replication_backup_restoration_steps,
)
from press.press.doctype.physical_backup_restoration.physical_backup_restoration import (
	get_physical_backup_restoration_steps,
)
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.logical_replication_backup.logical_replication_backup import (
		LogicalReplicationBackup,
	)
	from press.press.doctype.physical_backup_restoration.physical_backup_restoration import (
		PhysicalBackupRestoration,
	)
	from press.press.doctype.site.site import Site


class SiteUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		name: DF.Data
		activate_site_job: DF.Link | None
		backup_type: DF.Literal["Logical", "Physical", "Logical Replication"]
		cause_of_failure_is_resolved: DF.Check
		deactivate_site_job: DF.Link | None
		deploy_type: DF.Literal["", "Pull", "Migrate"]
		destination_bench: DF.Link | None
		destination_candidate: DF.Link | None
		destination_group: DF.Link | None
		difference: DF.Link | None
		difference_deploy_type: DF.Literal["", "Pull", "Migrate"]
		group: DF.Link | None
		logical_replication_backup: DF.Link | None
		physical_backup_restoration: DF.Link | None
		recover_job: DF.Link | None
		scheduled_time: DF.Datetime | None
		server: DF.Link | None
		site: DF.Link | None
		site_backup: DF.Link | None
		skipped_backups: DF.Check
		skipped_failing_patches: DF.Check
		source_bench: DF.Link | None
		source_candidate: DF.Link | None
		status: DF.Literal[
			"Pending",
			"Running",
			"Success",
			"Failure",
			"Recovering",
			"Recovered",
			"Fatal",
			"Scheduled",
			"Cancelled",
		]
		team: DF.Link | None
		touched_tables: DF.Code | None
		update_duration: DF.Duration | None
		update_end: DF.Datetime | None
		update_job: DF.Link | None
		update_start: DF.Datetime | None
	# end: auto-generated types

	dashboard_fields: ClassVar = [
		"status",
		"site",
		"destination_bench",
		"source_bench",
		"deploy_type",
		"difference",
		"scheduled_time",
		"creation",
		"skipped_backups",
		"skipped_failing_patches",
		"backup_type",
		"physical_backup_restoration",
		"activate_site_job",
		"deactivate_site_job",
		"update_job",
		"recover_job",
		"update_start",
		"update_end",
		"update_duration",
	]

	@staticmethod
	def get_list_query(query):
		results = query.run(as_dict=True)
		for result in results:
			if result.updated_on:
				result.updated_on = convert_utc_to_system_timezone(result.updated_on).replace(tzinfo=None)

		return results

	def get_doc(self, doc):
		doc.steps = self.get_steps()
		return doc

	def validate(self):
		if not self.is_new():
			return

		# Assume same-group migration if destination_group isn't set
		if not self.destination_group:
			self.destination_group = self.group

		if self.group == self.destination_group:
			differences = frappe.get_all(
				"Deploy Candidate Difference",
				fields=["name", "destination", "deploy_type"],
				filters={"group": self.group, "source": self.source_candidate},
			)
			if not differences:
				frappe.throw("Could not find suitable Destination Bench", frappe.ValidationError)

			self.validate_destination_bench(differences)
			self.validate_deploy_candidate_difference(differences)
		else:
			self.validate_destination_bench([])
			# Forcefully migrate since we can't compute deploy_type reasonably
			self.deploy_type = "Migrate"

		self.validate_apps()
		self.validate_pending_updates()
		self.validate_past_failed_updates()
		self.set_physical_backup_mode_if_eligible()
		self.set_logical_replication_backup_mode_if_eligible()

	def validate_destination_bench(self, differences):
		if not self.destination_bench:
			candidates = [d.destination for d in differences]
			try:
				filters = {
					"server": self.server,
					"status": "Active",
					"group": self.destination_group,
				}
				if differences:
					filters["candidate"] = ("in", candidates)
					filters["name"] = ("!=", self.source_bench)

				destination_bench = frappe.get_all(
					"Bench", fields=["name", "candidate"], filters=filters, order_by="creation desc"
				)[0]
				self.destination_bench = destination_bench.name
				self.destination_candidate = destination_bench.candidate
			except Exception:
				frappe.throw("Could not find suitable Destination Bench", frappe.ValidationError)

	def validate_deploy_candidate_difference(self, differences):
		try:
			difference = find(differences, lambda x: x.destination == self.destination_candidate)
			self.difference = difference.name
			self.deploy_type = "Pull"
			difference_doc = frappe.get_doc("Deploy Candidate Difference", self.difference)
			site_doc: "Site" = frappe.get_doc("Site", self.site)
			for site_app in site_doc.apps:
				difference_app = find(difference_doc.apps, lambda x: x.app == site_app.app)
				if difference_app and difference_app.deploy_type == "Migrate":
					self.deploy_type = "Migrate"

		except Exception:
			frappe.throw(
				f"Could not find Deploy Candidate Difference from {self.source_bench}"
				f" to {self.destination_bench}",
				frappe.ValidationError,
			)

	def validate_pending_updates(self):
		if self.has_pending_updates():
			frappe.throw("An update is already pending for this site", frappe.ValidationError)

	@property
	def triggered_by_user(self):
		return frappe.session.user != "Administrator"

	@property
	def use_physical_backup(self):
		return self.backup_type == "Physical" and not self.skipped_backups

	@property
	def use_logical_replication_backup(self):
		return self.backup_type == "Logical Replication" and not self.skipped_backups

	def validate_past_failed_updates(self):
		if getattr(self, "ignore_past_failures", False):
			return

		if self.triggered_by_user:
			return  # Allow user to trigger update for same source and destination

		if not self.skipped_failing_patches and self.have_past_updates_failed():
			frappe.throw(
				f"Update from Source Candidate {self.source_candidate} to Destination"
				f" Candidate {self.destination_candidate} has failed in the past.",
				frappe.ValidationError,
			)

	def validate_apps(self):
		site_apps = [app.app for app in frappe.get_doc("Site", self.site).apps]
		bench_apps = [app.app for app in frappe.get_doc("Bench", self.destination_bench).apps]

		if diff := set(site_apps) - set(bench_apps):
			frappe.throw(
				f"Destination Bench {self.destination_bench} doesn't have some of the apps installed on {self.site}: {', '.join(diff)}",
				frappe.ValidationError,
			)

	def before_insert(self):
		self.backup_type = "Logical"
		site: "Site" = frappe.get_cached_doc("Site", self.site)
		site.check_move_scheduled()

	def after_insert(self):
		if not self.scheduled_time:
			self.start()

	def set_physical_backup_mode_if_eligible(self):  # noqa: C901
		if self.skipped_backups:
			return

		if self.deploy_type != "Migrate":
			return

		# Check if physical backup is disabled globally from Press Settings
		if frappe.utils.cint(frappe.get_value("Press Settings", None, "disable_physical_backup")):
			return

		database_server = frappe.get_value("Server", self.server, "database_server")
		if not database_server:
			# It might be the case of configured RDS server and no self hosted database server
			return

		# Check if physical backup is enabled on the database server
		enable_physical_backup = frappe.get_value(
			"Database Server", database_server, "enable_physical_backup"
		)
		if not enable_physical_backup:
			return

		# Sanity check - Provider should be AWS EC2
		provider = frappe.get_value("Database Server", database_server, "provider")
		if provider != "AWS EC2":
			return

		# In case of ebs encryption don't proceed with physical backup
		virtual_machine = frappe.get_value("Database Server", database_server, "virtual_machine")
		has_kms_key_id = frappe.get_value("Virtual Machine", virtual_machine, "kms_key_id")
		if has_kms_key_id:
			return

		# Check for last logical backup
		last_logical_site_backups = frappe.db.get_list(
			"Site Backup",
			filters={"site": self.site, "physical": False, "status": "Success"},
			pluck="database_size",
			limit=1,
			order_by="creation desc",
			ignore_permissions=True,
		)
		db_backup_size = 0
		if len(last_logical_site_backups) > 0:
			db_backup_size = cint(last_logical_site_backups[0])

		# If last logical backup size is greater than 300MB (actual db size approximate 3GB)
		# Then only take physical backup
		if db_backup_size > 314572800:
			self.backup_type = "Physical"

	def set_logical_replication_backup_mode_if_eligible(self):
		if self.skipped_backups:
			return

		if self.deploy_type != "Migrate":
			return

		database_server = frappe.get_value("Server", self.server, "database_server")
		if not database_server:
			# It might be the case of configured RDS server and no self hosted database server
			return

		# Sanity check - Provider should be AWS EC2
		provider = frappe.get_value("Database Server", database_server, "provider")
		if provider != "AWS EC2":
			return

		if not frappe.get_value("Server", self.server, "enable_logical_replication_during_site_update"):
			return

		self.backup_type = "Logical Replication"

	@dashboard_whitelist()
	def start(self):
		previous_status = self.status

		self.status = "Pending"
		self.update_start = frappe.utils.now()
		self.save()
		site: Site = frappe.get_cached_doc("Site", self.site)
		try:
			site.ready_for_move()
		except SiteAlreadyArchived:
			# There is no point in retrying the update if the site is already archived
			update_status(self.name, "Fatal")
			return
		except SiteUnderMaintenance:
			# Just ignore the update for now
			# It will be retried later
			if previous_status == "Pending":
				# During `Bench Update` and in some other cases
				# Site Update get status `Pending` with no `scheduled_time`
				# If we can't do the update right now in those cases
				# Then we should set the status to `Scheduled`
				# And set the `scheduled_time` to now
				self.status = "Scheduled"
				if not self.scheduled_time:
					self.scheduled_time = frappe.utils.now_datetime()
				self.save()
			else:
				update_status(self.name, previous_status)

			return

		if self.use_physical_backup:
			self.deactivate_site()
		elif self.use_logical_replication_backup:
			self.create_logical_replication_backup_record()
		else:
			self.create_update_site_agent_request()

	def get_before_migrate_scripts(self, rollback=False):
		site_apps = [app.app for app in frappe.get_doc("Site", self.site).apps]

		script_field = "before_migrate_script"
		if rollback:
			script_field = "rollback_script"

		scripts = {}
		for app_rename in frappe.get_all(
			"App Rename",
			{"new_name": ["in", site_apps], "enabled": True},
			["old_name", "new_name", script_field],
		):
			scripts[app_rename.old_name] = app_rename.get(script_field)

		return scripts

	@property
	def is_destination_above_v12(self):
		version = frappe.get_cached_value("Release Group", self.destination_group, "version")
		return frappe.get_cached_value("Frappe Version", version, "number") > 12

	def create_logical_replication_backup_record(self):
		record: LogicalReplicationBackup = frappe.get_doc(
			{"doctype": "Logical Replication Backup", "site": self.site, "execution_stage": "Pre-Migrate"}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Site Update", self.name, "logical_replication_backup", record.name)
		record.execute()

	def trigger_post_migration_stage_logical_replication_backup(self):
		if not self.logical_replication_backup:
			return
		record: LogicalReplicationBackup = frappe.get_doc(
			"Logical Replication Backup", self.logical_replication_backup
		)
		record.execution_stage = "Post-Migrate"
		record.status = "Pending"
		record.save()
		record.execute()

	def trigger_failover_stage_logical_replication_backup(self):
		if not self.logical_replication_backup:
			return
		record: LogicalReplicationBackup = frappe.get_doc(
			"Logical Replication Backup", self.logical_replication_backup
		)
		record.execution_stage = "Failover"
		record.status = "Pending"
		record.save()
		record.execute()

	def create_update_site_agent_request(self):
		agent = Agent(self.server)
		site = frappe.get_doc("Site", self.site)
		job = agent.update_site(
			site,
			self.destination_bench,
			self.deploy_type,
			skip_failing_patches=self.skipped_failing_patches,
			skip_backups=self.skipped_backups or self.backup_type in ["Physical", "Logical Replication"],
			before_migrate_scripts=self.get_before_migrate_scripts(),
			skip_search_index=self.is_destination_above_v12,
		)
		self.set_update_job_value(job)

	def set_update_job_value(self, job):
		frappe.db.set_value("Site Update", self.name, "update_job", job.name)
		site_activity = frappe.db.get_value(
			"Site Activity",
			{
				"site": self.site,
				"action": "Update",
				"job": ("is", "not set"),
			},
			order_by="creation desc",
		)
		if site_activity:
			frappe.db.set_value("Site Activity", site_activity, "job", job.name)

	def activate_site(self, backup_failed=False):
		agent = Agent(self.server)
		job = agent.activate_site(
			frappe.get_doc("Site", self.site), reference_doctype="Site Update", reference_name=self.name
		)
		frappe.db.set_value("Site Update", self.name, "activate_site_job", job.name)
		if backup_failed:
			update_status(self.name, "Fatal")

	def deactivate_site(self):
		agent = Agent(self.server)
		job = agent.deactivate_site(
			frappe.get_doc("Site", self.site), reference_doctype="Site Update", reference_name=self.name
		)
		frappe.db.set_value("Site Update", self.name, {"deactivate_site_job": job.name, "status": "Running"})

	def create_physical_backup(self):
		site: Site = frappe.get_doc("Site", self.site)
		frappe.db.set_value(
			"Site Update", self.name, "site_backup", site.physical_backup(for_site_update=True).name
		)

	def have_past_updates_failed(self):
		return frappe.db.exists(
			"Site Update",
			{
				"site": self.site,
				"source_candidate": self.source_candidate,
				"destination_candidate": self.destination_candidate,
				"cause_of_failure_is_resolved": False,
			},
		)

	def has_pending_updates(self):
		return frappe.db.exists(
			"Site Update",
			{
				"site": self.site,
				"status": ("in", ("Pending", "Running", "Failure", "Scheduled", "Recovering")),
			},
		)

	def is_workload_diff_high(self) -> bool:
		site_plan = frappe.get_value("Site", self.site, "plan")
		cpu = frappe.get_value("Site Plan", site_plan, "cpu_time_per_day") or 0  # if plan not set, assume 0

		THRESHOLD = 8  # USD 100 site equivalent. (Since workload is based off of CPU)

		workload_diff_high = cpu >= THRESHOLD

		if not workload_diff_high:
			source_bench = frappe.get_doc("Bench", self.source_bench)
			dest_bench = frappe.get_doc("Bench", self.destination_bench)
			workload_diff_high = (dest_bench.workload - source_bench.workload) > THRESHOLD

		return workload_diff_high

	def reallocate_workers(self):
		"""
		Reallocate workers on source and destination benches

		Do it for private benches only now as there'll be too many worker updates for public benches
		"""
		group = frappe.get_doc("Release Group", self.destination_group)

		if group.public or group.central_bench or not self.is_workload_diff_high():
			return

		frappe.enqueue_doc(
			"Server",
			self.server,
			method="auto_scale_workers",
			job_id=f"auto_scale_workers:{self.server}",
			deduplicate=True,
			enqueue_after_commit=True,
			at_front=True,
		)

	@property
	def touched_tables_list(self):
		try:
			return json.loads(self.touched_tables)
		except Exception:
			return []

	@frappe.whitelist()
	def trigger_recovery_job(self):  # noqa: C901
		if self.recover_job:
			return
		agent = Agent(self.server)
		site: "Site" = frappe.get_doc("Site", self.site)
		job = None
		if site.bench == self.destination_bench:
			# The site is already on destination bench
			update_status(self.name, "Recovering")
			frappe.db.set_value("Site", self.site, "status", "Recovering")

			# If physical backup is enabled, we need to first perform physical backup restoration
			if self.use_physical_backup and not self.physical_backup_restoration:
				# Perform Physical Backup Restoration if not already done
				doc: PhysicalBackupRestoration = frappe.get_doc(
					{
						"doctype": "Physical Backup Restoration",
						"site": self.site,
						"status": "Pending",
						"site_backup": self.site_backup,
						"source_database": site.database_name,
						"destination_database": site.database_name,
						"destination_server": frappe.get_value("Server", site.server, "database_server"),
						"restore_specific_tables": len(self.touched_tables_list) > 0,
						"tables_to_restore": json.dumps(self.touched_tables_list),
					}
				)
				doc.insert(ignore_permissions=True)
				frappe.db.set_value(self.doctype, self.name, "physical_backup_restoration", doc.name)
				doc.execute()
				# After physical backup restoration, that will trigger recovery job again
				# via site_update.process_physical_backup_restoration_status_update(...) method
				return

			# If logical replication backup is enabled, we need to first perform failover stage
			if (
				self.use_logical_replication_backup
				and frappe.get_value(
					"Logical Replication Backup", self.logical_replication_backup, "failover_stage_status"
				)
				== "Pending"
			):
				self.trigger_failover_stage_logical_replication_backup()
				return

			if not self.skipped_backups and self.physical_backup_restoration:
				physical_backup_restoration_status = frappe.get_value(
					"Physical Backup Restoration", self.physical_backup_restoration, "status"
				)
				if physical_backup_restoration_status == "Failure":
					# mark site update as Fatal
					update_status(self.name, "Fatal")
					# mark site as broken
					frappe.db.set_value("Site", self.site, "status", "Broken")
					return
				if physical_backup_restoration_status != "Success":
					# just to be safe
					frappe.throw("Physical Backup Restoration is still in progress")

			# Attempt to move site to source bench

			# Disable maintenance mode for active sites
			activate = site.status_before_update == "Active"
			job = agent.update_site_recover_move(
				site,
				self.source_bench,
				self.deploy_type,
				activate,
				rollback_scripts=self.get_before_migrate_scripts(rollback=True),
				restore_touched_tables=(not self.skipped_backups and self.backup_type == "Logical"),
			)
		else:
			# Site is already on the source bench
			if site.status_before_update == "Active":
				# Disable maintenance mode for active sites
				job = agent.update_site_recover(site)
			else:
				# Site is already on source bench and maintenance mode is on
				# No need to do anything
				site.reset_previous_status()
				update_status(self.name, "Recovered")
		if job:
			frappe.db.set_value("Site Update", self.name, "recover_job", job.name)

	def delete_backup_snapshot(self):
		if self.site_backup:
			snapshot = frappe.get_value("Site Backup", self.site_backup, "database_snapshot")
			if snapshot:
				frappe.get_doc("Virtual Disk Snapshot", snapshot).delete_snapshot()

	@dashboard_whitelist()
	def get_steps(self):  # noqa: C901
		"""
		{
			"title": "Step Name",
			"status": "Success",
			"output": "Output",
		}
		TODO > Add duration of each step

		Expand the steps of job
		- Steps of Deactivate Job [if exists]
		- Steps of Physical Backup Job [Site Backup] [if exists]
		- Steps of Update Job
		- Steps of Physical Restore Job [if exists]
		- Steps of Recovery Job [if exists]
		- Steps of Activate Job [if exists]
		"""
		steps = []
		if self.deactivate_site_job:
			steps.extend(self.get_job_steps(self.deactivate_site_job, "Deactivate Site"))
		if self.backup_type == "Physical" and self.site_backup:
			if frappe.db.exists("Site Backup", self.site_backup):
				agent_job = frappe.get_value("Site Backup", self.site_backup, "job")
				steps.extend(self.get_job_steps(agent_job, "Backup Site"))
			else:
				steps.append(
					{
						"name": "site_backup_not_found",
						"title": "Backup Cleared",
						"status": "Skipped",
						"output": "",
						"stage": "Physical Backup",
					}
				)

		if (
			self.logical_replication_backup
			and frappe.db.get_value(
				"Logical Replication Backup", self.logical_replication_backup, "pre_migrate_stage_status"
			)
			!= "Pending"
		):
			steps.extend(
				get_logical_replication_backup_restoration_steps(
					self.logical_replication_backup, "Pre-Migrate"
				)
			)

		if self.update_job:
			steps.extend(self.get_job_steps(self.update_job, "Update Site"))

		if (
			self.logical_replication_backup
			and frappe.db.get_value(
				"Logical Replication Backup", self.logical_replication_backup, "post_migrate_stage_status"
			)
			!= "Pending"
		):
			steps.extend(
				get_logical_replication_backup_restoration_steps(
					self.logical_replication_backup, "Post-Migrate"
				)
			)

		if self.physical_backup_restoration:
			steps.extend(get_physical_backup_restoration_steps(self.physical_backup_restoration))

		if self.recover_job:
			steps.extend(self.get_job_steps(self.recover_job, "Recover Site"))

		if (
			self.logical_replication_backup
			and frappe.db.get_value(
				"Logical Replication Backup", self.logical_replication_backup, "failover_stage_status"
			)
			!= "Pending"
		):
			steps.extend(
				get_logical_replication_backup_restoration_steps(self.logical_replication_backup, "Failover")
			)

		if self.activate_site_job:
			steps.extend(self.get_job_steps(self.activate_site_job, "Activate Site"))
		return steps

	def get_job_steps(self, job: str, stage: str):
		agent_steps = frappe.get_all(
			"Agent Job Step",
			filters={"agent_job": job},
			fields=["output", "step_name", "status", "name"],
			order_by="creation asc",
		)
		return [
			{
				"name": step.get("name"),
				"title": step.get("step_name"),
				"status": step.get("status"),
				"output": step.get("output"),
				"stage": stage,
			}
			for step in agent_steps
		]

	@frappe.whitelist()
	def set_cause_of_failure_is_resolved(self):
		frappe.db.set_value("Site Update", self.name, "cause_of_failure_is_resolved", 1)

	@frappe.whitelist()
	def set_status(self, status):
		return self.update_status(self.name, status)

	@classmethod
	def update_status(cls, name, status):
		if status == "Cancelled":
			try:
				if (
					_status := frappe.db.get_value("Site Update", name, "status", for_update=True, wait=False)
				) != "Scheduled":
					frappe.throw(f"Cannot cancel a Site Update with status {_status}")

			except (frappe.QueryTimeoutError, frappe.QueryDeadlockError):
				frappe.throw(
					"The update is probably underway. Please reload/refresh to get the latest status."
				)

		frappe.db.set_value("Site Update", name, "status", status)

	@classmethod
	def get_ongoing_update(cls, job_name: str) -> OngoingUpdate | None:
		updates: list[OngoingUpdate] = frappe.get_all(
			"Site Update",
			fields=["name", "status", "destination_bench", "destination_group", "backup_type"],
			filters={"update_job": job_name},
		)
		if updates:
			return updates[0]
		return None


def update_status(name: str, status: str):
	SiteUpdate.update_status(name, status)
	if status in ("Success", "Failure", "Fatal", "Recovered"):
		frappe.db.set_value("Site Update", name, "update_end", frappe.utils.now())
		update_start = frappe.db.get_value("Site Update", name, "update_start")
		if update_start:
			frappe.db.set_value(
				"Site Update",
				name,
				"update_duration",
				frappe.utils.cint(
					frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), update_start)
				),
			)
	if status in ["Success", "Recovered"]:
		backup_type = frappe.db.get_value("Site Update", name, "backup_type")
		if backup_type == "Physical":
			# Remove the snapshot
			frappe.enqueue_doc(
				"Site Update",
				name,
				"delete_backup_snapshot",
				enqueue_after_commit=True,
			)


@site_cache(ttl=60)
def benches_with_available_update(site=None, server=None):
	site_bench = frappe.db.get_value("Site", site, "bench") if site else None
	values = {}
	if site:
		values["site_bench"] = site_bench
	if server:
		values["server"] = server
	source_benches_info = frappe.db.sql(
		"""
		SELECT sb.name AS source_bench, sb.candidate AS source_candidate, sb.server AS server, dcd.destination AS destination_candidate
		FROM `tabBench` sb, `tabDeploy Candidate Difference` dcd
		WHERE sb.status IN ('Active', 'Broken') AND sb.candidate = dcd.source
		AND (%(site_bench)s IS NULL OR sb.name = %(site_bench)s)
		AND (%(server)s IS NULL OR sb.server = %(server)s)
		""",
		values=values,
		as_dict=True,
	)

	destination_candidates = list(set(d["destination_candidate"] for d in source_benches_info))

	destination_benches_info = frappe.get_all(
		"Bench",
		filters={"status": "Active", "candidate": ("in", destination_candidates)},
		fields=["candidate AS destination_candidate", "name AS destination_bench", "server"],
		ignore_ifnull=True,
	)

	destinations = set()
	for bench in destination_benches_info:
		destinations.add((bench.destination_candidate, bench.server))

	updates_available_for_benches = []
	for bench in source_benches_info:
		if (bench.destination_candidate, bench.server) in destinations:
			updates_available_for_benches.append(bench)

	return list(set([bench.source_bench for bench in updates_available_for_benches]))


@frappe.whitelist()
def sites_with_available_update(server=None):
	benches = benches_with_available_update(server=server)
	return frappe.get_all(
		"Site",
		filters={
			"status": ("in", ("Active", "Inactive", "Suspended")),
			"bench": ("in", benches),
			"only_update_at_specified_time": False,  # will be taken care of by another scheduled job
			"skip_auto_updates": False,
		},
		fields=["name", "timezone", "bench", "server", "status"],
	)


def schedule_updates():
	servers = frappe.get_all("Server", {"status": "Active"}, pluck="name")
	for server in servers:
		frappe.enqueue(
			"press.press.doctype.site_update.site_update.schedule_updates_server",
			server=server,
			job_id=f"schedule_updates:{server}",
			deduplicate=True,
			queue="long",
		)


def schedule_updates_server(server):
	# Prevent flooding the queue
	queue_size = frappe.db.get_single_value("Press Settings", "auto_update_queue_size")
	pending_update_count = frappe.db.count(
		"Site Update",
		{
			"status": ("in", ("Pending", "Running")),
			"server": server,
			"creation": (">", frappe.utils.add_to_date(None, hours=-4)),
		},
	)
	if pending_update_count > queue_size:
		return

	sites = sites_with_available_update(server)
	sites = list(filter(is_site_in_deploy_hours, sites))

	# If a site can't be updated for some reason, then we shouldn't get stuck
	# Shuffle sites list, to achieve this
	random.shuffle(sites)

	benches = {}
	update_triggered_count = 0
	for site in sites:
		if site.bench in benches:
			continue
		if update_triggered_count > queue_size:
			break
		if not should_try_update(site) or frappe.db.exists(
			"Site Update",
			{
				"site": site.name,
				"status": ("in", ("Pending", "Running", "Failure", "Scheduled")),
			},
		):
			continue

		try:
			site = frappe.get_doc("Site", site.name)
			if site.site_migration_scheduled():
				continue
			site.schedule_update()
			update_triggered_count += 1
			frappe.db.commit()
			benches[site.bench] = True
		except Exception:
			log_error("Site Update Exception", site=site)
			frappe.db.rollback()


def should_try_update(site):
	source = frappe.db.get_value("Bench", site.bench, "candidate")
	candidates = frappe.get_all(
		"Deploy Candidate Difference", filters={"source": source}, pluck="destination"
	)

	source_apps = [app.app for app in frappe.get_cached_doc("Site", site.name).apps]
	dest_apps = []
	destinations = frappe.get_all(
		"Bench",
		["name", "candidate"],
		{
			"candidate": ("in", candidates),
			"status": "Active",
			"server": site.server,
		},
		limit=1,
		ignore_ifnull=True,
		order_by="creation DESC",
	)
	# Most recent active bench is the destination bench
	if not destinations:
		return False

	destination_bench = frappe.get_cached_doc("Bench", destinations[0].name)
	dest_apps = [app.app for app in destination_bench.apps]

	if set(source_apps) - set(dest_apps):
		return False

	return not frappe.db.exists(
		"Site Update",
		{
			"site": site.name,
			"source_candidate": source,
			"destination_candidate": destination_bench.candidate,
			"cause_of_failure_is_resolved": False,
		},
	)


def is_site_in_deploy_hours(site):
	if site.status in ("Inactive", "Suspended"):
		return True
	server_time = datetime.now()
	timezone = site.timezone or "Asia/Kolkata"
	site_timezone = pytz.timezone(timezone)
	site_time = server_time.astimezone(site_timezone)
	deploy_hours = frappe.get_hooks("deploy_hours")

	if site_time.hour in deploy_hours:
		return True
	return False


def process_physical_backup_restoration_status_update(name: str):
	site_backup_name = frappe.db.exists(
		"Site Update",
		{
			"physical_backup_restoration": name,
		},
	)
	if site_backup_name:
		site_update: SiteUpdate = frappe.get_doc("Site Update", site_backup_name)
		physical_backup_restoration: PhysicalBackupRestoration = frappe.get_doc(
			"Physical Backup Restoration", name
		)
		if physical_backup_restoration.status in ["Success", "Failure"]:
			site_update.trigger_recovery_job()


def process_activate_site_job_update(job: AgentJob):
	if job.reference_doctype != "Site Update" or not job.reference_name:
		return
	if job.status == "Success":
		# If `Site Update` successful, then mark site as `Active`
		if frappe.db.get_value(job.reference_doctype, job.reference_name, "status") == "Success":
			frappe.get_doc("Site", job.site).reset_previous_status(fix_broken=True)
		else:
			# Set status to `status_before_update`
			frappe.get_doc("Site", job.site).reset_previous_status()
	elif job.status in ["Failure", "Delivery Failure"]:
		# Mark the site as broken
		frappe.db.set_value("Site", job.site, "status", "Broken")
		update_status(job.reference_name, "Fatal")


def process_deactivate_site_job_update(job):
	if job.reference_doctype != "Site Update":
		return
	if job.status == "Success":
		# proceed to backup stage
		site_update = frappe.get_doc("Site Update", job.reference_name)
		site_update.create_physical_backup()
	elif job.status in ["Failure", "Delivery Failure"]:
		# mark Site Update as Fatal
		update_status(job.reference_name, "Fatal")
		# Run the activate site to ensure site is active
		site_update = frappe.get_doc("Site Update", job.reference_name)
		site_update.activate_site()


def update_site_bench_group_fields(job: AgentJob, site_update: OngoingUpdate):
	if not job.site:
		raise NotImplementedError
	bench = frappe.db.get_value("Site", job.site, "bench")
	move_site_step_status = frappe.db.get_value(
		"Agent Job Step", {"step_name": "Move Site", "agent_job": job.name}, "status"
	)
	if bench != site_update.destination_bench and move_site_step_status == "Success":
		frappe.db.set_value("Site", job.site, "bench", site_update.destination_bench)
		frappe.db.set_value("Site", job.site, "group", site_update.destination_group)


def reallocate_workers_if_moved(job: AgentJob, site_update: OngoingUpdate):
	site_enable_step_status = frappe.db.get_value(
		"Agent Job Step",
		{"step_name": "Disable Maintenance Mode", "agent_job": job.name},
		"status",
	)
	if site_enable_step_status == "Success":
		SiteUpdate("Site Update", site_update.name).reallocate_workers()


def update_touched_tables_step(job: AgentJob, site_update: OngoingUpdate):
	log_touched_tables_step = frappe.db.get_value(
		"Agent Job Step",
		{"step_name": "Log Touched Tables", "agent_job": job.name},
		["status", "data"],
		as_dict=True,
	)
	if log_touched_tables_step and log_touched_tables_step.status == "Success":
		frappe.db.set_value("Site Update", site_update.name, "touched_tables", log_touched_tables_step.data)


def handle_success(job: AgentJob, site_update: OngoingUpdate):
	if site_update.backup_type == "Logical Replication":
		SiteUpdate("Site Update", site_update.name).trigger_post_migration_stage_logical_replication_backup()
	else:
		frappe.get_doc("Site", job.site).reset_previous_status(fix_broken=True)


def handle_fatal(job: AgentJob, site_update: OngoingUpdate):
	if site_update.backup_type in ["Physical", "Logical Replication"]:
		# For Physical restore, just do activate site
		# Because we have deactivated site first
		SiteUpdate("Site Update", site_update.name).activate_site()
	else:
		# For Logical restore, we need to reset site status just
		frappe.get_doc("Site", job.site).reset_previous_status()


def handle_failure(job: AgentJob, site_update: OngoingUpdate):
	frappe.db.set_value("Site", job.site, "status", "Broken")
	frappe.db.set_value(
		"Site Update",
		site_update.name,
		"cause_of_failure_is_resolved",
		job.failed_because_of_agent_update or job.failed_because_of_incident,
	)
	if not frappe.db.get_value("Site Update", site_update.name, "skipped_backups"):
		doc = SiteUpdate("Site Update", site_update.name)
		doc.trigger_recovery_job()
	else:
		# If user has done Site Update with skipped_backups
		# We have nothing to do here
		update_status(site_update.name, "Fatal")
		SiteUpdate("Site Update", site_update.name).reallocate_workers()


class OngoingUpdate(frappe._dict):
	name: str
	status: str
	destination_bench: str
	destination_group: str
	backup_type: str


def process_update_site_job_update(job: AgentJob):
	site_update = SiteUpdate.get_ongoing_update(job.name)
	if not site_update:
		return
	updated_status = {
		# For physical backup, we have already deactivated site first
		# So no point in setting status back to Pending
		"Pending": "Running" if site_update.backup_type in ["Physical", "Logical Replication"] else "Pending",
		"Running": "Running",
		"Success": "Success",
		"Failure": "Failure",
		"Delivery Failure": "Fatal",
	}[job.status]

	if updated_status != site_update.status:
		update_site_bench_group_fields(job, site_update)
		reallocate_workers_if_moved(job, site_update)
		update_touched_tables_step(job, site_update)

		if not (site_update.backup_type == "Logical Replication" and updated_status == "Success"):
			update_status(site_update.name, updated_status)
		if updated_status == "Running":
			frappe.db.set_value("Site", job.site, "status", "Updating")
		elif updated_status == "Success":
			handle_success(job, site_update)
		elif updated_status == "Fatal":
			handle_fatal(job, site_update)
		elif updated_status == "Failure":
			handle_failure(job, site_update)


def process_update_site_recover_job_update(job: AgentJob):
	updated_status = {
		"Pending": "Recovering",
		"Running": "Recovering",
		"Success": "Recovered",
		"Failure": "Fatal",
		"Delivery Failure": "Fatal",
	}[job.status]
	site_update = frappe.get_all(
		"Site Update",
		fields=["name", "status", "source_bench", "group"],
		filters={"recover_job": job.name},
	)[0]
	if updated_status != site_update.status:
		site_bench = frappe.db.get_value("Site", job.site, "bench")
		move_site_step_status = frappe.db.get_value(
			"Agent Job Step", {"step_name": "Move Site", "agent_job": job.name}, "status"
		)
		if site_bench != site_update.source_bench and move_site_step_status == "Success":
			frappe.db.set_value("Site", job.site, "bench", site_update.source_bench)
			frappe.db.set_value("Site", job.site, "group", site_update.group)

		update_status(site_update.name, updated_status)

		if updated_status == "Recovering":
			frappe.db.set_value("Site", job.site, "status", "Recovering")
		elif updated_status == "Recovered":
			frappe.get_doc("Site", job.site).reset_previous_status()
		elif updated_status == "Fatal":
			frappe.db.set_value("Site", job.site, "status", "Broken")


def mark_stuck_updates_as_fatal():
	frappe.db.set_value(
		"Site Update",
		{
			"status": ("in", ["Pending", "Running", "Failure"]),
			"modified": ("<", frappe.utils.add_days(None, -2)),
		},
		"status",
		"Fatal",
	)


def run_scheduled_updates():
	updates = frappe.get_all(
		"Site Update",
		{"scheduled_time": ("<=", frappe.utils.now()), "status": "Scheduled"},
		pluck="name",
	)

	for update in updates:
		try:
			site_update: SiteUpdate = frappe.get_doc("Site Update", update, for_update=True)
			if site_update.status != "Scheduled":
				continue

			site_update.validate()
			site_update.start()
			frappe.db.commit()
		except Exception:
			log_error("Scheduled Site Update Error", update=update)
			frappe.db.rollback()


def on_doctype_update():
	frappe.db.add_index("Site Update", ["site", "source_candidate", "destination_candidate"])
	frappe.db.add_index("Site Update", ["server", "status"])


def process_callback_from_logical_replication_backup(backup: "LogicalReplicationBackup"):  # noqa: C901
	site_update_name = frappe.db.exists("Site Update", {"logical_replication_backup": backup.name})
	if not site_update_name:
		return
	site_update: "SiteUpdate" = frappe.get_doc("Site Update", site_update_name)
	"""
	Site Update Statuses:

	Pending > Stage before migration
			During transitioning to Pending state, we create the logical replication backup record
	Running > Steps during actual site migration
	Success > Migration Done ! Run Post Migration Steps
	Failure > Migration Failed ! Run Failover
	"""
	if site_update.status == "Pending":
		if backup.pre_migrate_stage_status == "Success":
			site_update.create_update_site_agent_request()
		elif backup.pre_migrate_stage_status == "Failure":
			site_update.activate_site(backup_failed=True)

	elif site_update.status == "Running":
		# Site update is in Running stage because
		# After successful migration we will set `Site Update` status to `Running`
		# And trigger post_migration

		# Irrespective of post_migrate stage status,
		# Site Update should be marked as Success
		if backup.post_migrate_stage_status in ["Success", "Failure"]:
			site_update.activate_site()

	elif site_update.status == "Recovering":
		if backup.failover_stage_status == "Success":
			site_update.trigger_recovery_job()
		elif backup.failover_stage_status == "Failure":
			update_status(site_update.name, "Fatal")
			frappe.db.set_value("Site", backup.site, "status", "Broken")
