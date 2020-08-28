# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import random
import frappe
from datetime import datetime
from frappe.model.document import Document
from frappe.core.utils import find
import pytz
from press.agent import Agent
from press.utils import log_error


class SiteUpdate(Document):
	def validate(self):
		if not self.is_new():
			return
		differences = frappe.get_all(
			"Deploy Candidate Difference",
			fields=["name", "destination", "deploy_type"],
			filters={"group": self.group, "source": self.source_candidate},
		)
		if not differences:
			frappe.throw("Could not find suitable Destination Bench", frappe.ValidationError)
		if not self.destination_bench:
			candidates = [d.destination for d in differences]
			try:
				destination_bench = frappe.get_all(
					"Bench",
					fields=["name", "candidate"],
					filters={
						"server": self.server,
						"status": "Active",
						"group": self.group,
						"name": ("!=", self.source_bench),
						"candidate": ("in", candidates),
					},
				)[0]
				self.destination_bench = destination_bench.name
				self.destination_candidate = destination_bench.candidate
			except Exception:
				frappe.throw("Could not find suitable Destination Bench", frappe.ValidationError)

		try:
			difference = find(differences, lambda x: x.destination == self.destination_candidate)
			self.difference = difference.name
			self.deploy_type = "Pull"
			difference_doc = frappe.get_doc("Deploy Candidate Difference", self.difference)
			site_doc = frappe.get_doc("Site", self.site)
			for site_app in site_doc.apps:
				difference_app = find(difference_doc.apps, lambda x: x.app == site_app.app)
				if difference_app.changed and difference_app.deploy_type == "Migrate":
					self.deploy_type = "Migrate"

		except Exception:
			frappe.throw(
				f"Could not find Deploy Candidate Difference from {self.source_bench}"
				f" to {self.destination_bench}",
				frappe.ValidationError,
			)

		if self.has_pending_updates():
			frappe.throw(
				"An update is already pending for this site",
				frappe.ValidationError,
			)

		if self.have_past_updates_failed():
			frappe.throw(
				f"Update from Source Candidate {self.source_candidate} to Destination"
				f" Candidate {self.destination_candidate} has failed in the past.",
				frappe.ValidationError,
			)

	def after_insert(self):
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.server)
		site = frappe.get_doc("Site", self.site)
		job = agent.update_site(site, self.destination_bench, self.deploy_type)
		self.update_job = job.name
		self.save()

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
				"status": ("in", ("Pending", "Running", "Failure"))
			},
		)


def trigger_recovery_job(site_update_name):
	site_update = frappe.get_doc("Site Update", site_update_name)
	if site_update.recover_job:
		return
	agent = Agent(site_update.server)
	site = frappe.get_doc("Site", site_update.site)
	job = None
	if site.bench == site_update.destination_bench:
		# The site is already on destination bench
		# Attempt to move site to source bench

		# Disable maintenance mode for active sites
		activate = site.status_before_update == "Active"
		job = agent.update_site_recover_move(
			site, site_update.source_bench, site_update.deploy_type, activate
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


def benches_with_available_update():
	active_destination_benches = frappe.get_all(
		"Bench", filters={"status": "Active"}, fields=["candidate"],
	)

	active_destination_candidates = list(
		set(bench.candidate for bench in active_destination_benches)
	)

	source_differences = frappe.get_all(
		"Deploy Candidate Difference",
		fields=["source"],
		filters={"destination": ("in", active_destination_candidates)},
	)
	source_candidates = list(set(source.source for source in source_differences))
	benches = frappe.get_all(
		"Bench", filters={"status": "Active", "candidate": ("in", source_candidates)},
	)
	return list(set(bench.name for bench in benches))


def sites_with_available_update():
	benches = benches_with_available_update()
	sites = frappe.get_all(
		"Site",
		filters={
			"status": ("in", ("Active", "Inactive", "Suspended")),
			"bench": ("in", benches),
		},
		fields=["name", "timezone", "bench", "status"],
	)
	return sites


def schedule_updates():
	# Prevent flooding the queue
	queue_size = frappe.db.get_single_value("Press Settings", "auto_update_queue_size")
	pending_update_count = frappe.db.count(
		"Site Update", {"status": ("in", ("Pending", "Running"))}
	)
	if pending_update_count > queue_size:
		return

	sites = sites_with_available_update()
	sites = list(filter(is_site_in_deploy_hours, sites))
	sites = list(filter(should_try_update, sites))

	# If a site can't be updated for some reason, then we shouldn't get stuck
	# Shuffle sites list, to achieve this
	random.shuffle(sites)

	update_triggered_count = 0
	for site in sites:
		if update_triggered_count > queue_size:
			break
		try:
			site = frappe.get_doc("Site", site.name)
			site.schedule_update()
			update_triggered_count += 1
		except Exception:
			log_error("Site Update Exception", site=site)


def should_try_update(site):
	source = frappe.db.get_value("Bench", site.bench, "candidate")
	destination = frappe.get_all(
		"Deploy Candidate Difference",
		fields=["destination"],
		filters={"source": source},
		limit=1,
	)[0].destination
	return not frappe.db.exists(
		"Site Update",
		{
			"site": site.name,
			"source_candidate": source,
			"destination_candidate": destination,
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


def process_update_site_job_update(job):
	updated_status = {
		"Pending": "Pending",
		"Running": "Running",
		"Success": "Success",
		"Failure": "Failure",
	}[job.status]
	site_update = frappe.get_all(
		"Site Update",
		fields=["name", "status", "destination_bench"],
		filters={"update_job": job.name},
	)[0]
	if updated_status != site_update.status:
		site_bench = frappe.db.get_value("Site", job.site, "bench")
		move_site_step_status = frappe.db.get_value(
			"Agent Job Step", {"step_name": "Move Site", "agent_job": job.name}, "status"
		)
		if site_bench != site_update.destination_bench and move_site_step_status == "Success":
			frappe.db.set_value("Site", job.site, "bench", site_update.destination_bench)

		frappe.db.set_value("Site Update", site_update.name, "status", updated_status)
		if updated_status == "Running":
			frappe.db.set_value("Site", job.site, "status", "Updating")
		elif updated_status == "Success":
			frappe.get_doc("Site", job.site).reset_previous_status()
		elif updated_status == "Failure":
			frappe.db.set_value("Site", job.site, "status", "Broken")
			trigger_recovery_job(site_update.name)


def process_update_site_recover_job_update(job):
	updated_status = {
		"Pending": "Pending",
		"Running": "Running",
		"Success": "Recovered",
		"Failure": "Fatal",
	}[job.status]
	site_update = frappe.get_all(
		"Site Update",
		fields=["name", "status", "source_bench"],
		filters={"recover_job": job.name},
	)[0]
	if updated_status != site_update.status:
		site_bench = frappe.db.get_value("Site", job.site, "bench")
		move_site_step_status = frappe.db.get_value(
			"Agent Job Step", {"step_name": "Move Site", "agent_job": job.name}, "status"
		)
		if site_bench != site_update.source_bench and move_site_step_status == "Success":
			frappe.db.set_value("Site", job.site, "bench", site_update.source_bench)

		frappe.db.set_value("Site Update", site_update.name, "status", updated_status)
		if updated_status == "Recovered":
			frappe.get_doc("Site", job.site).reset_previous_status()
		elif updated_status == "Fatal":
			frappe.db.set_value("Site", job.site, "status", "Broken")
