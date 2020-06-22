# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
import json
from press.agent import Agent


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

		if not self.port_offset:
			benches = frappe.get_all(
				"Bench", fields=["port_offset"], filters={"server": self.server}
			)
			if benches:
				self.port_offset = max(map(lambda x: x.port_offset, benches)) + 1
			else:
				self.port_offset = 0

		config = frappe.db.get_single_value("Press Settings", "bench_configuration")
		config = json.loads(config)
		config.update(
			{
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
		unarchived_sites = frappe.db.exists("Site", {"bench": self.name, "status": ("!=", "Archived")})
		if unarchived_sites:
			frappe.throw("Cannot archive bench with active sites.")
		agent = Agent(self.server)
		agent.archive_bench(self)


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


def process_archive_bench_job_update(job):
	bench_status = frappe.get_value("Bench", job.bench, "status")

	updated_status = {"Pending": "Pending", "Success": "Archived", "Failure": "Broken"}[
		job.status
	]

	if updated_status != bench_status:
		frappe.db.set_value("Bench", job.bench, "status", updated_status)
