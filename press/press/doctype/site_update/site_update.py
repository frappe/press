# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import pytz
import random
import frappe

from press.agent import Agent
from datetime import datetime
from press.utils import log_error
from frappe.core.utils import find
from frappe.model.document import Document


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
				if difference_app and difference_app.deploy_type == "Migrate":
					self.deploy_type = "Migrate"

		except Exception:
			frappe.throw(
				f"Could not find Deploy Candidate Difference from {self.source_bench}"
				f" to {self.destination_bench}",
				frappe.ValidationError,
			)

		if self.has_pending_updates():
			frappe.throw(
				"An update is already pending for this site", frappe.ValidationError,
			)

		if not self.skipped_failing_patches and self.have_past_updates_failed():
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
		job = agent.update_site(
			site,
			self.destination_bench,
			self.deploy_type,
			skip_failing_patches=self.skipped_failing_patches,
		)
		frappe.db.set_value("Site Update", self.name, "update_job", job.name)

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
			{"site": self.site, "status": ("in", ("Pending", "Running", "Failure"))},
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
	source_benches_info = frappe.db.sql(
		"""
		SELECT sb.name AS source_bench, sb.candidate AS source_candidate, sb.server AS server, dcd.destination AS destination_candidate
		FROM `tabBench` sb, `tabDeploy Candidate Difference` dcd
		WHERE sb.status = 'Active' AND sb.candidate = dcd.source
		""",
		as_dict=True,
	)

	destination_candidates = list(
		set(d["destination_candidate"] for d in source_benches_info)
	)

	destination_benches_info = frappe.get_all(
		"Bench",
		filters={"status": "Active", "candidate": ("in", destination_candidates)},
		fields=["candidate AS destination_candidate", "name AS destination_bench", "server"],
	)

	updates_available_for_benches = []
	for bench in source_benches_info:
		destination_bench_exists = find(
			destination_benches_info,
			lambda x: (
				x["destination_candidate"] == bench.destination_candidate
				and x["server"] == bench.server
			),
		)

		if destination_bench_exists:
			updates_available_for_benches.append(bench)

	return list(set([bench.source_bench for bench in updates_available_for_benches]))


def sites_with_available_update():
	benches = benches_with_available_update()
	sites = frappe.get_all(
		"Site",
		filters={
			"status": ("in", ("Active", "Inactive", "Suspended")),
			"bench": ("in", benches),
		},
		fields=["name", "timezone", "bench", "status", "skip_auto_updates"],
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
	sites = list(filter(should_not_skip_auto_updates, sites))
	sites = list(filter(is_site_in_deploy_hours, sites))
	sites = list(filter(should_try_update, sites))

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
		try:
			site = frappe.get_doc("Site", site.name)
			site.schedule_update()
			update_triggered_count += 1
			frappe.db.commit()
			benches[site.bench] = True
		except Exception:
			log_error("Site Update Exception", site=site)
			frappe.db.rollback()


def should_not_skip_auto_updates(site):
	return not site.skip_auto_updates


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
	updated_status = job.status
	site_update = frappe.get_all(
		"Site Update",
		fields=["name", "status", "destination_bench"],
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
