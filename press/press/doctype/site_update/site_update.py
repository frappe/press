# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import random
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

import frappe
import pytz
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils import convert_utc_to_system_timezone
from frappe.utils.caching import site_cache

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site


class SiteUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cause_of_failure_is_resolved: DF.Check
		deploy_type: DF.Literal["", "Pull", "Migrate"]
		destination_bench: DF.Link | None
		destination_candidate: DF.Link | None
		destination_group: DF.Link | None
		difference: DF.Link | None
		difference_deploy_type: DF.Literal["", "Pull", "Migrate"]
		group: DF.Link | None
		recover_job: DF.Link | None
		scheduled_time: DF.Datetime | None
		server: DF.Link | None
		site: DF.Link | None
		skipped_backups: DF.Check
		skipped_failing_patches: DF.Check
		source_bench: DF.Link | None
		source_candidate: DF.Link | None
		status: DF.Literal["Pending", "Running", "Success", "Failure", "Recovered", "Fatal", "Scheduled"]
		team: DF.Link | None
		update_job: DF.Link | None
	# end: auto-generated types

	dashboard_fields: ClassVar = [
		"status",
		"site",
		"destination_bench",
		"source_bench",
		"deploy_type",
		"difference",
		"update_job",
		"scheduled_time",
		"creation",
		"skipped_backups",
		"skipped_failing_patches",
	]

	@staticmethod
	def get_list_query(query):
		results = query.run(as_dict=True)
		for result in results:
			if result.updated_on:
				result.updated_on = convert_utc_to_system_timezone(result.updated_on).replace(tzinfo=None)

		return results

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
		site: "Site" = frappe.get_cached_doc("Site", self.site)
		site.check_move_scheduled()

	def after_insert(self):
		if not self.scheduled_time:
			self.start()

	@dashboard_whitelist()
	def start(self):
		self.status = "Pending"
		self.save()
		site: "Site" = frappe.get_cached_doc("Site", self.site)
		site.ready_for_move()
		self.create_agent_request()

	def get_before_migrate_scripts(self, rollback=False):
		site_apps = [app.app for app in frappe.get_doc("Site", self.site).apps]

		script_field = "before_migrate_script"
		if rollback:
			script_field = "rollback_script"

		scripts = {}
		for app_rename in frappe.get_all(
			"App Rename", {"new_name": ["in", site_apps]}, ["old_name", "new_name", script_field]
		):
			scripts[app_rename.old_name] = app_rename.get(script_field)

		return scripts

	@property
	def is_destination_above_v12(self):
		version = frappe.get_cached_value("Release Group", self.destination_group, "version")
		return frappe.get_cached_value("Frappe Version", version, "number") > 12

	def create_agent_request(self):
		agent = Agent(self.server)
		site = frappe.get_doc("Site", self.site)
		job = agent.update_site(
			site,
			self.destination_bench,
			self.deploy_type,
			skip_failing_patches=self.skipped_failing_patches,
			skip_backups=self.skipped_backups,
			before_migrate_scripts=self.get_before_migrate_scripts(),
			skip_search_index=self.is_destination_above_v12,
		)
		self.set_job_value(job)

	def set_job_value(self, job):
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
				"status": ("in", ("Pending", "Running", "Failure", "Scheduled")),
			},
		)

	def reallocate_workers(self):
		"""
		Reallocate workers on source and destination benches

		Do it for private benches only now as there'll be too many worker updates for public benches
		"""
		group = frappe.get_doc("Release Group", self.destination_group)

		if group.public or group.central_bench:
			return

		server = frappe.get_doc("Server", self.server)
		source_bench = frappe.get_doc("Bench", self.source_bench)
		dest_bench = frappe.get_doc("Bench", self.destination_bench)

		workload_diff = dest_bench.workload - source_bench.workload
		if (
			server.new_worker_allocation
			and workload_diff >= 8  # USD 100 site equivalent. (Since workload is based off of CPU)
		):
			frappe.enqueue_doc(
				"Server",
				server.name,
				method="auto_scale_workers",
				job_id=f"auto_scale_workers:{server.name}",
				deduplicate=True,
				enqueue_after_commit=True,
				at_front=True,
			)

	@frappe.whitelist()
	def trigger_recovery_job(self):
		trigger_recovery_job(self.name)


