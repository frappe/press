# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import os
from datetime import date
from typing import List

import frappe
import requests
from frappe.utils.password import get_decrypted_password
from press.utils import log_error, sanitize_config


class Agent:
	def __init__(self, server, server_type="Server"):
		self.server_type = server_type
		self.server = server
		self.port = 443

	def new_bench(self, bench):
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)
		data = {
			"name": bench.name,
			"bench_config": json.loads(bench.bench_config),
			"common_site_config": json.loads(bench.config),
			"registry": {
				"url": settings.docker_registry_url,
				"username": settings.docker_registry_username,
				"password": settings.docker_registry_password,
			},
		}
		return self.create_agent_job("New Bench", "benches", data, bench=bench.name)

	def archive_bench(self, bench):
		return self.create_agent_job(
			"Archive Bench", f"benches/{bench.name}/archive", bench=bench.name
		)

	def update_bench_config(self, bench):
		data = {
			"bench_config": json.loads(bench.bench_config),
			"common_site_config": json.loads(bench.config),
		}
		return self.create_agent_job(
			"Update Bench Configuration", f"benches/{bench.name}/config", data, bench=bench.name,
		)

	def new_site(self, site):
		apps = [app.app for app in site.apps]
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
			"New Site", f"benches/{site.bench}/sites", data, bench=site.bench, site=site.name,
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
		apps = [app.app for app in site.apps]
		data = {
			"apps": apps,
			"mariadb_root_password": get_decrypted_password(
				"Server", site.server, "mariadb_root_password"
			),
			"admin_password": get_decrypted_password("Site", site.name, "admin_password"),
			"database": frappe.get_doc("Remote File", site.remote_database_file).download_link,
			"public": frappe.get_doc("Remote File", site.remote_public_file).download_link,
			"private": frappe.get_doc("Remote File", site.remote_private_file).download_link,
		}

		return self.create_agent_job(
			"Restore Site",
			f"benches/{site.bench}/sites/{site.name}/restore",
			data,
			bench=site.bench,
			site=site.name,
		)

	def rename_site(self, site, new_name: str):
		data = {"new_name": new_name}
		return self.create_agent_job(
			"Rename Site",
			f"benches/{site.bench}/sites/{site.name}/rename",
			data,
			bench=site.bench,
			site=site.name,
		)

	def rename_upstream_site(self, server: str, site, new_name: str, domains: List[str]):
		ip = frappe.db.get_value("Server", server, "ip")
		data = {"new_name": new_name, "domains": domains}
		return self.create_agent_job(
			"Rename Site on Upstream",
			f"proxy/upstreams/{ip}/sites/{site.name}/rename",
			data,
			site=site.name,
		)

	def new_site_from_backup(self, site):
		apps = [app.app for app in site.apps]

		def sanitized_site_config(site):
			sanitized_config = {}
			if site.remote_config_file:
				from press.press.doctype.site_activity.site_activity import log_site_activity

				site_config = frappe.get_doc("Remote File", site.remote_config_file)
				new_config = site_config.get_content()
				sanitized_config = sanitize_config(new_config)
				existing_config = json.loads(site.config)
				existing_config.update(sanitized_config)
				site._update_configuration(existing_config)
				log_site_activity(site.name, "Update Configuration")

			return json.dumps(sanitized_config)

		data = {
			"config": json.loads(site.config),
			"apps": apps,
			"name": site.name,
			"mariadb_root_password": get_decrypted_password(
				"Server", site.server, "mariadb_root_password"
			),
			"admin_password": get_decrypted_password("Site", site.name, "admin_password"),
			"site_config": sanitized_site_config(site),
			"database": frappe.get_doc("Remote File", site.remote_database_file).download_link,
			"public": frappe.get_doc("Remote File", site.remote_public_file).download_link,
			"private": frappe.get_doc("Remote File", site.remote_private_file).download_link,
		}

		return self.create_agent_job(
			"New Site from Backup",
			f"benches/{site.bench}/sites/restore",
			data,
			bench=site.bench,
			site=site.name,
		)

	def install_app_site(self, site, app):
		data = {"name": app}
		return self.create_agent_job(
			"Install App on Site",
			f"benches/{site.bench}/sites/{site.name}/apps",
			data,
			bench=site.bench,
			site=site.name,
		)

	def uninstall_app_site(self, site, app):
		return self.create_agent_job(
			"Uninstall App from Site",
			f"benches/{site.bench}/sites/{site.name}/apps/{app}",
			method="DELETE",
			bench=site.bench,
			site=site.name,
		)

	def migrate_site(self, site):
		return self.create_agent_job(
			"Migrate Site",
			f"benches/{site.bench}/sites/{site.name}/migrate",
			bench=site.bench,
			site=site.name,
		)

	def update_site(self, site, target, deploy_type):
		activate = site.status_before_update == "Active"
		data = {"target": target, "activate": activate}
		return self.create_agent_job(
			f"Update Site {deploy_type}",
			f"benches/{site.bench}/sites/{site.name}/update/{deploy_type.lower()}",
			data,
			bench=site.bench,
			site=site.name,
		)

	def update_site_recover_move(self, site, target, deploy_type, activate):
		data = {"target": target, "activate": activate}
		return self.create_agent_job(
			f"Recover Failed Site {deploy_type}",
			f"benches/{site.bench}/sites/{site.name}/update/{deploy_type.lower()}/recover",
			data,
			bench=site.bench,
			site=site.name,
		)

	def update_site_recover(self, site):
		return self.create_agent_job(
			"Recover Failed Site Update",
			f"benches/{site.bench}/sites/{site.name}/update/recover",
			bench=site.bench,
			site=site.name,
		)

	def update_site_config(self, site):
		data = {
			"config": json.loads(site.config),
			"remove": json.loads(site._keys_removed_in_last_update),
		}
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

	def backup_site(self, site, with_files=False, offsite=False):
		data = {"with_files": with_files}

		if offsite:
			settings = frappe.get_single("Press Settings")
			backups_path = os.path.join(site.name, str(date.today()))

			if settings.aws_s3_bucket:
				auth = {
					"ACCESS_KEY": settings.offsite_backups_access_key_id,
					"SECRET_KEY": get_decrypted_password(
						"Press Settings", "Press Settings", "offsite_backups_secret_access_key"
					),
				}
				data.update(
					{"offsite": {"bucket": settings.aws_s3_bucket, "auth": auth, "path": backups_path}}
				)

			else:
				log_error("Offsite Backups aren't set yet")

		return self.create_agent_job(
			"Backup Site",
			f"benches/{site.bench}/sites/{site.name}/backup",
			data=data,
			bench=site.bench,
			site=site.name,
		)

	def add_domain(self, site, domain):
		data = {
			"domain": domain,
		}
		return self.create_agent_job(
			"Add Domain",
			f"benches/{site.bench}/sites/{site.name}/domains",
			data,
			bench=site.bench,
			site=site.name,
		)

	def remove_domain(self, site, domain):
		return self.create_agent_job(
			"Remove Domain",
			f"benches/{site.bench}/sites/{site.name}/domains/{domain}",
			method="DELETE",
			site=site.name,
			bench=site.bench,
		)

	def new_host(self, domain):
		certificate = frappe.get_doc("TLS Certificate", domain.tls_certificate)
		data = {
			"name": domain.domain,
			"target": domain.site,
			"certificate": {
				"privkey.pem": certificate.private_key,
				"fullchain.pem": certificate.full_chain,
				"chain.pem": certificate.intermediate_chain,
			},
		}
		return self.create_agent_job(
			"Add Host to Proxy", "proxy/hosts", data, host=domain.domain, site=domain.site,
		)

	def setup_redirects(self, site: str, domains: List[str], target: str):
		data = {"domains": domains, "target": target}
		return self.create_agent_job(
			"Setup Redirects on Hosts", "proxy/hosts/redirects", data, site=site,
		)

	def remove_redirects(self, site: str, domains: List[str]):
		data = {"domains": domains}
		return self.create_agent_job(
			"Remove Redirects on Hosts",
			"proxy/hosts/redirects",
			data,
			method="DELETE",
			site=site,
		)

	def remove_host(self, domain):
		return self.create_agent_job(
			"Remove Host from Proxy",
			f"proxy/hosts/{domain.domain}",
			method="DELETE",
			site=domain.site,
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

	def cleanup_unused_files(self):
		return self.create_agent_job("Cleanup Unused Files", "server/cleanup", {})

	def get(self, path):
		return self.request("GET", path)

	def post(self, path, data=None):
		return self.request("POST", path, data)

	def request(self, method, path, data=None, files=None):
		try:
			url = f"https://{self.server}:{self.port}/agent/{path}"
			password = get_decrypted_password(self.server_type, self.server, "agent_password")
			headers = {"Authorization": f"bearer {password}"}
			intermediate_ca = frappe.db.get_value(
				"Press Settings", "Press Settings", "backbone_intermediate_ca"
			)
			if frappe.conf.developer_mode and intermediate_ca:
				root_ca = frappe.db.get_value(
					"Certificate Authority", intermediate_ca, "parent_authority"
				)
				verify = frappe.get_doc("Certificate Authority", root_ca).certificate_file
			else:
				verify = True
			if files:
				file_objects = {
					key: frappe.get_doc("File", {"file_url": url}).get_content()
					for key, url in files.items()
				}
				file_objects["json"] = json.dumps(data).encode()
				result = requests.request(
					method, url, headers=headers, files=file_objects, verify=verify
				)
			else:
				result = requests.request(method, url, headers=headers, json=data, verify=verify)
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

	def get_site_sid(self, site):
		return self.get(f"benches/{site.bench}/sites/{site.name}/sid")["sid"]

	def get_site_info(self, site):
		return self.get(f"benches/{site.bench}/sites/{site.name}/info")["data"]

	def get_sites_info(self, bench, since):
		return self.post(f"benches/{bench.name}/info", data={"since": since})

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
