# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
import json
import os
from datetime import date
from typing import TYPE_CHECKING, List

import _io
import frappe
import requests
from frappe.utils.password import get_decrypted_password
from press.utils import log_error, sanitize_config

if TYPE_CHECKING:
	from io import BufferedReader

	from press.press.doctype.app_patch.app_patch import AgentPatchConfig, AppPatch
	from press.press.doctype.site.site import Site


class Agent:
	if TYPE_CHECKING:
		from typing import Optional

		from requests import Response

		response: "Optional[Response]"

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

		if bench.mounts:
			data["mounts"] = [
				{
					"source": m.source,
					"destination": m.destination,
					"is_absolute_path": m.is_absolute_path,
				}
				for m in bench.mounts
			]

		return self.create_agent_job("New Bench", "benches", data, bench=bench.name)

	def archive_bench(self, bench):
		return self.create_agent_job(
			"Archive Bench", f"benches/{bench.name}/archive", bench=bench.name
		)

	def restart_nginx(self):
		return self.create_agent_job(
			"Reload NGINX",
			"server/reload",
		)

	def restart_bench(self, bench, web_only=False):
		return self.create_agent_job(
			"Bench Restart",
			f"benches/{bench.name}/restart",
			data={"web_only": web_only},
			bench=bench.name,
		)

	def rebuild_bench(self, bench):
		return self.create_agent_job(
			"Rebuild Bench Assets",
			f"benches/{bench.name}/rebuild",
			bench=bench.name,
		)

	def update_bench_config(self, bench):
		data = {
			"bench_config": json.loads(bench.bench_config),
			"common_site_config": json.loads(bench.config),
		}
		return self.create_agent_job(
			"Update Bench Configuration", f"benches/{bench.name}/config", data, bench=bench.name
		)

	def new_site(self, site):
		apps = [app.app for app in site.apps]
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"config": json.loads(site.config),
			"apps": apps,
			"name": site.name,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
			"admin_password": site.get_password("admin_password"),
		}

		return self.create_agent_job(
			"New Site", f"benches/{site.bench}/sites", data, bench=site.bench, site=site.name
		)

	def reinstall_site(self, site):
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
			"admin_password": site.get_password("admin_password"),
		}

		return self.create_agent_job(
			"Reinstall Site",
			f"benches/{site.bench}/sites/{site.name}/reinstall",
			data,
			bench=site.bench,
			site=site.name,
		)

	def restore_site(self, site: "Site", skip_failing_patches=False):
		site.check_enough_space_on_server()
		apps = [app.app for app in site.apps]
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		public_link, private_link = None, None
		if site.remote_public_file:
			public_link = frappe.get_doc("Remote File", site.remote_public_file).download_link
		if site.remote_private_file:
			private_link = frappe.get_doc("Remote File", site.remote_private_file).download_link
		data = {
			"apps": apps,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
			"admin_password": site.get_password("admin_password"),
			"database": frappe.get_doc("Remote File", site.remote_database_file).download_link,
			"public": public_link,
			"private": private_link,
			"skip_failing_patches": skip_failing_patches,
		}

		return self.create_agent_job(
			"Restore Site",
			f"benches/{site.bench}/sites/{site.name}/restore",
			data,
			bench=site.bench,
			site=site.name,
		)

	def rename_site(self, site, new_name: str, create_user: dict = None):
		data = {"new_name": new_name}
		if create_user:
			data["create_user"] = create_user
		return self.create_agent_job(
			"Rename Site",
			f"benches/{site.bench}/sites/{site.name}/rename",
			data,
			bench=site.bench,
			site=site.name,
		)

	def optimize_tables(self, site):
		return self.create_agent_job(
			"Optimize Tables",
			f"benches/{site.bench}/sites/{site.name}/optimize",
			bench=site.bench,
			site=site.name,
		)

	def rename_upstream_site(self, server: str, site, new_name: str, domains: List[str]):
		_server = frappe.get_doc("Server", server)
		ip = _server.ip if _server.is_self_hosted else _server.private_ip
		data = {"new_name": new_name, "domains": domains}
		return self.create_agent_job(
			"Rename Site on Upstream",
			f"proxy/upstreams/{ip}/sites/{site.name}/rename",
			data,
			site=site.name,
		)

	def new_site_from_backup(self, site: "Site", skip_failing_patches=False):
		site.check_enough_space_on_server()
		apps = [app.app for app in site.apps]

		def sanitized_site_config(site):
			sanitized_config = {}
			if site.remote_config_file:
				from press.press.doctype.site_activity.site_activity import log_site_activity

				site_config = frappe.get_doc("Remote File", site.remote_config_file)
				new_config = site_config.get_content()
				new_config["maintenance_mode"] = 0  # Don't allow deactivated sites to be created
				sanitized_config = sanitize_config(new_config)
				existing_config = json.loads(site.config)
				existing_config.update(sanitized_config)
				site._update_configuration(existing_config)
				log_site_activity(site.name, "Update Configuration")

			return json.dumps(sanitized_config)

		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		public_link, private_link = None, None

		if site.remote_public_file:
			public_link = frappe.get_doc("Remote File", site.remote_public_file).download_link
		if site.remote_private_file:
			private_link = frappe.get_doc("Remote File", site.remote_private_file).download_link

		data = {
			"config": json.loads(site.config),
			"apps": apps,
			"name": site.name,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
			"admin_password": site.get_password("admin_password"),
			"site_config": sanitized_site_config(site),
			"database": frappe.get_doc("Remote File", site.remote_database_file).download_link,
			"public": public_link,
			"private": private_link,
			"skip_failing_patches": skip_failing_patches,
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

	def setup_erpnext(self, site, user, config):
		data = {"user": user, "config": config}
		return self.create_agent_job(
			"Setup ERPNext",
			f"benches/{site.bench}/sites/{site.name}/erpnext",
			data,
			bench=site.bench,
			site=site.name,
		)

	def migrate_site(self, site, skip_failing_patches=False, activate=True):
		data = {"skip_failing_patches": skip_failing_patches, "activate": activate}
		return self.create_agent_job(
			"Migrate Site",
			f"benches/{site.bench}/sites/{site.name}/migrate",
			bench=site.bench,
			site=site.name,
			data=data,
		)

	def clear_site_cache(self, site):
		return self.create_agent_job(
			"Clear Cache",
			f"benches/{site.bench}/sites/{site.name}/cache",
			method="DELETE",
			bench=site.bench,
			site=site.name,
		)

	def update_site(
		self,
		site,
		target,
		deploy_type,
		skip_failing_patches=False,
		skip_backups=False,
		before_migrate_scripts=None,
		skip_search_index=True,
	):
		activate = site.status_before_update in ("Active", "Broken")
		data = {
			"target": target,
			"activate": activate,
			"skip_failing_patches": skip_failing_patches,
			"skip_backups": skip_backups,
			"before_migrate_scripts": before_migrate_scripts,
			"skip_search_index": skip_search_index,
		}
		return self.create_agent_job(
			f"Update Site {deploy_type}",
			f"benches/{site.bench}/sites/{site.name}/update/{deploy_type.lower()}",
			data,
			bench=site.bench,
			site=site.name,
		)

	def restore_site_tables(self, site):
		activate = site.status_before_update == "Active"
		data = {"activate": activate}
		return self.create_agent_job(
			"Restore Site Tables",
			f"benches/{site.bench}/sites/{site.name}/update/migrate/restore",
			data,
			bench=site.bench,
			site=site.name,
		)

	def update_site_recover_move(
		self, site, target, deploy_type, activate, rollback_scripts=None
	):
		data = {"target": target, "activate": activate, "rollback_scripts": rollback_scripts}
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

	def reset_site_usage(self, site):
		return self.create_agent_job(
			"Reset Site Usage",
			f"benches/{site.bench}/sites/{site.name}/usage",
			method="DELETE",
			bench=site.bench,
			site=site.name,
		)

	def archive_site(self, site, site_name=None, force=False):
		site_name = site_name or site.name
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
			"force": force,
		}

		return self.create_agent_job(
			"Archive Site",
			f"benches/{site.bench}/sites/{site_name}/archive",
			data,
			bench=site.bench,
			site=site.name,
		)

	def backup_site(self, site, with_files=False, offsite=False):
		from press.press.doctype.site_backup.site_backup import get_backup_bucket

		data = {"with_files": with_files}

		if offsite:
			settings = frappe.get_single("Press Settings")
			backups_path = os.path.join(site.name, str(date.today()))
			backup_bucket = get_backup_bucket(site.cluster, region=True)
			bucket_name = (
				backup_bucket.get("name") if isinstance(backup_bucket, dict) else backup_bucket
			)
			if settings.aws_s3_bucket or bucket_name:
				auth = {
					"ACCESS_KEY": settings.offsite_backups_access_key_id,
					"SECRET_KEY": settings.get_password("offsite_backups_secret_access_key"),
					"REGION": backup_bucket.get("region") if isinstance(backup_bucket, dict) else "",
				}
				data.update(
					{"offsite": {"bucket": bucket_name, "auth": auth, "path": backups_path}}
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
			"Add Host to Proxy", "proxy/hosts", data, host=domain.domain, site=domain.site
		)

	def setup_wildcard_hosts(self, wildcards):
		return self.create_agent_job(
			"Add Wildcard Hosts to Proxy", "proxy/wildcards", wildcards
		)

	def setup_redirects(self, site: str, domains: List[str], target: str):
		data = {"domains": domains, "target": target}
		return self.create_agent_job(
			"Setup Redirects on Hosts", "proxy/hosts/redirects", data, site=site
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
		_server = frappe.get_doc("Server", server)
		ip = _server.ip if _server.is_self_hosted else _server.private_ip
		data = {"name": ip}
		return self.create_agent_job(
			"Add Upstream to Proxy", "proxy/upstreams", data, upstream=server
		)

	def update_upstream_private_ip(self, server):
		ip, private_ip = frappe.db.get_value("Server", server, ["ip", "private_ip"])
		data = {"name": private_ip}
		return self.create_agent_job(
			"Rename Upstream", f"proxy/upstreams/{ip}/rename", data, upstream=server
		)

	def new_upstream_file(self, server, site=None, code_server=None):
		_server = frappe.get_doc("Server", server)
		ip = _server.ip if _server.is_self_hosted else _server.private_ip
		data = {"name": site if site else code_server}
		doctype = "Site" if site else "Code Server"
		return self.create_agent_job(
			f"Add {doctype} to Upstream",
			f"proxy/upstreams/{ip}/sites",
			data,
			site=site,
			code_server=code_server,
			upstream=server,
		)

	def remove_upstream_file(
		self, server, site=None, site_name=None, code_server=None, skip_reload=False
	):
		_server = frappe.get_doc("Server", server)
		ip = _server.ip if _server.is_self_hosted else _server.private_ip
		doctype = "Site" if site else "Code Server"
		file_name = site_name or site if (site or site_name) else code_server
		data = {"skip_reload": skip_reload}
		return self.create_agent_job(
			f"Remove {doctype} from Upstream",
			f"proxy/upstreams/{ip}/sites/{file_name}",
			method="DELETE",
			site=site,
			code_server=code_server,
			upstream=server,
			data=data,
		)

	def setup_code_server(self, bench, name, password):
		data = {"name": name, "password": password}
		return self.create_agent_job(
			"Setup Code Server", f"benches/{bench}/codeserver", data, code_server=name
		)

	def start_code_server(self, bench, name, password):
		data = {"password": password}
		return self.create_agent_job(
			"Start Code Server",
			f"benches/{bench}/codeserver/start",
			data,
			code_server=name,
		)

	def stop_code_server(self, bench, name):
		return self.create_agent_job(
			"Stop Code Server",
			f"benches/{bench}/codeserver/stop",
			code_server=name,
		)

	def archive_code_server(self, bench, name):
		return self.create_agent_job(
			"Archive Code Server",
			f"benches/{bench}/codeserver/archive",
			method="POST",
			code_server=name,
		)

	def add_ssh_user(self, bench):
		private_ip = frappe.db.get_value("Server", bench.server, "private_ip")
		candidate = frappe.get_doc("Deploy Candidate", bench.candidate)
		data = {
			"name": bench.name,
			"principal": bench.group,
			"ssh": {"ip": private_ip, "port": 22000 + bench.port_offset},
			"certificate": candidate.get_certificate(),
		}
		return self.create_agent_job(
			"Add User to Proxy", "ssh/users", data, bench=bench.name, upstream=bench.server
		)

	def remove_ssh_user(self, bench):
		return self.create_agent_job(
			"Remove User from Proxy",
			f"ssh/users/{bench.name}",
			method="DELETE",
			bench=bench.name,
			upstream=bench.server,
		)

	def add_proxysql_user(self, site, database, username, password, database_server):
		data = {
			"username": username,
			"password": password,
			"database": database,
			"backend": {"ip": database_server.private_ip, "id": database_server.server_id},
		}
		return self.create_agent_job(
			"Add User to ProxySQL", "proxysql/users", data, site=site.name
		)

	def add_proxysql_backend(self, database_server):
		data = {
			"backend": {"ip": database_server.private_ip, "id": database_server.server_id},
		}
		return self.create_agent_job("Add Backend to ProxySQL", "proxysql/backends", data)

	def remove_proxysql_user(self, site, username):
		return self.create_agent_job(
			"Remove User from ProxySQL",
			f"proxysql/users/{username}",
			method="DELETE",
			site=site.name,
		)

	def create_database_access_credentials(self, site, mode):
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"mode": mode,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
		}
		credentials = self.post(
			f"benches/{site.bench}/sites/{site.name}/credentials", data=data
		)
		return credentials

	def revoke_database_access_credentials(self, site):
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"user": site.database_access_user,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
		}
		return self.post(
			f"benches/{site.bench}/sites/{site.name}/credentials/revoke", data=data
		)

	def update_site_status(self, server, site, status, skip_reload=False):
		data = {"status": status, "skip_reload": skip_reload}
		_server = frappe.get_doc("Server", server)
		ip = _server.ip if _server.is_self_hosted else _server.private_ip
		return self.create_agent_job(
			"Update Site Status",
			f"proxy/upstreams/{ip}/sites/{site}/status",
			data=data,
			site=site,
			upstream=server,
		)

	def reload_nginx(self):
		return self.create_agent_job("Reload NGINX Job", "proxy/reload")

	def cleanup_unused_files(self):
		return self.create_agent_job("Cleanup Unused Files", "server/cleanup", {})

	def get(self, path, raises=True):
		return self.request("GET", path, raises=raises)

	def post(self, path, data=None, raises=True):
		return self.request("POST", path, data, raises=raises)

	def request(self, method, path, data=None, files=None, agent_job=None, raises=True):
		self.response = None
		agent_job_id = agent_job.name if agent_job else None
		headers = None
		url = None

		try:
			url = f"https://{self.server}:{self.port}/agent/{path}"
			password = get_decrypted_password(self.server_type, self.server, "agent_password")
			headers = {"Authorization": f"bearer {password}", "X-Agent-Job-Id": agent_job_id}
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
					key: value
					if isinstance(value, _io.BufferedReader)
					else frappe.get_doc("File", {"file_url": url}).get_content()
					for key, value in files.items()
				}
				file_objects["json"] = json.dumps(data).encode()
				self.response = requests.request(
					method, url, headers=headers, files=file_objects, verify=verify
				)
			else:
				self.response = requests.request(
					method, url, headers=headers, json=data, verify=verify, timeout=(10, 30)
				)
			json_response = None
			try:
				json_response = self.response.json()
				if raises:
					self.response.raise_for_status()
				return json_response
			except Exception:
				self.handle_request_failure(agent_job, self.response)
				log_error(
					title="Agent Request Result Exception",
					method=method,
					url=url,
					data=data,
					files=files,
					headers=headers,
					result=json_response or self.response.text,
					doc=agent_job,
				)
		except Exception as exc:
			self.handle_exception(agent_job, exc)
			log_error(
				title="Agent Request Exception",
				method=method,
				url=url,
				data=data,
				files=files,
				headers=headers,
				doc=agent_job,
			)

	def handle_request_failure(self, agent_job, result):
		if not agent_job:
			return

		message = f"""
			Status Code: {getattr(result, 'status_code', 'Unknown')} \n
			Response: {getattr(result, 'text', 'Unknown')}
		"""
		self.log_failure_reason(agent_job, message)
		agent_job.flags.status_code = result.status_code

	def handle_exception(self, agent_job, exception):
		self.log_failure_reason(agent_job, exception)

	def log_failure_reason(self, agent_job=None, message=None):
		if not agent_job:
			return

		agent_job.traceback = message
		agent_job.output = message

	def create_agent_job(
		self,
		job_type,
		path,
		data=None,
		files=None,
		method="POST",
		bench=None,
		site=None,
		code_server=None,
		upstream=None,
		host=None,
		reference_doctype=None,
		reference_name=None,
	):

		"""
		Check if job already exists in Undelivered, Pending, Running state
		don't add new job until its gets comleted
		"""

		disable_agent_job_deduplication = frappe.db.get_single_value(
			"Press Settings", "disable_agent_job_deduplication", cache=True
		)

		if not disable_agent_job_deduplication:
			job = self.get_similar_in_execution_job(
				job_type, path, bench, site, code_server, upstream, host, method
			)

			if job:
				return job

		job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"server_type": self.server_type,
				"server": self.server,
				"bench": bench,
				"host": host,
				"site": site,
				"code_server": code_server,
				"upstream": upstream,
				"status": "Undelivered",
				"request_method": method,
				"request_path": path,
				"request_data": json.dumps(data or {}, indent=4, sort_keys=True),
				"request_files": json.dumps(files or {}, indent=4, sort_keys=True),
				"job_type": job_type,
				"reference_doctype": reference_doctype,
				"reference_name": reference_name,
			}
		).insert()
		return job

	def get_similar_in_execution_job(
		self,
		job_type,
		path,
		bench=None,
		site=None,
		code_server=None,
		upstream=None,
		host=None,
		method="POST",
	):
		"""Deduplicate jobs in execution state"""

		filters = {
			"server_type": self.server_type,
			"server": self.server,
			"job_type": job_type,
			"status": ("not in", ("Success", "Failure", "Delivery Failure")),
			"request_method": method,
			"request_path": path,
		}

		if bench:
			filters["bench"] = bench

		if site:
			filters["site"] = site

		if code_server:
			filters["code_server"] = code_server

		if upstream:
			filters["upstream"] = upstream

		if host:
			filters["host"] = host

		job = frappe.db.get_value("Agent Job", filters, "name")

		return frappe.get_doc("Agent Job", job) if job else False

	def update_monitor_rules(self, rules, routes):
		data = {"rules": rules, "routes": routes}
		status = self.post("monitor/rules", data=data)
		return status

	def get_job_status(self, id):
		status = self.get(f"jobs/{id}")
		return status

	def get_site_sid(self, site, user=None):
		if user:
			data = {"user": user}
			result = self.post(f"benches/{site.bench}/sites/{site.name}/sid", data=data)
		else:
			result = self.get(f"benches/{site.bench}/sites/{site.name}/sid")
		return result and result.get("sid")

	def get_site_info(self, site):
		return self.get(f"benches/{site.bench}/sites/{site.name}/info")["data"]

	def get_sites_info(self, bench, since):
		return self.post(f"benches/{bench.name}/info", data={"since": since})

	def get_site_analytics(self, site):
		return self.get(f"benches/{site.bench}/sites/{site.name}/analytics")["data"]

	def get_sites_analytics(self, bench):
		return self.get(f"benches/{bench.name}/analytics")

	def describe_database_table(self, site, doctype, columns):
		data = {"doctype": doctype, "columns": list(columns)}
		return self.post(
			f"benches/{site.bench}/sites/{site.name}/describe-database-table",
			data=data,
		)["data"]

	def add_database_index(self, site, doctype, columns):
		data = {"doctype": doctype, "columns": list(columns)}
		return self.post(
			f"benches/{site.bench}/sites/{site.name}/add-database-index",
			data=data,
		)["data"]

	def get_jobs_status(self, ids):
		status = self.get(f"jobs/{','.join(map(str, ids))}")
		if len(ids) == 1:
			return [status]
		return status

	def get_jobs_id(self, agent_job_ids):
		return self.get(f"agent-jobs/{agent_job_ids}")

	def get_version(self):
		return self.get("version")

	def update(self):
		url = frappe.get_doc(self.server_type, self.server).get_agent_repository_url()
		return self.post("update", data={"url": url})

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

	def run_after_migrate_steps(self, site):
		data = {
			"admin_password": site.get_password("admin_password"),
		}
		return self.create_agent_job(
			"Run After Migrate Steps",
			f"benches/{site.bench}/sites/{site.name}/run_after_migrate_steps",
			bench=site.bench,
			site=site.name,
			data=data,
		)

	def move_site_to_bench(
		self,
		site,
		target,
		deactivate=True,
		skip_failing_patches=False,
	):
		"""
		Move site to bench without backup
		"""
		activate = site.status not in ("Inactive", "Suspended")
		data = {
			"target": target,
			"deactivate": deactivate,
			"activate": activate,
			"skip_failing_patches": skip_failing_patches,
		}
		return self.create_agent_job(
			"Move Site to Bench",
			f"benches/{site.bench}/sites/{site.name}/move_to_bench",
			data,
			bench=site.bench,
			site=site.name,
		)

	def force_update_bench_limits(self, bench: str, data: dict):
		return self.create_agent_job(
			"Force Update Bench Limits", f"benches/{bench}/limits", bench=bench, data=data
		)

	def patch_app(self, app_patch: "AppPatch", data: "AgentPatchConfig"):
		bench = app_patch.bench
		app = app_patch.app
		return self.create_agent_job(
			"Patch App",
			f"benches/{bench}/patch/{app}",
			bench=bench,
			data=data,
			reference_doctype="App Patch",
			reference_name=app_patch.name,
		)

	def upload_build_context_for_docker_build(
		self,
		file: "BufferedReader",
		dc_name: str,
	) -> str | None:
		if res := self.request(
			"POST", f"builder/upload/{dc_name}", files={"build_context_file": file}
		):
			return res.get("filename")

		return None

	def run_remote_builder(self, data: dict):
		reference_name = data.get("deploy_candidate")
		return self.create_agent_job(
			"Run Remote Builder",
			"builder/build",
			data=data,
			reference_doctype="Deploy Candidate",
			reference_name=reference_name,
		)

	def call_supervisorctl(self, bench: str, action: str, programs: list[str]):
		return self.create_agent_job(
			"Call Bench Supervisorctl",
			f"/benches/{bench}/supervisorctl",
			data={"command": action, "programs": programs},
		)

	def run_command_in_docker_cache(
		self,
		command: str = "ls -A",
		cache_target: str = "/home/frappe/.cache",
		remove_image: bool = True,
	):
		data = dict(
			command=command,
			cache_target=cache_target,
			remove_image=remove_image,
		)
		return self.request(
			"POST",
			"docker_cache_utils/run_command_in_docker_cache",
			data=data,
		)

	def get_cached_apps(self):
		return self.request(
			"POST",
			"docker_cache_utils/get_cached_apps",
			data={},
		)


class AgentCallbackException(Exception):
	pass