def trigger_recovery_job(site_update_name):
	site_update: "SiteUpdate" = frappe.get_doc("Site Update", site_update_name)
	if site_update.recover_job:
		return
	agent = Agent(site_update.server)
	site: "Site" = frappe.get_doc("Site", site_update.site)
	job = None
	if site.bench == site_update.destination_bench:
		# The site is already on destination bench
		# Attempt to move site to source bench

		# Disable maintenance mode for active sites
		activate = site.status_before_update == "Active"
		job = agent.update_site_recover_move(
			site,
			site_update.source_bench,
			site_update.deploy_type,
			activate,
			rollback_scripts=site_update.get_before_migrate_scripts(rollback=True),
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
	if job:
		frappe.db.set_value("Site Update", site_update_name, "recover_job", job.name)


@site_cache(ttl=60)
def benches_with_available_update(site=None, server=None):
	site_bench = frappe.db.get_value("Site", site, "bench") if site else None
	values = {}
	if site:
		values["site_bench"] = site_bench
	if server:
		values["server"] = server
	source_benches_info = frappe.db.sql(
		f"""
		SELECT sb.name AS source_bench, sb.candidate AS source_candidate, sb.server AS server, dcd.destination AS destination_candidate
		FROM `tabBench` sb, `tabDeploy Candidate Difference` dcd
		WHERE sb.status IN ('Active', 'Broken') AND sb.candidate = dcd.source
		{'AND sb.name = %(site_bench)s' if site else ''}
		{'AND sb.server = %(server)s' if server else ''}
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


def process_update_site_job_update(job):  # noqa: C901
	updated_status = job.status
	site_update = frappe.get_all(
		"Site Update",
		fields=["name", "status", "destination_bench", "destination_group"],
		filters={"update_job": job.name},
	)

	if not site_update:
		return

	site_update = site_update[0]

	if updated_status != site_update.status:
		site_bench = frappe.db.get_value("Site", job.site, "bench")
		move_site_step_status = frappe.db.get_value(
			"Agent Job Step", {"step_name": "Move Site", "agent_job": job.name}, "status"
		)
		if site_bench != site_update.destination_bench and move_site_step_status == "Success":
			frappe.db.set_value("Site", job.site, "bench", site_update.destination_bench)
			frappe.db.set_value("Site", job.site, "group", site_update.destination_group)
		site_enable_step_status = frappe.db.get_value(
			"Agent Job Step",
			{"step_name": "Disable Maintenance Mode", "agent_job": job.name},
			"status",
		)
		if site_enable_step_status == "Success":
			frappe.get_doc("Site Update", site_update.name).reallocate_workers()

		frappe.db.set_value("Site Update", site_update.name, "status", updated_status)
		if updated_status == "Running":
			frappe.db.set_value("Site", job.site, "status", "Updating")
		elif updated_status == "Success":
			frappe.get_doc("Site", job.site).reset_previous_status(fix_broken=True)
		elif updated_status == "Delivery Failure":
			frappe.get_doc("Site", job.site).reset_previous_status()
		elif updated_status == "Failure":
			frappe.db.set_value("Site", job.site, "status", "Broken")
			if not frappe.db.get_value("Site Update", site_update.name, "skipped_backups"):
				trigger_recovery_job(site_update.name)
			else:
				frappe.db.set_value("Site Update", site_update.name, "status", "Fatal")

	if job.status == "Failure":
		send_job_failure_notification(job.name)


def process_update_site_recover_job_update(job):
	updated_status = {
		"Pending": "Pending",
		"Running": "Running",
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

		frappe.db.set_value("Site Update", site_update.name, "status", updated_status)
		if updated_status == "Recovered":
			frappe.get_doc("Site", job.site).reset_previous_status()
		elif updated_status == "Fatal":
			frappe.db.set_value("Site", job.site, "status", "Broken")

	if job.status == "Failure":
		send_job_failure_notification(job.name)


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
			doc = frappe.get_doc("Site Update", update)
			doc.validate()
			doc.start()
			frappe.db.commit()
		except Exception:
			log_error("Scheduled Site Update Error", update=update)
			frappe.db.rollback()


def send_job_failure_notification(job_name):
	from press.press.doctype.press_notification.press_notification import (
		create_new_notification,
	)

	job_site, job_type = frappe.db.get_value("Agent Job", job_name, ["site", "job_type"])
	notification_type, message = "", ""

	if job_type == "Update Site Migrate":
		notification_type = "Site Migrate"
		message = f"Site <b>{job_site}</b> failed to migrate"
	elif job_type == "Update Site Pull":
		notification_type = "Site Update"
		message = f"Site <b>{job_site}</b> failed to update"
	elif job_type.startswith("Recover Failed"):
		notification_type = "Site Recovery"
		message = f"Site <b>{job_site}</b> failed to recover after a failed update/migration"

	if notification_type:
		create_new_notification(
			frappe.get_value("Site", job_site, "team"),
			notification_type,
			"Agent Job",
			job_name,
			message,
		)


def on_doctype_update():
	frappe.db.add_index("Site Update", ["site", "source_candidate", "destination_candidate"])
	frappe.db.add_index("Site Update", ["server", "status"])
