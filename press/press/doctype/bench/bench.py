# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
import json
import requests
from frappe.utils.password import get_decrypted_password


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

		config = json.loads(frappe.db.get_single_value("Press Settings", "bench_configuration"))
		config.update(
			{
				"background_workers": self.workers,
				"redis_cache": f"redis://localhost:{13000 + self.port_offset}",
				"redis_queue": f"redis://localhost:{11000 + self.port_offset}",
				"redis_socketio": f"redis://localhost:{12000 + self.port_offset}",
				"socketio_port": 9000 + self.port_offset,
				"webserver_port": 8000 + self.port_offset,
			}
		)
		self.config = json.dumps(config, indent=4)

	def after_insert(self):
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.server)
		agent.new_bench(self)


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


class Agent:
	def __init__(self, server, server_type="Server"):
		self.server_type = server_type
		self.server = server
		self.port = 80

	def new_bench(self, bench):
		data = {
			"config": json.loads(bench.config),
			"apps": [],
			"name": bench.name,
			"python": "python3",
		}
		for app in bench.apps:
			repo, branch = frappe.db.get_value("Frappe App", app.app, ["url", "branch"])
			data["apps"].append(
				{"name": app.scrubbed, "repo": repo, "branch": branch, "hash": app.hash}
			)

		job = self.create_agent_job("New Bench", "benches", data, bench=bench.name)
		job_id = self.post("benches", data)["job"]
		job.job_id = job_id
		job.save()

	def new_site(self, site):
		apps = [frappe.db.get_value("Frappe App", app.app, "scrubbed") for app in site.apps]
		data = {
			"config": {"monitor": True, "developer_mode": True},
			"apps": apps,
			"name": site.name,
			"mariadb_root_password": get_decrypted_password(
				"Server", site.server, "mariadb_root_password"
			),
			"admin_password": get_decrypted_password("Site", site.name, "admin_password"),
		}

		job = self.create_agent_job(
			"New Site", f"benches/{site.bench}/sites", data, bench=site.bench, site=site.name
		)
		job_id = self.post(f"benches/{site.bench}/sites", data)["job"]
		job.job_id = job_id
		job.save()

	def new_domain(self, domain):
		data = {"name": domain}
		job = self.create_agent_job("Add Host to Proxy", "proxy/hosts", data)
		job_id = self.post(f"proxy/hosts", data)["job"]
		job.job_id = job_id
		job.save()

	def new_server(self, server):
		ip = frappe.db.get_value("Server", server, "ip")
		data = {"name": ip}
		job = self.create_agent_job(
			"Add Upstream to Proxy", "proxy/upstreams", data, upstream=server
		)
		job_id = self.post(f"proxy/upstreams", data)["job"]
		job.job_id = job_id
		job.save()

	def new_upstream_site(self, server, site):
		ip = frappe.db.get_value("Server", server, "ip")
		data = {"name": site}
		job = self.create_agent_job(
			"Add Site to Upstream",
			f"proxy/upstreams/{ip}/sites",
			data,
			site=site,
			upstream=server,
		)
		job_id = self.post(f"proxy/upstreams/{ip}/sites", data)["job"]
		job.job_id = job_id
		job.save()

	def ping(self):
		return self.get(f"ping")["message"]

	def post(self, path, data):
		url = f"http://{self.server}:{self.port}/agent/{path}"
		password = get_decrypted_password(self.server_type, self.server, "agent_password")
		headers = {"Authorization": f"bearer {password}"}
		result = requests.post(url, headers=headers, json=data)
		try:
			return result.json()
		except Exception:
			frappe.log_error(result.text, title="Agent Request Exception")

	def get(self, path):
		url = f"http://{self.server}:{self.port}/agent/{path}"
		password = get_decrypted_password(self.server_type, self.server, "agent_password")
		headers = {"Authorization": f"bearer {password}"}
		result = requests.get(url, headers=headers)
		try:
			return result.json()
		except Exception:
			frappe.log_error(result.text, title="Agent Request Exception")

	def create_agent_job(self, job_type, path, data, bench=None, site=None, upstream=None):
		job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"server_type": self.server_type,
				"server": self.server,
				"bench": bench,
				"site": site,
				"upstream": upstream,
				"status": "Pending",
				"request_method": "POST",
				"request_path": path,
				"request_data": json.dumps(data, indent=4, sort_keys=True),
				"job_type": job_type,
			}
		).insert()
		return job

	def get_job_status(self, id):
		status = self.get(f"jobs/{id}")
		return status

	def update(self):
		return self.post("update", {})
