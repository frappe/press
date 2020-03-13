# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe

import json
import requests
from frappe.utils.password import get_decrypted_password
from press.utils import log_error


class Agent:
	def __init__(self, server, server_type="Server"):
		self.server_type = server_type
		self.server = server
		self.port = 80

	def new_bench(self, bench, clone=None):
		data = {
			"config": json.loads(bench.config),
			"apps": [],
			"name": bench.name,
			"python": "python3",
			"clone": clone,
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

	def archive_site(self, site):
		password = get_decrypted_password("Server", site.server, "mariadb_root_password")
		data = {"mariadb_root_password": password}

		job = self.create_agent_job(
			"Archive Site",
			f"benches/{site.bench}/sites/{site.name}/archive",
			data,
			bench=site.bench,
			site=site.name,
		)
		job_id = self.post(f"benches/{site.bench}/sites/{site.name}/archive", data)["job"]
		job.job_id = job_id
		job.save()

	def backup_site(self, site):
		job = self.create_agent_job(
			"Backup Site",
			f"benches/{site.bench}/sites/{site.name}/backup",
			{},
			bench=site.bench,
			site=site.name,
		)
		job_id = self.post(f"benches/{site.bench}/sites/{site.name}/backup", {})["job"]
		job.job_id = job_id
		job.save()
		return job

	def fetch_monitor_data(self, bench):
		data = self.post(f"benches/{bench}/monitor", {})["data"]
		return data

	def fetch_site_status(self, site):
		data = self.get(f"benches/{site.bench}/sites/{site.name}/status")["data"]
		return data

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

	def remove_upstream_site(self, server, site):
		ip = frappe.db.get_value("Server", server, "ip")
		job = self.create_agent_job(
			"Remove Site from Upstream",
			f"proxy/upstreams/{ip}/sites/{site}",
			{},
			site=site,
			upstream=server,
		)
		job_id = self.delete(f"proxy/upstreams/{ip}/sites/{site}")["job"]
		job.job_id = job_id
		job.save()

	def ping(self):
		return self.get(f"ping")["message"]

	def get(self, path):
		return self.request("GET", path)

	def post(self, path, data):
		return self.request("POST", path, data)

	def delete(self, path):
		return self.request("DELETE", path)

	def request(self, method, path, data=None):
		try:
			url = f"http://{self.server}:{self.port}/agent/{path}"
			password = get_decrypted_password(self.server_type, self.server, "agent_password")
			headers = {"Authorization": f"bearer {password}"}
			result = requests.request(method, url, headers=headers, data=data)
			try:
				return result.json()
			except Exception:
				log_error(title="Agent Request Result Exception", method=method, url=url, data=data, headers=headers, result=result.text)
		except Exception:
			log_error(title="Agent Request Exception", method=method, url=url, data=data, headers=headers)

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
