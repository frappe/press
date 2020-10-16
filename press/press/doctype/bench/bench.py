# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
import json
from press.agent import Agent
from press.utils import log_error


class Bench(Document):
	def validate(self):
		if not self.candidate:
			candidate = frappe.get_all("Deploy Candidate", filters={"group": self.group})[0]
			self.candidate = candidate.name
		candidate = frappe.get_doc("Deploy Candidate", self.candidate)
		if not self.apps:
			for release in candidate.apps:
				scrubbed = frappe.get_value("Frappe App", release.app, "scrubbed")
				self.append(
					"apps", {"app": release.app, "scrubbed": scrubbed, "hash": release.hash}
				)

		if self.is_new():
			self.port_offset = self.get_unused_port_offset()

		db_host = frappe.db.get_value("Database Server", self.database_server, "private_ip")
		config = frappe.db.get_single_value("Press Settings", "bench_configuration")
		config = json.loads(config)
		config.update(
			{
				"db_host": db_host or "localhost",
				"background_workers": self.workers,
				"gunicorn_workers": self.gunicorn_workers,
				"redis_cache": f"redis://localhost:{13000 + self.port_offset}",
				"redis_queue": f"redis://localhost:{11000 + self.port_offset}",
				"redis_socketio": f"redis://localhost:{12000 + self.port_offset}",
				"socketio_port": 9000 + self.port_offset,
				"webserver_port": 8000 + self.port_offset,
			}
		)
		self.config = json.dumps(config, indent=4)

	def get_unused_port_offset(self):
		benches = frappe.get_all(
			"Bench",
			fields=["port_offset"],
			filters={"server": self.server, "status": ("!=", "Archived")},
		)
		all_offsets = range(0, 100)
		used_offsets = map(lambda x: x.port_offset, benches)
		available_offsets = set(all_offsets) - set(used_offsets)
		return min(available_offsets)

	def on_update(self):
		self.update_bench_config()

	def update_bench_config(self):
		old = self.get_doc_before_save()
		if old and old.config != self.config:
			agent = Agent(self.server)
			agent.update_bench_config(self)

	def after_insert(self):
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.server)
		agent.new_bench(self)

	def archive(self):
		unarchived_sites = frappe.db.exists(
			"Site", {"bench": self.name, "status": ("!=", "Archived")}
		)
		if unarchived_sites:
			frappe.throw("Cannot archive bench with active sites.")
		agent = Agent(self.server)
		agent.archive_bench(self)

	def sync_info(self):
		"""Initiates a Job to update Site Usage, site.config.encryption_key and timezone details for all sites on Bench."""
		try:
			sites = frappe.get_all("Site", filters={"bench": self.name, "status": ("!=", "Archived")}, pluck="name")
			last_synced_time = round(
				frappe.get_all(
					"Site Usage", filters=[["site", "in", sites]], limit_page_length=1, order_by="creation desc", pluck="creation",
				)[0].timestamp()
			)
		except IndexError:
			last_synced_time = None

		agent = Agent(self.server)
		data = agent.get_sites_info(self, since=last_synced_time)
		for site, info in data.items():
			frappe.get_doc("Site", site).sync_info(info)


def process_new_bench_job_update(job):
	bench_status = frappe.get_value("Bench", job.bench, "status")

	updated_status = {
		"Pending": "Pending",
		"Running": "Installing",
		"Success": "Active",
		"Failure": "Broken",
	}[job.status]

	if updated_status != bench_status:
		frappe.db.set_value("Bench", job.bench, "status", updated_status)
		if updated_status == "Active":
			frappe.enqueue(
				"press.press.doctype.bench.bench.archive_obsolete_benches",
				enqueue_after_commit=True,
			)


def process_archive_bench_job_update(job):
	bench_status = frappe.get_value("Bench", job.bench, "status")

	updated_status = {
		"Pending": "Pending",
		"Running": "Pending",
		"Success": "Archived",
		"Failure": "Broken",
	}[job.status]

	if updated_status != bench_status:
		frappe.db.set_value("Bench", job.bench, "status", updated_status)


def archive_obsolete_benches():
	benches = frappe.get_all(
		"Bench", fields=["name", "candidate"], filters={"status": "Active"}
	)
	for bench in benches:
		# If this bench is already being archived then don't do anything.
		active_archival_jobs = frappe.db.exists(
			"Agent Job",
			{
				"job_type": "Archive Bench",
				"bench": bench.name,
				"status": ("in", ("Pending", "Running", "Success")),
			},
		)
		if active_archival_jobs:
			continue

		# Don't try archiving benches with sites
		if frappe.db.count("Site", {"bench": bench.name, "status": ("!=", "Archived")}):
			continue
		# If there isn't a Deploy Candidate Difference with this bench's candidate as source
		# That means this is the most recent bench and should be skipped.
		if not frappe.db.exists("Deploy Candidate Difference", {"source": bench.candidate}):
			continue

		# This bench isn't most recent.
		# But if none of the recent versions of this bench are yet active then this bench is still useful.

		# If any of the recent versions are active then, this bench can be safely archived.
		differences = frappe.get_all(
			"Deploy Candidate Difference",
			fields=["destination"],
			filters={"source": bench.candidate},
		)
		for difference in differences:
			if frappe.db.exists(
				"Bench", {"candidate": difference.destination, "status": "Active"}
			):
				try:
					frappe.get_doc("Bench", bench.name).archive()
					return
				except Exception:
					log_error("Bench Archival Error", bench=bench.name)


def scale_workers():
	# This method only operates on one bench at a time to avoid command collision
	# TODO: Fix this in agent. Lock commands that can't be run simultaneously
	benches = frappe.get_all(
		"Bench",
		fields=["name", "candidate", "workers", "gunicorn_workers"],
		filters={"status": "Active", "auto_scale_workers": True},
	)
	for bench in benches:
		site_count = frappe.db.count("Site", {"bench": bench.name, "status": "Active"})
		if site_count <= 25:
			workers, gunicorn_workers = 1, 2
		elif site_count <= 50:
			workers, gunicorn_workers = 2, 4
		elif site_count <= 75:
			workers, gunicorn_workers = 3, 6
		elif site_count <= 100:
			workers, gunicorn_workers = 4, 8
		elif site_count <= 150:
			workers, gunicorn_workers = 6, 8
		else:
			workers, gunicorn_workers = 8, 8

		if (bench.workers, bench.gunicorn_workers) != (workers, gunicorn_workers):
			bench = frappe.get_doc("Bench", bench.name)
			bench.workers, bench.gunicorn_workers = workers, gunicorn_workers
			bench.save()
			return


def sync_benches():
	benches = frappe.get_all("Bench", {"status": "Active"}, pluck="name")
	for bench in benches:
		frappe.enqueue(
			"press.press.doctype.bench.bench.sync_bench",
			queue="long",
			name=bench,
			enqueue_after_commit=True,
		)
	frappe.db.commit()


def sync_bench(name):
	bench = frappe.get_doc("Bench", name)
	try:
		bench.sync_info()
		frappe.db.commit()
	except Exception:
		log_error("Bench Sync Error", bench=bench.name)
