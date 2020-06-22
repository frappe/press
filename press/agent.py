# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe

import json
import requests
from frappe.utils.password import get_decrypted_password
from press.utils import log_error
from press.api.github import get_access_token


class Agent:
	def __init__(self, server, server_type="Server"):
		self.server_type = server_type
		self.server = server
		self.port = 443

	def new_bench(self, bench, clone=None):
		data = {
			"config": json.loads(bench.config),
			"apps": [],
			"name": bench.name,
			"python": "python3",
			"clone": clone,
		}
		for app in bench.apps:
			url, repo_owner, repo, branch, installation = frappe.db.get_value(
				"Frappe App", app.app, ["url", "repo_owner", "repo", "branch", "installation"]
			)
			if installation:
				token = get_access_token(installation)
				url = f"https://x-access-token:{token}@github.com/{repo_owner}/{repo}"
			data["apps"].append(
				{"name": app.scrubbed, "repo": repo, "url": url, "branch": branch, "hash": app.hash}
			)
		return self.create_agent_job("New Bench", "benches", data, bench=bench.name)

	def archive_bench(self, bench):
		return self.create_agent_job(
			"Archive Bench", f"benches/{bench.name}/archive", bench=bench.name
		)

	def update_bench_config(self, bench):
		data = {"config": json.loads(bench.config)}
		return self.create_agent_job(
			"Update Bench Configuration", f"benches/{bench.name}/config", data, bench=bench.name,
		)

	def new_site(self, site):
		apps = [frappe.db.get_value("Frappe App", app.app, "scrubbed") for app in site.apps]
		data = {
			"config": json.loads(site.config),
			"apps": apps,
			"name": site.name,
			"mariadb_root_password": get_decrypted_password(
				"Server", site.server, "mariadb_root_password"
			),
			"admin_password": get_decrypted_password("Site", site.name, "admin_password"),
		}

		return self.create_agent_job(
			"New Site", f"benches/{site.bench}/sites", data, bench=site.bench, site=site.name
		)

	def reinstall_site(self, site):
		data = {
			"mariadb_root_password": get_decrypted_password(
				"Server", site.server, "mariadb_root_password"
			),
			"admin_password": get_decrypted_password("Site", site.name, "admin_password"),
		}

		return self.create_agent_job(
			"Reinstall Site",
			f"benches/{site.bench}/sites/{site.name}/reinstall",
			data,
			bench=site.bench,
			site=site.name,
		)

	def restore_site(self, site):
		apps = [frappe.db.get_value("Frappe App", app.app, "scrubbed") for app in site.apps]
		data = {
			"apps": apps,
			"mariadb_root_password": get_decrypted_password(
				"Server", site.server, "mariadb_root_password"
			),
			"admin_password": get_decrypted_password("Site", site.name, "admin_password"),
		}
		files = {
			"database": site.database_file,
			"public": site.public_file,
			"private": site.private_file,
		}

		return self.create_agent_job(
			"Restore Site",
			f"benches/{site.bench}/sites/{site.name}/restore",
			data,
			files=files,
			bench=site.bench,
			site=site.name,
		)

	def new_site_from_backup(self, site):
		apps = [frappe.db.get_value("Frappe App", app.app, "scrubbed") for app in site.apps]
		data = {
			"config": json.loads(site.config),
			"apps": apps,
			"name": site.name,
			"mariadb_root_password": get_decrypted_password(
				"Server", site.server, "mariadb_root_password"
			),
			"admin_password": get_decrypted_password("Site", site.name, "admin_password"),
		}
		files = {
			"database": site.database_file,
			"public": site.public_file,
			"private": site.private_file,
		}

		return self.create_agent_job(
			"New Site from Backup",
			f"benches/{site.bench}/sites/restore",
			data,
			files=files,
			bench=site.bench,
			site=site.name,
		)

	def install_app_site(self, site, app):
		data = {"name": frappe.db.get_value("Frappe App", app, "scrubbed")}
		return self.create_agent_job(
			"Install App on Site",
			f"benches/{site.bench}/sites/{site.name}/apps",
			data,
			bench=site.bench,
			site=site.name,
		)

	def update_site(self, site, target, deploy_type):
		data = {"target": target}
		return self.create_agent_job(
			f"Update Site {deploy_type}",
			f"benches/{site.bench}/sites/{site.name}/update/{deploy_type.lower()}",
			data,
			bench=site.bench,
			site=site.name,
		)

	def update_site_recover(self, site, target):
		data = {"target": target}
		return self.create_agent_job(
			"Recover Failed Site Migration",
			f"benches/{site.bench}/sites/{site.name}/update/recover",
			data,
			bench=site.bench,
			site=site.name,
		)

	def update_site_config(self, site):
		data = {"config": json.loads(site.config)}
		return self.create_agent_job(
			"Update Site Configuration",
			f"benches/{site.bench}/sites/{site.name}/config",
			data,
			bench=site.bench,
			site=site.name,
		)

	def archive_site(self, site):
		password = get_decrypted_password("Server", site.server, "mariadb_root_password")
		data = {"mariadb_root_password": password}

		return self.create_agent_job(
			"Archive Site",
			f"benches/{site.bench}/sites/{site.name}/archive",
			data,
			bench=site.bench,
			site=site.name,
		)

	def backup_site(self, site, with_files=False):
		data = {"with_files": with_files}
		return self.create_agent_job(
			"Backup Site",
			f"benches/{site.bench}/sites/{site.name}/backup",
			data=data,
			bench=site.bench,
			site=site.name,
		)

	def new_host(self, domain):
		certificate = frappe.get_doc("TLS Certificate", domain.tls_certificate)
		data = {
			"name": domain.domain,
			"target": domain.site,
			"certificate": {
				"privkey.pem": certificate.privkey,
				"fullchain.pem": certificate.fullchain,
				"chain.pem": certificate.chain,
			},
		}
		return self.create_agent_job(
			"Add Host to Proxy", "proxy/hosts", data, host=domain.domain, site=domain.site
		)

	def new_server(self, server):
		ip = frappe.db.get_value("Server", server, "ip")
		data = {"name": ip}
		return self.create_agent_job(
			"Add Upstream to Proxy", "proxy/upstreams", data, upstream=server
		)

	def new_upstream_site(self, server, site):
		ip = frappe.db.get_value("Server", server, "ip")
		data = {"name": site}
		return self.create_agent_job(
			"Add Site to Upstream",
			f"proxy/upstreams/{ip}/sites",
			data,
			site=site,
			upstream=server,
		)

	def remove_upstream_site(self, server, site):
		ip = frappe.db.get_value("Server", server, "ip")
		return self.create_agent_job(
			"Remove Site from Upstream",
			f"proxy/upstreams/{ip}/sites/{site}",
			method="DELETE",
			site=site,
			upstream=server,
		)

	def update_site_status(self, server, site, status):
		data = {"status": status}
		ip = frappe.db.get_value("Server", server, "ip")
		return self.create_agent_job(
			"Update Site Status",
			f"proxy/upstreams/{ip}/sites/{site}/status",
			data=data,
			site=site,
			upstream=server,
		)

	def get(self, path):
		return self.request("GET", path)

	def post(self, path, data=None):
		return self.request("POST", path, data)

	def request(self, method, path, data=None, files=None):
		try:
			url = f"https://{self.server}:{self.port}/agent/{path}"
			password = get_decrypted_password(self.server_type, self.server, "agent_password")
			headers = {"Authorization": f"bearer {password}"}
			if files:
				file_objects = {
					key: frappe.get_doc("File", {"file_url": url}).get_content()
					for key, url in files.items()
				}
				file_objects["json"] = json.dumps(data).encode()
				result = requests.request(method, url, headers=headers, files=file_objects)
			else:
				result = requests.request(method, url, headers=headers, json=data)
			try:
				return result.json()
			except Exception:
				log_error(
					title="Agent Request Result Exception",
					method=method,
					url=url,
					data=data,
					files=files,
					headers=headers,
					result=result.text,
				)
		except Exception:
			log_error(
				title="Agent Request Exception",
				method=method,
				url=url,
				data=data,
				files=files,
				headers=headers,
			)

	def create_agent_job(
		self,
		job_type,
		path,
		data=None,
		files=None,
		method="POST",
		bench=None,
		site=None,
		upstream=None,
		host=None,
	):
		job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"server_type": self.server_type,
				"server": self.server,
				"bench": bench,
				"host": host,
				"site": site,
				"upstream": upstream,
				"status": "Pending",
				"request_method": method,
				"request_path": path,
				"request_data": json.dumps(data or {}, indent=4, sort_keys=True),
				"request_files": json.dumps(files or {}, indent=4, sort_keys=True),
				"job_type": job_type,
			}
		).insert()
		return job

	def get_job_status(self, id):
		status = self.get(f"jobs/{id}")
		return status

	def get_jobs_status(self, ids):
		status = self.get(f"jobs/{','.join(map(str, ids))}")
		if len(ids) == 1:
			return [status]
		return status

	def update(self):
		return self.post("update")

	def ping(self):
		return self.get("ping")["message"]

	def fetch_monitor_data(self, bench):
		data = self.post(f"benches/{bench}/monitor")["data"]
		return data

	def fetch_site_status(self, site):
		data = self.get(f"benches/{site.bench}/sites/{site.name}/status")["data"]
		return data

	def fetch_bench_status(self, bench):
		data = self.get(f"benches/{bench}/status")
		return data

	def fetch_server_status(self):
		data = {
			"mariadb_root_password": get_decrypted_password(
				"Server", self.server, "mariadb_root_password"
			)
		}
		data = self.post("server/status", data=data)
		return data
