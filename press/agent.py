# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import _io  # type: ignore
import json
import os
import re
from contextlib import suppress
from datetime import date
from typing import TYPE_CHECKING, Any, Literal

import frappe
import frappe.utils
import requests
from frappe.utils.password import get_decrypted_password
from requests.exceptions import HTTPError

from press.utils import (
	get_mariadb_root_password,
	log_error,
	sanitize_config,
	servers_using_alternative_port_for_communication,
)

if TYPE_CHECKING:
	from io import BufferedReader

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_patch.app_patch import AgentPatchConfig, AppPatch
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.physical_backup_restoration.physical_backup_restoration import (
		PhysicalBackupRestoration,
	)
	from press.press.doctype.site.site import Site
	from press.press.doctype.site_backup.site_backup import SiteBackup


APPS_LIST_REGEX = re.compile(r"\[.*\]")


class Agent:
	if TYPE_CHECKING:
		from typing import Optional

		from requests import Response

		response: Response | None

	def __init__(self, server, server_type="Server"):
		self.server_type = server_type
		self.server = server
		self.port = 443 if self.server not in servers_using_alternative_port_for_communication() else 8443

	def new_bench(self, bench: "Bench"):
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)
		cluster = frappe.db.get_value(self.server_type, self.server, "cluster")
		registry_url = frappe.db.get_value("Cluster", cluster, "repository") or settings.docker_registry_url

		data = {
			"name": bench.name,
			"bench_config": json.loads(bench.bench_config),
			"common_site_config": json.loads(bench.config),
			"registry": {
				"url": registry_url,
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
		return self.create_agent_job("Archive Bench", f"benches/{bench.name}/archive", bench=bench.name)

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

	def _get_managed_db_config(self, site):
		managed_database_service = frappe.get_cached_value("Bench", site.bench, "managed_database_service")

		if not managed_database_service:
			return {}

		return frappe.get_cached_value(
			"Managed Database Service",
			managed_database_service,
			["database_host", "database_root_user", "port"],
			as_dict=True,
		)

	def new_site(self, site, create_user: dict | None = None):
		apps = [app.app for app in site.apps]

		data = {
			"config": json.loads(site.config),
			"apps": apps,
			"name": site.name,
			"mariadb_root_password": get_mariadb_root_password(site),
			"admin_password": site.get_password("admin_password"),
			"managed_database_config": self._get_managed_db_config(site),
		}

		if create_user:
			data["create_user"] = create_user

		return self.create_agent_job(
			"New Site", f"benches/{site.bench}/sites", data, bench=site.bench, site=site.name
		)

	def reinstall_site(self, site):
		data = {
			"mariadb_root_password": get_mariadb_root_password(site),
			"admin_password": site.get_password("admin_password"),
			"managed_database_config": self._get_managed_db_config(site),
		}

		return self.create_agent_job(
			"Reinstall Site",
			f"benches/{site.bench}/sites/{site.name}/reinstall",
			data,
			bench=site.bench,
			site=site.name,
		)

	def restore_site(self, site: "Site", skip_failing_patches=False):
		site.check_space_on_server_for_restore()
		apps = [app.app for app in site.apps]
		public_link, private_link, database_link = None, None, None
		if site.remote_database_file:
			database_link = frappe.get_doc("Remote File", site.remote_database_file).download_link
		if site.remote_public_file:
			public_link = frappe.get_doc("Remote File", site.remote_public_file).download_link
		if site.remote_private_file:
			private_link = frappe.get_doc("Remote File", site.remote_private_file).download_link

		data = {
			"apps": apps,
			"mariadb_root_password": get_mariadb_root_password(site),
			"admin_password": site.get_password("admin_password"),
			"database": database_link,
			"public": public_link,
			"private": private_link,
			"skip_failing_patches": skip_failing_patches,
			"managed_database_config": self._get_managed_db_config(site),
		}

		return self.create_agent_job(
			"Restore Site",
			f"benches/{site.bench}/sites/{site.name}/restore",
			data,
			bench=site.bench,
			site=site.name,
		)

	def rename_site(self, site, new_name: str, create_user: dict | None = None, config: dict | None = None):
		data: dict[str, Any] = {"new_name": new_name}
		if create_user:
			data["create_user"] = create_user
		if config:
			data["config"] = config
		return self.create_agent_job(
			"Rename Site",
			f"benches/{site.bench}/sites/{site.name}/rename",
			data,
			bench=site.bench,
			site=site.name,
		)

	def create_user(self, site, email, first_name, last_name, password=None):
		data = {
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"password": password,
		}
		return self.create_agent_job(
			"Create User",
			f"benches/{site.bench}/sites/{site.name}/create-user",
			data,
			bench=site.bench,
			site=site.name,
		)

	def complete_setup_wizard(self, site, data):
		return self.create_agent_job(
			"Complete Setup Wizard",
			f"benches/{site.bench}/sites/{site.name}/complete-setup-wizard",
			data,
			bench=site.bench,
			site=site.name,
		)

	def optimize_tables(self, site, tables):
		return self.create_agent_job(
			"Optimize Tables",
			f"benches/{site.bench}/sites/{site.name}/optimize",
			data={"tables": tables},
			bench=site.bench,
			site=site.name,
		)

	def rename_upstream_site(self, server: str, site, new_name: str, domains: list[str]):
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
		site.check_space_on_server_for_restore()
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

		public_link, private_link = None, None

		if site.remote_public_file:
			public_link = frappe.get_doc("Remote File", site.remote_public_file).download_link
		if site.remote_private_file:
			private_link = frappe.get_doc("Remote File", site.remote_private_file).download_link

		assert site.config is not None, "Site config is required to restore site from backup"

		data = {
			"config": json.loads(site.config) if site.config else {},
			"apps": apps,
			"name": site.name,
			"mariadb_root_password": get_mariadb_root_password(site),
			"admin_password": site.get_password("admin_password"),
			"site_config": sanitized_site_config(site),
			"database": frappe.get_doc("Remote File", site.remote_database_file).download_link,
			"public": public_link,
			"private": private_link,
			"skip_failing_patches": skip_failing_patches,
			"managed_database_config": self._get_managed_db_config(site),
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

	def activate_site(self, site, reference_doctype=None, reference_name=None):
		return self.create_agent_job(
			"Activate Site",
			f"benches/{site.bench}/sites/{site.name}/activate",
			bench=site.bench,
			site=site.name,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def deactivate_site(self, site, reference_doctype=None, reference_name=None):
		return self.create_agent_job(
			"Deactivate Site",
			f"benches/{site.bench}/sites/{site.name}/deactivate",
			bench=site.bench,
			site=site.name,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
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
		self,
		site,
		target,
		deploy_type,
		activate,
		rollback_scripts=None,
		restore_touched_tables=True,
	):
		data = {
			"target": target,
			"activate": activate,
			"rollback_scripts": rollback_scripts,
			"restore_touched_tables": restore_touched_tables,
		}
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

	def physical_backup_database(self, site: Site, site_backup: SiteBackup):
		"""
		For physical database backup, the flow :
		- Create the agent job
		- Agent job will lock the specific database + flush the changes to disk
		- Take a database dump
		- Use `fsync` to ensure the changes are written to disk
		- Agent will send back a request to FC for taking the snapshot
			- By calling `snapshot_create_callback` url
		- Then, unlock the database
		"""
		press_public_base_url = frappe.utils.get_url()
		data = {
			"databases": [site_backup.database_name],
			"mariadb_root_password": get_mariadb_root_password(site),
			"private_ip": frappe.get_value(
				"Database Server", frappe.db.get_value("Server", site.server, "database_server"), "private_ip"
			),
			"site_backup": {
				"name": site_backup.name,
				"snapshot_request_key": site_backup.snapshot_request_key,
				"snapshot_trigger_url": f"{press_public_base_url}/api/method/press.api.site_backup.create_snapshot",
			},
		}
		return self.create_agent_job(
			"Physical Backup Database",
			"/database/physical-backup",
			data=data,
			bench=site.bench,
			site=site.name,
		)

	def physical_restore_database(self, site, backup_restoration: PhysicalBackupRestoration):
		data = {
			"backup_db": backup_restoration.source_database,
			"target_db": backup_restoration.destination_database,
			"target_db_root_password": get_mariadb_root_password(site),
			"private_ip": frappe.get_value(
				"Database Server", frappe.db.get_value("Server", site.server, "database_server"), "private_ip"
			),
			"backup_db_base_directory": os.path.join(backup_restoration.mount_point, "var/lib/mysql"),
			"restore_specific_tables": backup_restoration.restore_specific_tables,
			"tables_to_restore": json.loads(backup_restoration.tables_to_restore),
		}
		return self.create_agent_job(
			"Physical Restore Database",
			"/database/physical-restore",
			data=data,
			bench=site.bench,
			site=site.name,
			reference_name=backup_restoration.name,
			reference_doctype=backup_restoration.doctype,
		)

	def backup_site(self, site, site_backup: SiteBackup):
		from press.press.doctype.site_backup.site_backup import get_backup_bucket

		data = {
			"with_files": site_backup.with_files,
			"agent_job_timeout": site.backup_timeout,
		}
		if site_backup.offsite:
			settings = frappe.get_single("Press Settings")
			backups_path = os.path.join(site.name, str(date.today()))
			backup_bucket = get_backup_bucket(site.cluster, region=True)
			bucket_name = backup_bucket.get("name") if isinstance(backup_bucket, dict) else backup_bucket
			if settings.aws_s3_bucket or bucket_name:
				auth = {
					"ACCESS_KEY": settings.offsite_backups_access_key_id,
					"SECRET_KEY": settings.get_password("offsite_backups_secret_access_key"),
					"REGION": backup_bucket.get("region") if isinstance(backup_bucket, dict) else "",
				}
				data.update({"offsite": {"bucket": bucket_name, "auth": auth, "path": backups_path}})
			else:
				log_error("Offsite Backups aren't set yet")

			data.update(
				{
					"keep_files_locally_after_offsite_backup": bool(
						frappe.get_value("Server", site.server, "keep_files_on_server_in_offsite_backup")
					)
				}
			)

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
		return self.create_agent_job("Add Wildcard Hosts to Proxy", "proxy/wildcards", wildcards)

	def setup_redirects(self, site: str, domains: list[str], target: str):
		data = {"domains": domains, "target": target}
		return self.create_agent_job("Setup Redirects on Hosts", "proxy/hosts/redirects", data, site=site)

	def remove_redirects(self, site: str, domains: list[str]):
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
			{},
			method="DELETE",
			site=domain.site,
		)

	def new_server(self, server):
		_server = frappe.get_doc("Server", server)
		ip = _server.ip if _server.is_self_hosted else _server.private_ip
		data = {"name": ip}
		return self.create_agent_job("Add Upstream to Proxy", "proxy/upstreams", data, upstream=server)

	def update_upstream_private_ip(self, server):
		ip, private_ip = frappe.db.get_value("Server", server, ["ip", "private_ip"])
		data = {"name": private_ip}
		return self.create_agent_job("Rename Upstream", f"proxy/upstreams/{ip}/rename", data, upstream=server)

	def proxy_add_auto_scale_site_to_upstream(
		self, primary_upstream: str, secondary_upstreams: list[dict[str, int]]
	) -> "AgentJob":
		return self.create_agent_job(
			"Add Auto Scale Site to Upstream",
			f"proxy/upstreams/{primary_upstream}/auto-scale-site",
			data={"secondary_upstreams": secondary_upstreams},
		)

	def proxy_remove_auto_scale_site_to_upstream(self, primary_upstream: str) -> "AgentJob":
		return self.create_agent_job(
			"Remove Auto Scale Site from Upstream",
			f"proxy/upstreams/{primary_upstream}/remove-auto-scale-site",
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

	def add_domain_to_upstream(self, server, site=None, domain=None):
		_server = frappe.get_doc("Server", server)
		ip = _server.ip if _server.is_self_hosted else _server.private_ip
		data = {"domain": domain}
		return self.create_agent_job(
			"Add Domain to Upstream",
			f"proxy/upstreams/{ip}/domains",
			data,
			site=site,
			upstream=server,
		)

	def remove_upstream_file(self, server, site=None, site_name=None, code_server=None):
		_server = frappe.get_doc("Server", server)
		ip = _server.ip if _server.is_self_hosted else _server.private_ip
		doctype = "Site" if site else "Code Server"
		file_name = site_name or site if (site or site_name) else code_server
		extra_domains = frappe.get_all(
			"Site Domain",
			{"site": site, "tls_certificate": ("is", "not set"), "status": "Active", "domain": ("!=", site)},
			pluck="domain",
		)
		data = {"extra_domains": extra_domains}
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

	def add_proxysql_user(
		self,
		site,
		database: str,
		username: str,
		password: str,
		max_connections: int,
		database_server,
		reference_doctype=None,
		reference_name=None,
	):
		data = {
			"username": username,
			"password": password,
			"database": database,
			"max_connections": max_connections,
			"backend": {"ip": database_server.private_ip, "id": database_server.server_id},
		}
		return self.create_agent_job(
			"Add User to ProxySQL",
			"proxysql/users",
			data,
			site=site.name,
			reference_name=reference_name,
			reference_doctype=reference_doctype,
		)

	def add_proxysql_backend(self, database_server):
		data = {
			"backend": {"ip": database_server.private_ip, "id": database_server.server_id},
		}
		return self.create_agent_job("Add Backend to ProxySQL", "proxysql/backends", data)

	def remove_proxysql_user(self, site, username, reference_doctype=None, reference_name=None):
		return self.create_agent_job(
			"Remove User from ProxySQL",
			f"proxysql/users/{username}",
			method="DELETE",
			site=site.name,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def create_database_access_credentials(self, site, mode):
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"mode": mode,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
		}
		return self.post(f"benches/{site.bench}/sites/{site.name}/credentials", data=data)

	def revoke_database_access_credentials(self, site):
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"user": site.database_access_user,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
		}
		return self.post(f"benches/{site.bench}/sites/{site.name}/credentials/revoke", data=data)

	def create_database_user(self, site, username, password, reference_name):
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"username": username,
			"password": password,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
		}
		return self.create_agent_job(
			"Create Database User",
			f"benches/{site.bench}/sites/{site.name}/database/users",
			data,
			site=site.name,
			reference_doctype="Site Database User",
			reference_name=reference_name,
		)

	def remove_database_user(self, site, username, reference_name):
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			)
		}
		return self.create_agent_job(
			"Remove Database User",
			f"benches/{site.bench}/sites/{site.name}/database/users/{username}",
			method="DELETE",
			data=data,
			site=site.name,
			reference_doctype="Site Database User",
			reference_name=reference_name,
		)

	def modify_database_user_permissions(self, site, username, mode, permissions: dict, reference_name):
		database_server = frappe.db.get_value("Bench", site.bench, "database_server")
		data = {
			"mode": mode,
			"permissions": permissions,
			"mariadb_root_password": get_decrypted_password(
				"Database Server", database_server, "mariadb_root_password"
			),
		}
		return self.create_agent_job(
			"Modify Database User Permissions",
			f"benches/{site.bench}/sites/{site.name}/database/users/{username}/permissions",
			method="POST",
			data=data,
			site=site.name,
			reference_doctype="Site Database User",
			reference_name=reference_name,
		)

	def update_site_status(self, server: str, site: str, status, skip_reload=False):
		extra_domains = frappe.get_all(
			"Site Domain",
			{"site": site, "tls_certificate": ("is", "not set"), "status": "Active", "domain": ("!=", site)},
			pluck="domain",
		)
		data = {"status": status, "extra_domains": extra_domains, "skip_reload": skip_reload}
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

	def cleanup_unused_files(self, force: bool = False):
		return self.create_agent_job("Cleanup Unused Files", "server/cleanup", {"force": force})

	def get(self, path, raises=True):
		return self.request("GET", path, raises=raises)

	def post(self, path, data=None, raises=True):
		return self.request("POST", path, data, raises=raises)

	def delete(self, path, data=None, raises=True):
		return self.request("DELETE", path, data, raises=raises)

	def _make_req(self, method, path, data, files, agent_job_id):
		password = get_decrypted_password(self.server_type, self.server, "agent_password")
		headers = {"Authorization": f"bearer {password}", "X-Agent-Job-Id": agent_job_id}
		url = f"https://{self.server}:{self.port}/agent/{path}"
		intermediate_ca = frappe.db.get_value("Press Settings", "Press Settings", "backbone_intermediate_ca")
		if frappe.conf.developer_mode and intermediate_ca:
			root_ca = frappe.db.get_value("Certificate Authority", intermediate_ca, "parent_authority")
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
			return requests.request(method, url, headers=headers, files=file_objects, verify=verify)
		return requests.request(method, url, headers=headers, json=data, verify=verify, timeout=(10, 30))

	def request(self, method, path, data=None, files=None, agent_job=None, raises=True):
		self.raise_if_past_requests_have_failed()
		response = json_response = None
		try:
			agent_job_id = agent_job.name if agent_job else None
			response = self._make_req(method, path, data, files, agent_job_id)
			json_response = response.json()
			if raises and response.status_code >= 400:
				output = "\n\n".join([json_response.get("output", ""), json_response.get("traceback", "")])
				if output == "\n\n":
					output = json.dumps(json_response, indent=2, sort_keys=True)
				raise HTTPError(
					f"{response.status_code} {response.reason}\n\n{output}",
					response=response,
				)
			return json_response
		except (HTTPError, TypeError, ValueError):
			self.handle_request_failure(agent_job, response)
			log_error(
				title="Agent Request Result Exception",
				result=json_response or getattr(response, "text", None),
			)
		except requests.JSONDecodeError as exc:
			if response and response.status_code >= 500:
				self.log_request_failure(exc)
				self.handle_exception(agent_job, exc)
				log_error(
					title="Agent Request Exception",
				)
		except Exception as exc:
			self.log_request_failure(exc)
			self.handle_exception(agent_job, exc)
			log_error(
				title="Agent Request Exception",
			)

	def raise_if_past_requests_have_failed(self):
		failures = frappe.db.get_value("Agent Request Failure", {"server": self.server}, "failure_count")
		if failures:
			raise AgentRequestSkippedException(f"Previous {failures} requests have failed. Try again later.")

	def log_request_failure(self, exc):
		filters = {
			"server": self.server,
		}
		failure = frappe.db.get_value(
			"Agent Request Failure", filters, ["name", "failure_count"], as_dict=True
		)
		if failure:
			frappe.db.set_value(
				"Agent Request Failure", failure.name, "failure_count", failure.failure_count + 1
			)
		else:
			fields = filters
			fields.update(
				{
					"server_type": self.server_type,
					"traceback": frappe.get_traceback(with_context=True),
					"error": repr(exc),
					"failure_count": 1,
				}
			)
			is_primary = frappe.db.get_value(self.server_type, self.server, "is_primary")
			if self.server_type == "Server" and not is_primary:
				# Don't create agent request failures for secondary servers
				# Since we try to connect to them frequently after IP changes
				return

			frappe.new_doc("Agent Request Failure", **fields).insert(ignore_permissions=True)

	def raw_request(self, method, path, data=None, raises=True, timeout=None):
		url = f"https://{self.server}:{self.port}/agent/{path}"
		password = get_decrypted_password(self.server_type, self.server, "agent_password")
		headers = {"Authorization": f"bearer {password}"}
		timeout = timeout or (10, 30)
		response = requests.request(method, url, headers=headers, json=data, timeout=timeout)
		json_response = response.json()
		if raises:
			response.raise_for_status()
		return json_response

	def should_skip_requests(self):
		if self.server_type in ("Server", "Database Server", "Proxy Server") and frappe.db.get_value(
			self.server_type, self.server, "halt_agent_jobs"
		):
			return True

		return bool(frappe.db.count("Agent Request Failure", {"server": self.server}))

	def handle_request_failure(self, agent_job, result: Response | None):
		if not agent_job:
			raise

		status_code = getattr(result, "status_code", "Unknown")
		with suppress(TypeError, ValueError):
			reason = json.dumps(result.json(), indent=4, sort_keys=True) if result else None

		message = f"""
Status Code: {status_code}\n
Response: {reason or getattr(result, "text", "Unknown")}
"""
		self.log_failure_reason(agent_job, message)
		agent_job.flags.status_code = status_code

	def handle_exception(self, agent_job, exception):
		self.log_failure_reason(agent_job, exception)

	def log_failure_reason(self, agent_job=None, message=None):
		if not agent_job:
			raise

		agent_job.traceback = message
		agent_job.output = message

	def create_agent_job(
		self,
		job_type,
		path,
		data: dict | None = None,
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
		don't add new job until its gets completed
		"""

		disable_agent_job_deduplication = frappe.db.get_single_value(
			"Press Settings", "disable_agent_job_deduplication", cache=True
		)

		if not disable_agent_job_deduplication:
			existing_job = self.get_similar_in_execution_job(
				job_type, path, bench, site, code_server, upstream, host, method
			)

			if existing_job:
				return existing_job

		job: "AgentJob" = frappe.get_doc(
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
			filters["site"] = site if not isinstance(site, list) else ("IN", site)

		if code_server:
			filters["code_server"] = code_server

		if upstream:
			filters["upstream"] = upstream

		if host:
			filters["host"] = host

		job = frappe.db.get_value("Agent Job", filters, "name", debug=1)

		return frappe.get_doc("Agent Job", job) if job else False

	def update_monitor_rules(self, rules, routes):
		data = {"rules": rules, "routes": routes}
		return self.post("monitor/rules", data=data)

	def get_job_status(self, id):
		return self.get(f"jobs/{id}")

	def cancel_job(self, id):
		return self.post(f"jobs/{id}/cancel")

	def get_site_sid(self, site, user=None):
		if user:
			data = {"user": user}
			result = self.post(f"benches/{site.bench}/sites/{site.name}/sid", data=data)
		else:
			result = self.get(f"benches/{site.bench}/sites/{site.name}/sid")
		return result and result.get("sid")

	def get_site_info(self, site):
		result = self.get(f"benches/{site.bench}/sites/{site.name}/info")
		if result:
			return result["data"]
		return None

	def get_sites_info(self, bench, since):
		return self.post(f"benches/{bench.name}/info", data={"since": since})

	def get_site_analytics(self, site):
		result = self.get(f"benches/{site.bench}/sites/{site.name}/analytics")
		if result:
			return result["data"]
		return None

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
		return self.create_agent_job(
			"Add Database Index",
			f"benches/{site.bench}/sites/{site.name}/add-database-index",
			data,
			site=site.name,
		)

	def get_jobs_status(self, ids):
		status = self.get(f"jobs/{','.join(map(str, ids))}")
		if len(ids) == 1:
			return [status]
		return status

	def get_jobs_id(self, agent_job_ids):
		return self.get(f"agent-jobs/{agent_job_ids}")

	def get_version(self):
		return self.raw_request("GET", "version", raises=True, timeout=(2, 10))

	def update(self):
		url = frappe.get_doc(self.server_type, self.server).get_agent_repository_url()
		branch = frappe.get_doc(self.server_type, self.server).get_agent_repository_branch()
		return self.post("update", data={"url": url, "branch": branch})

	def ping(self):
		return self.raw_request("GET", "ping", raises=True, timeout=(2, 5))["message"]

	def fetch_monitor_data(self, bench):
		return self.post(f"benches/{bench}/monitor")["data"]

	def fetch_site_status(self, site):
		return self.get(f"benches/{site.bench}/sites/{site.name}/status")["data"]

	def fetch_bench_status(self, bench):
		return self.get(f"benches/{bench}/status")

	def get_snapshot(self, bench: str):
		return self.get(f"process-snapshot/{bench}")

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
		if res := self.request("POST", f"builder/upload/{dc_name}", files={"build_context_file": file}):
			return res.get("filename")

		return None

	def run_build(self, data: dict):
		reference_name = data.get("deploy_candidate_build")
		return self.create_agent_job(
			"Run Remote Builder",
			"builder/build",
			data=data,
			reference_doctype="Deploy Candidate Build",
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

	def get_site_apps(self, site):
		raw_apps_list = self.get(
			f"benches/{site.bench}/sites/{site.name}/apps",
		)

		try:
			raw_apps = raw_apps_list["data"]
			apps = APPS_LIST_REGEX.findall(raw_apps)[0]
			apps: list[str] = json.loads(apps)
		except (json.JSONDecodeError, IndexError):
			apps: list[str] = [line.split()[0] for line in raw_apps_list["data"].splitlines() if line]

		return apps

	def fetch_database_table_schema(
		self, site, include_table_size: bool = False, include_index_info: bool = False
	):
		return self.create_agent_job(
			"Fetch Database Table Schema",
			f"benches/{site.bench}/sites/{site.name}/database/schema",
			bench=site.bench,
			site=site.name,
			data={
				"include_table_size": include_table_size,
				"include_index_info": include_index_info,
			},
			reference_doctype="Site",
			reference_name=site.name,
		)

	def run_sql_query_in_database(self, site, query, commit):
		return self.post(
			f"benches/{site.bench}/sites/{site.name}/database/query/execute",
			data={"query": query, "commit": commit, "as_dict": False},
		)

	def get_summarized_performance_report_of_database(self, site):
		return self.post(
			f"benches/{site.bench}/sites/{site.name}/database/performance-report",
			data={"mariadb_root_password": get_mariadb_root_password(site)},
		)

	def analyze_slow_queries(self, site, normalized_queries: list[dict]):
		"""
		normalized_queries format:
		[
			{
				"example": "",
				"normalized" : "",
			}
		]
		"""
		return self.create_agent_job(
			"Analyze Slow Queries",
			f"benches/{site.bench}/sites/{site.name}/database/analyze-slow-queries",
			data={
				"queries": normalized_queries,
				"mariadb_root_password": get_mariadb_root_password(site),
			},
			site=site.name,
		)

	def fetch_database_processes(self, site):
		return self.post(
			f"benches/{site.bench}/sites/{site.name}/database/processes",
			data={
				"mariadb_root_password": get_mariadb_root_password(site),
			},
		)

	def kill_database_process(self, site, id):
		return self.post(
			f"benches/{site.bench}/sites/{site.name}/database/kill-process/{id}",
			data={
				"mariadb_root_password": get_mariadb_root_password(site),
			},
		)

	def update_database_schema_sizes(self):
		if self.server_type != "Database Server":
			return NotImplementedError("This method is only supported for Database Server")

		return self.create_agent_job(
			"Update Database Schema Sizes",
			"database/update-schema-sizes",
			data={
				"private_ip": frappe.get_value("Database Server", self.server, "private_ip"),
				"mariadb_root_password": get_decrypted_password(
					"Database Server", self.server, "mariadb_root_password"
				),
			},
			reference_doctype=self.server_type,
			reference_name=self.server,
		)

	def fetch_database_variables(self):
		if self.server_type != "Database Server":
			return NotImplementedError("Only Database Server supports this method")
		return self.post(
			"database/variables",
			data={
				"private_ip": frappe.get_value("Database Server", self.server, "private_ip"),
				"mariadb_root_password": get_decrypted_password(
					"Database Server", self.server, "mariadb_root_password"
				),
			},
		)

	def fetch_binlog_list(self):
		return self.get("database/binlogs/list")

	def pull_docker_images(self, image_tags: list[str], reference_doctype=None, reference_name=None):
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)
		return self.create_agent_job(
			"Pull Docker Images",
			"/server/pull-images",
			data={
				"image_tags": image_tags,
				"registry": {
					"url": settings.docker_registry_url,
					"username": settings.docker_registry_username,
					"password": settings.docker_registry_password,
				},
			},
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def push_docker_images(
		self, images: list[str], reference_doctype: str | None = None, reference_name: str | None = None
	) -> AgentJob:
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)
		return self.create_agent_job(
			"Push Images to Registry",
			"/server/push-images",
			data={
				"images": images,
				"registry_settings": {
					"url": settings.docker_registry_url,
					"username": settings.docker_registry_username,
					"password": settings.docker_registry_password,
				},
			},
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def upload_binlogs_to_s3(self, binlogs: list[str]):
		from press.press.doctype.site_backup.site_backup import get_backup_bucket

		if self.server_type != "Database Server":
			return NotImplementedError("Only Database Server supports this method")

		settings = frappe.get_single("Press Settings")
		backup_bucket = get_backup_bucket(
			frappe.get_value("Database Server", self.server, "cluster"), region=True
		)
		bucket_name = backup_bucket.get("name") if isinstance(backup_bucket, dict) else backup_bucket
		if not (settings.aws_s3_bucket or bucket_name):
			return ValueError("Offsite Backups aren't set yet")

		auth = {
			"ACCESS_KEY": settings.offsite_backups_access_key_id,
			"SECRET_KEY": settings.get_password("offsite_backups_secret_access_key"),
			"REGION": backup_bucket.get("region") if isinstance(backup_bucket, dict) else "",
		}

		return self.create_agent_job(
			"Upload Binlogs To S3",
			"/database/binlogs/upload",
			data={"binlogs": binlogs, "offsite": {"bucket": bucket_name, "auth": auth, "path": self.server}},
		)

	def add_binlogs_to_indexer(self, binlogs):
		return self.create_agent_job(
			"Add Binlogs To Indexer",
			"/database/binlogs/indexer/add",
			data={"binlogs": binlogs},
		)

	def remove_binlogs_from_indexer(self, binlogs):
		return self.create_agent_job(
			"Remove Binlogs From Indexer", "/database/binlogs/indexer/remove", data={"binlogs": binlogs}
		)

	def get_binlogs_timeline(
		self,
		start: int,
		end: int,
		database: str,
		table: str | None = None,
		type: str | None = None,
		event_size_comparator: Literal["gt", "lt"] | None = None,
		event_size: int | None = None,
	):
		return self.post(
			"/database/binlogs/indexer/timeline",
			data={
				"start_timestamp": start,
				"end_timestamp": end,
				"database": database,
				"table": table,
				"type": type,
				"event_size_comparator": event_size_comparator,
				"event_size": event_size,
			},
		)

	def search_binlogs(
		self,
		start: int,
		end: int,
		database: str,
		type: str | None = None,
		table: str | None = None,
		search_str: str | None = None,
		event_size_comparator: Literal["gt", "lt"] | None = None,
		event_size: int | None = None,
	):
		return self.post(
			"/database/binlogs/indexer/search",
			data={
				"start_timestamp": start,
				"end_timestamp": end,
				"database": database,
				"type": type,
				"table": table,
				"search_str": search_str,
				"event_size_comparator": event_size_comparator,
				"event_size": event_size,
			},
		)

	def purge_binlog(self, database_server: DatabaseServer, to_binlog: str):
		return self.post(
			"/database/binlogs/purge",
			data={
				"private_ip": database_server.private_ip,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
				"to_binlog": to_binlog,
			},
		)

	def purge_binlogs_by_size_limit(self, database_server: DatabaseServer, max_binlog_gb: int):
		return self.create_agent_job(
			"Purge Binlogs By Size Limit",
			"/database/binlogs/purge_by_size_limit",
			data={
				"private_ip": database_server.private_ip,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
				"max_binlog_gb": max_binlog_gb,
			},
		)

	def get_binlog_queries(self, row_ids: dict[str, list[int]], database: str):
		return self.post(
			"/database/binlogs/indexer/query",
			data={
				"row_ids": row_ids,
				"database": database,
			},
		)

	def ping_database(self, database_server: DatabaseServer):
		return self.post(
			"/database/ping",
			data={
				"private_ip": database_server.private_ip,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
			},
		)

	def get_replication_status(self, database_server: DatabaseServer):
		return self.post(
			"/database/replication/status",
			data={
				"private_ip": database_server.private_ip,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
			},
		)

	def reset_replication(self, database_server: DatabaseServer):
		return self.post(
			"/database/replication/reset",
			data={
				"private_ip": database_server.private_ip,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
			},
		)

	def configure_replication(
		self,
		database_server: DatabaseServer,
		master_database_server: DatabaseServer,
		gtid_slave_pos: str | None = None,
	):
		return self.post(
			"/database/replication/config",
			data={
				"private_ip": database_server.private_ip,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
				"master_private_ip": master_database_server.private_ip,
				"master_mariadb_root_password": master_database_server.get_password("mariadb_root_password"),
				"gtid_slave_pos": gtid_slave_pos,
			},
		)

	def start_replication(self, database_server: DatabaseServer):
		return self.post(
			"/database/replication/start",
			data={
				"private_ip": database_server.private_ip,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
			},
		)

	def stop_replication(self, database_server: DatabaseServer):
		return self.post(
			"/database/replication/stop",
			data={
				"private_ip": database_server.private_ip,
				"mariadb_root_password": database_server.get_password("mariadb_root_password"),
			},
		)

	# Snapshot Recovery Related Methods
	def search_sites_in_snapshot(self, sites: list[str], reference_doctype=None, reference_name=None):
		return self.create_agent_job(
			"Search Sites In Snapshot",
			"/snapshot_recovery/search_sites",
			data={"sites": sites},
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def backup_site_database_from_snapshot(
		self,
		cluster: str,
		site: str,
		database_name: str,
		database_server: str,
		reference_doctype=None,
		reference_name=None,
	):
		from press.press.doctype.site_backup.site_backup import get_backup_bucket

		database_server_doc: DatabaseServer = frappe.get_doc("Database Server", database_server)  # type: ignore
		data = {
			"site": site,
			"database_name": database_name,
			"database_ip": frappe.get_value(
				"Virtual Machine", database_server_doc.virtual_machine, "private_ip_address"
			),
			"mariadb_root_password": database_server_doc.get_password("mariadb_root_password"),
		}

		# offsite config
		settings = frappe.get_single("Press Settings")
		backups_path = os.path.join(site, str(date.today()))
		backup_bucket = get_backup_bucket(cluster, region=True)
		bucket_name = backup_bucket.get("name") if isinstance(backup_bucket, dict) else backup_bucket
		if settings.aws_s3_bucket or bucket_name:
			auth = {
				"ACCESS_KEY": settings.offsite_backups_access_key_id,
				"SECRET_KEY": settings.get_password("offsite_backups_secret_access_key"),
				"REGION": backup_bucket.get("region") if isinstance(backup_bucket, dict) else "",
			}
			data.update({"offsite": {"bucket": bucket_name, "auth": auth, "path": backups_path}})
		else:
			frappe.throw("Offsite Backups aren't setup yet")

		return self.create_agent_job(
			"Backup Database From Snapshot",
			"/snapshot_recovery/backup_database",
			data=data,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def backup_site_files_from_snapshot(
		self,
		cluster: str,
		site: str,
		bench: str,
		reference_doctype=None,
		reference_name=None,
	):
		from press.press.doctype.site_backup.site_backup import get_backup_bucket

		data: dict[str, Any] = {
			"site": site,
			"bench": bench,
		}

		# offsite config
		settings = frappe.get_single("Press Settings")
		backups_path = os.path.join(site, str(date.today()))
		backup_bucket = get_backup_bucket(cluster, region=True)
		bucket_name = backup_bucket.get("name") if isinstance(backup_bucket, dict) else backup_bucket
		if settings.aws_s3_bucket or bucket_name:
			auth = {
				"ACCESS_KEY": settings.offsite_backups_access_key_id,
				"SECRET_KEY": settings.get_password("offsite_backups_secret_access_key"),
				"REGION": backup_bucket.get("region") if isinstance(backup_bucket, dict) else "",
			}
			data.update({"offsite": {"bucket": bucket_name, "auth": auth, "path": backups_path}})
		else:
			frappe.throw("Offsite Backups aren't setup yet")

		return self.create_agent_job(
			"Backup Files From Snapshot",
			"/snapshot_recovery/backup_files",
			data=data,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def update_database_host_in_all_benches(
		self, db_host: str, reference_doctype: str | None = None, reference_name: str | None = None
	):
		return self.create_agent_job(
			"Update Database Host",
			"/benches/database_host",
			data={
				"db_host": db_host,
			},
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def change_bench_directory(
		self,
		secondary_server_private_ip: str,
		is_primary: bool,
		directory: str,
		restart_benches: bool,
		reference_name: str | None = None,
		redis_connection_string_ip: str | None = None,
		reference_doctype: str | None = None,
		registry_settings: dict | None = None,
	) -> AgentJob:
		return self.create_agent_job(
			"Change Bench Directory",
			"/server/change-bench-directory",
			data={
				"restart_benches": restart_benches,
				"redis_connection_string_ip": redis_connection_string_ip,
				"is_primary": is_primary,
				"directory": directory,
				"secondary_server_private_ip": secondary_server_private_ip,
				"registry_settings": registry_settings,
			},
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def add_servers_to_acl(
		self,
		secondary_server_private_ip: str,
		reference_doctype: str | None = None,
		reference_name: str | None = None,
	) -> AgentJob:
		return self.create_agent_job(
			"Add Servers to ACL",
			"/nfs/add-to-acl",
			data={
				"secondary_server_private_ip": secondary_server_private_ip,
			},
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def remove_servers_from_acl(
		self,
		secondary_server_private_ip: str,
		reference_doctype: str | None = None,
		reference_name: str | None = None,
	) -> AgentJob:
		return self.create_agent_job(
			"Remove Servers from ACL",
			"/nfs/remove-from-acl",
			data={
				"secondary_server_private_ip": secondary_server_private_ip,
			},
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def stop_bench_workers(
		self, reference_doctype: str | None = None, reference_name: str | None = None
	) -> AgentJob:
		return self.create_agent_job(
			"Stop Bench Workers",
			"/server/stop-bench-workers",
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def start_bench_workers(
		self, reference_doctype: str | None = None, reference_name: str | None = None
	) -> AgentJob:
		return self.create_agent_job(
			"Start Bench Workers",
			"/server/start-bench-workers",
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def remove_redis_localhost_bind(
		self, reference_doctype: str | None = None, reference_name: str | None = None
	) -> AgentJob:
		return self.create_agent_job(
			"Remove Redis Localhost Bind",
			"/server/remove-localhost-redis-bind",
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def force_remove_all_benches(
		self, reference_doctype: str | None = None, reference_name: str | None = None
	) -> AgentJob:
		return self.create_agent_job(
			"Force Remove All Benches",
			"/server/force-remove-all-benches",
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)

	def update_nginx_access(self, ip_accept: list[str], ip_drop: list[str]) -> AgentJob:
		return self.create_agent_job(
			"Update Nginx Access",
			"/server/update-nginx-access",
			data={
				"ip_access": ip_accept,
				"ip_drop": ip_drop,
			},
		)


class AgentCallbackException(Exception):
	pass


class AgentRequestSkippedException(Exception):
	pass
