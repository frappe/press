# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import json
import re
from collections import defaultdict
from typing import Any, Dict, List

import boto3
import dateutil.parser
import frappe
import requests
from frappe.core.utils import find
from frappe.frappeclient import FrappeClient
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cint, cstr, get_datetime

try:
	from frappe.utils import convert_utc_to_user_timezone
except ImportError:
	from frappe.utils import convert_utc_to_system_timezone as convert_utc_to_user_timezone

from frappe.utils.password import get_decrypted_password
from frappe.utils.user import is_system_user

from press.agent import Agent
from press.api.site import check_dns
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.plan.plan import get_plan_config
from press.press.doctype.site_activity.site_activity import log_site_activity
from press.utils import convert, get_client_blacklisted_keys, guess_type, log_error
from press.press.doctype.site_analytics.site_analytics import create_site_analytics
from press.press.doctype.marketplace_app.marketplace_app import marketplace_app_hook


class Site(Document):
	def _get_site_name(self, subdomain: str):
		"""Get full site domain name given subdomain."""
		if not self.domain:
			self.domain = frappe.db.get_single_value("Press Settings", "domain")
		return f"{subdomain}.{self.domain}"

	def autoname(self):
		self.name = self._get_site_name(self.subdomain)

	def validate(self):
		if self.has_value_changed("subdomain"):
			self.validate_site_name()
		self.set_site_admin_password()
		self.validate_installed_apps()
		self.validate_host_name()
		self.validate_site_config()
		self.validate_auto_update_fields()

	def before_insert(self):
		# initialize site.config based on plan
		self._update_configuration(self.get_plan_config(), save=False)
		if not self.notify_email and self.team != "Administrator":
			self.notify_email = frappe.db.get_value("Team", self.team, "notify_email")

	def validate_site_name(self):
		site_regex = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$"
		if not re.match(site_regex, self.subdomain):
			frappe.throw(
				"Subdomain contains invalid characters. Use lowercase"
				" characters, numbers and hyphens"
			)
		if len(self.subdomain) > 32:
			frappe.throw("Subdomain too long. Use 32 or less characters")

		if len(self.subdomain) < 5:
			frappe.throw("Subdomain too short. Use 5 or more characters")

	def set_site_admin_password(self):
		# set site.admin_password if doesn't exist
		if not self.admin_password:
			self.admin_password = frappe.generate_hash(length=16)

	def validate_installed_apps(self):
		# validate apps to be installed on site
		bench_apps = frappe.get_doc("Bench", self.bench).apps
		for app in self.apps:
			if not find(bench_apps, lambda x: x.app == app.app):
				frappe.throw(f"app {app.app} is not available on Bench {self.bench}.")

		if self.apps[0].app != "frappe":
			frappe.throw("First app to be installed on site must be frappe.")

		site_apps = [app.app for app in self.apps]
		if len(site_apps) != len(set(site_apps)):
			frappe.throw("Can't install same app twice.")

		# Install apps in the same order as bench
		if self.is_new():
			bench_app_names = [app.app for app in bench_apps]
			self.apps.sort(key=lambda x: bench_app_names.index(x.app))

	def validate_host_name(self):
		# set or update site.host_name
		if self.is_new():
			self.host_name = self.name
			self._update_configuration({"host_name": f"https://{self.host_name}"}, save=False)
		elif self.has_value_changed("host_name"):
			self._validate_host_name()

	def validate_site_config(self):
		# update site._keys_removed_in_last_update value
		old_keys = json.loads(self.config)
		new_keys = [x.key for x in self.configuration]
		self._keys_removed_in_last_update = json.dumps(
			[x for x in old_keys if x not in new_keys]
		)

		# generate site.config from site.configuration
		self.update_config_preview()

		# create an agent request if config has been updated
		# if not self.is_new() and self.has_value_changed("config"):
		# 	Agent(self.server).update_site_config(self)

	def validate_auto_update_fields(self):
		# Validate day of month
		if not (1 <= self.update_on_day_of_month <= 31):
			frappe.throw("Day of the month must be between 1 and 31 (included)!")

	def on_update(self):
		if self.status == "Active" and self.has_value_changed("host_name"):
			self.update_site_config({"host_name": f"https://{self.host_name}"})
			self._update_redirects_for_all_site_domains()
			frappe.db.set_value("Site Domain", self.host_name, "redirect_to_primary", False)

		self.update_subscription()

		if self.status not in ["Pending", "Archived", "Suspended"] and self.has_value_changed(
			"subdomain"
		):
			self.rename(self._get_site_name(self.subdomain))

	def rename_upstream(self, new_name: str):
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		site_domains = frappe.get_all(
			"Site Domain", {"site": self.name, "name": ("!=", self.name)}, pluck="name"
		)
		agent.rename_upstream_site(self.server, self, new_name, site_domains)

	@frappe.whitelist()
	def retry_rename(self):
		"""Retry rename with current subdomain"""
		if not self.name == self._get_site_name(self.subdomain):
			self.rename(self._get_site_name(self.subdomain))
		else:
			frappe.throw("Please choose a different subdomain")

	@frappe.whitelist()
	def retry_archive(self):
		"""Retry archive with subdomain+domain name of site"""
		site_name = self.subdomain + "." + self.domain
		if frappe.db.exists("Site", {"name": site_name, "bench": self.bench}):
			frappe.throw(f"Another site already exists in {self.bench} with name: {site_name}")
		self.archive(site_name=site_name, reason="Retry Archive")

	def rename(self, new_name: str):
		self.create_dns_record()
		agent = Agent(self.server)
		agent.rename_site(self, new_name)
		self.rename_upstream(new_name)
		self.status = "Pending"
		self.save()

		try:
			# remove old dns record from route53 after rename
			domain = frappe.get_doc("Root Domain", self.domain)
			proxy_server = frappe.get_value("Server", self.server, "proxy_server")
			self.remove_dns_record(domain, proxy_server, self.name)
		except Exception:
			log_error("Removing Old Site from Route53 Failed")

	def update_config_preview(self):
		"""Regenrates site.config on each site.validate from the site.configuration child table data"""
		new_config = {}

		# Update from site.configuration
		for row in self.configuration:
			# update internal flag from master
			row.internal = frappe.db.get_value("Site Config Key", row.key, "internal")
			key_type = row.type or row.get_type()
			if key_type == "Password":
				# we don't support password type yet!
				key_type = "String"
			row.type = key_type

			if key_type == "Number":
				key_value = (
					int(row.value) if isinstance(row.value, (float, int)) else json.loads(row.value)
				)
			elif key_type == "Boolean":
				key_value = (
					row.value if isinstance(row.value, bool) else bool(json.loads(cstr(row.value)))
				)
			elif key_type == "JSON":
				key_value = json.loads(cstr(row.value))
			else:
				key_value = row.value

			new_config[row.key] = key_value

		self.config = json.dumps(new_config, indent=4)

	def install_app(self, app):
		if not find(self.apps, lambda x: x.app == app):
			log_site_activity(self.name, "Install App")
			self.append("apps", {"app": app})
			agent = Agent(self.server)
			agent.install_app_site(self, app)
			self.status = "Pending"
			self.save()

			marketplace_app_hook(app=app, site=self.name, op="install")

	def uninstall_app(self, app):
		app_doc = find(self.apps, lambda x: x.app == app)
		log_site_activity(self.name, "Uninstall App")
		self.remove(app_doc)
		agent = Agent(self.server)
		agent.uninstall_app_site(self, app_doc.app)
		self.status = "Pending"
		self.save()

		marketplace_app_hook(app=app, site=self.name, op="uninstall")

	def _create_default_site_domain(self):
		"""Create Site Domain with Site name."""
		return frappe.get_doc(
			{
				"doctype": "Site Domain",
				"site": self.name,
				"domain": self.name,
				"status": "Active",
				"retry_count": 0,
				"dns_type": "A",
			}
		).insert(ignore_if_duplicate=True)

	def after_insert(self):
		# log activity
		log_site_activity(self.name, "Create")
		self._create_default_site_domain()
		self.create_dns_record()
		self.create_agent_request()

	@frappe.whitelist()
	def create_dns_record(self):
		"""Check if site needs dns records and creates one."""
		domain = frappe.get_doc("Root Domain", self.domain)
		if self.cluster == domain.default_cluster:
			return
		proxy_server = frappe.get_value("Server", self.server, "proxy_server")
		self._change_dns_record("UPSERT", domain, proxy_server)

	def remove_dns_record(self, domain: Document, proxy_server: str, site: str):
		"""Remove dns record of site pointing to proxy."""
		self._change_dns_record("DELETE", domain, proxy_server, site)

	def _change_dns_record(
		self, method: str, domain: Document, proxy_server: str, site: str = None
	):
		"""
		Change dns record of site

		method: CREATE | DELETE | UPSERT
		"""
		try:
			site_name = self._get_site_name(self.subdomain) if not site else site
			client = boto3.client(
				"route53",
				aws_access_key_id=domain.aws_access_key_id,
				aws_secret_access_key=domain.get_password("aws_secret_access_key"),
			)
			zones = client.list_hosted_zones_by_name()["HostedZones"]
			hosted_zone = find(reversed(zones), lambda x: domain.name.endswith(x["Name"][:-1]))[
				"Id"
			]
			client.change_resource_record_sets(
				ChangeBatch={
					"Changes": [
						{
							"Action": method,
							"ResourceRecordSet": {
								"Name": site_name,
								"Type": "CNAME",
								"TTL": 600,
								"ResourceRecords": [{"Value": proxy_server}],
							},
						}
					]
				},
				HostedZoneId=hosted_zone,
			)
		except Exception:
			log_error(
				"Route 53 Record Creation Error",
				domain=domain.name,
				site=site_name,
				proxy_server=proxy_server,
			)

	def create_agent_request(self):
		agent = Agent(self.server)
		if self.remote_database_file:
			agent.new_site_from_backup(self, skip_failing_patches=self.skip_failing_patches)
		else:
			agent.new_site(self)

		server = frappe.get_all(
			"Server", filters={"name": self.server}, fields=["proxy_server"], limit=1
		)[0]

		agent = Agent(server.proxy_server, server_type="Proxy Server")
		agent.new_upstream_site(self.server, self.name)

	@frappe.whitelist()
	def reinstall(self):
		log_site_activity(self.name, "Reinstall")
		agent = Agent(self.server)
		agent.reinstall_site(self)
		self.status = "Pending"
		self.save()

	@frappe.whitelist()
	def migrate(self, skip_failing_patches=False):
		log_site_activity(self.name, "Migrate")
		agent = Agent(self.server)
		activate = True
		if self.status in ("Inactive", "Suspended"):
			activate = False
			self.status_before_update = self.status
		elif self.status == "Broken" and self.status_before_update in (
			"Inactive",
			"Suspended",
		):
			activate = False
		agent.migrate_site(self, skip_failing_patches=skip_failing_patches, activate=activate)
		self.status = "Pending"
		self.save()

	@frappe.whitelist()
	def last_migrate_failed(self):
		"""Returns `True` if the last site update's(`Migrate` deploy type) migrate site job step failed, `False` otherwise"""

		site_update = frappe.get_all(
			"Site Update",
			filters={"site": self.name},
			fields=["status", "update_job", "deploy_type"],
			limit=1,
			order_by="creation desc",
		)

		if not (site_update and site_update[0].deploy_type == "Migrate"):
			return False
		site_update = site_update[0]

		if site_update.status == "Recovered":
			migrate_site_step = frappe.get_all(
				"Agent Job Step",
				filters={"step_name": "Migrate Site", "agent_job": site_update.update_job},
				fields=["status"],
				limit=1,
			)

			if migrate_site_step and migrate_site_step[0].status == "Failure":
				return True

		return False

	@frappe.whitelist()
	def restore_tables(self):
		self.status_before_update = self.status
		agent = Agent(self.server)
		agent.restore_site_tables(self)
		self.status = "Pending"
		self.save()

	@frappe.whitelist()
	def clear_site_cache(self):
		log_site_activity(self.name, "Clear Cache")
		agent = Agent(self.server)
		agent.clear_site_cache(self)

	@frappe.whitelist()
	def restore_site(self, skip_failing_patches=False):
		if not frappe.get_doc("Remote File", self.remote_database_file).exists():
			raise Exception(
				"Remote File {0} is unavailable on S3".format(self.remote_database_file)
			)

		log_site_activity(self.name, "Restore")
		agent = Agent(self.server)
		agent.restore_site(self, skip_failing_patches=skip_failing_patches)
		self.status = "Pending"
		self.save()

	@frappe.whitelist()
	def backup(self, with_files=False, offsite=False):
		return frappe.get_doc(
			{
				"doctype": "Site Backup",
				"site": self.name,
				"with_files": with_files,
				"offsite": offsite,
			}
		).insert()

	@frappe.whitelist()
	def schedule_update(self, skip_failing_patches=False, skip_backups=False):
		log_site_activity(self.name, "Update")
		self.status_before_update = self.status
		self.status = "Pending"
		self.save()
		frappe.get_doc(
			{
				"doctype": "Site Update",
				"site": self.name,
				"skipped_failing_patches": skip_failing_patches,
				"skipped_backups": skip_backups,
			}
		).insert()

	@frappe.whitelist()
	def move_to_group(self, group, skip_failing_patches=False):
		log_site_activity(self.name, "Update")
		self.status_before_update = self.status
		self.status = "Pending"
		self.save()
		return frappe.get_doc(
			{
				"doctype": "Site Update",
				"site": self.name,
				"destination_group": group,
				"skipped_failing_patches": skip_failing_patches,
			}
		).insert()

	@frappe.whitelist()
	def move_to_bench(self, bench, deactivate=True, skip_failing_patches=False):
		log_site_activity(self.name, "Update")
		self.status_before_update = self.status
		self.status = "Pending"
		self.save()
		agent = Agent(self.server)
		agent.move_site_to_bench(self, bench, deactivate, skip_failing_patches)

	def reset_previous_status(self):
		self.status = self.status_before_update
		self.status_before_update = None
		if not self.status:
			status_map = {402: "Suspended", 503: "Inactive"}
			try:
				response = requests.get(f"https://{self.name}")
				self.status = status_map.get(response.status_code, "Active")
			except Exception:
				log_error("Site Status Fetch Error", site=self.name)
		self.save()

	@frappe.whitelist()
	def update_without_backup(self):
		log_site_activity(self.name, "Update without Backup")
		self.status_before_update = self.status
		self.status = "Pending"
		self.save()
		frappe.get_doc(
			{
				"doctype": "Site Update",
				"site": self.name,
				"skipped_backups": 1,
			}
		).insert()

	@frappe.whitelist()
	def add_domain(self, domain):
		domain = domain.lower()
		if check_dns(self.name, domain):
			log_site_activity(self.name, "Add Domain")
			frappe.get_doc(
				{
					"doctype": "Site Domain",
					"status": "Pending",
					"site": self.name,
					"domain": domain,
					"dns_type": "CNAME",
					"ssl": False,
				}
			).insert()

	def get_config_value_for_key(self, key: str) -> Any:
		"""
		Get site config value configuration child table for given key.

		:returns: None if key not in config.
		"""
		key_obj = find(self.configuration, lambda x: x.key == key)
		if key_obj:
			return json.loads(key_obj.get("value"))
		return None

	def add_domain_to_config(self, domain: str):
		domains = self.get_config_value_for_key("domains") or []
		domains.append(domain)
		self._update_configuration({"domains": domains})
		agent = Agent(self.server)
		agent.add_domain(self, domain)

	def remove_domain_from_config(self, domain):
		domains = self.get_config_value_for_key("domains")
		domains.remove(domain)
		self._update_configuration({"domains": domains})
		agent = Agent(self.server)
		agent.remove_domain(self, domain)

	def remove_domain(self, domain):
		if domain == self.name:
			raise Exception("Cannot delete default site_domain")
		site_domain = frappe.get_all(
			"Site Domain", filters={"site": self.name, "domain": domain}
		)[0]
		site_domain = frappe.delete_doc("Site Domain", site_domain.name)

	def retry_add_domain(self, domain):
		if check_dns(self.name, domain):
			site_domain = frappe.get_all(
				"Site Domain",
				filters={
					"site": self.name,
					"domain": domain,
					"status": ("!=", "Active"),
					"retry_count": ("<=", 5),
				},
			)[0]
			site_domain = frappe.get_doc("Site Domain", site_domain.name)
			site_domain.retry()

	def _check_if_domain_belongs_to_site(self, domain: str):
		if not frappe.db.exists(
			{"doctype": "Site Domain", "site": self.name, "domain": domain}
		):
			frappe.throw(
				msg=f"Site Domain {domain} for site {self.name} does not exist",
				exc=frappe.exceptions.LinkValidationError,
			)

	def _check_if_domain_is_active(self, domain: str):
		status = frappe.get_value("Site Domain", domain, "status")
		if status != "Active":
			frappe.throw(
				msg="Only active domains can be primary", exc=frappe.LinkValidationError
			)

	def _validate_host_name(self):
		"""Perform checks for primary domain."""
		self._check_if_domain_belongs_to_site(self.host_name)
		self._check_if_domain_is_active(self.host_name)

	def set_host_name(self, domain: str):
		"""Set host_name/primary domain of site."""
		self.host_name = domain
		self.save()

	def _get_redirected_domains(self) -> List[str]:
		"""Get list of redirected site domains for site."""
		return frappe.get_all(
			"Site Domain",
			filters={"site": self.name, "redirect_to_primary": True},
			pluck="name",
		)

	def _update_redirects_for_all_site_domains(self):
		domains = self._get_redirected_domains()
		if domains:
			return self.set_redirects_in_proxy(domains)

	def _remove_redirects_for_all_site_domains(self):
		domains = self._get_redirected_domains()
		if domains:
			self.unset_redirects_in_proxy(domains)

	def set_redirects_in_proxy(self, domains: List[str]):
		target = self.host_name
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		return agent.setup_redirects(self.name, domains, target)

	def unset_redirects_in_proxy(self, domains: List[str]):
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.remove_redirects(self.name, domains)

	def set_redirect(self, domain: str):
		"""Enable redirect to primary for domain."""
		self._check_if_domain_belongs_to_site(domain)
		site_domain = frappe.get_doc("Site Domain", domain)
		site_domain.setup_redirect()

	def unset_redirect(self, domain: str):
		"""Disable redirect to primary for domain."""
		self._check_if_domain_belongs_to_site(domain)
		site_domain = frappe.get_doc("Site Domain", domain)
		site_domain.remove_redirect()

	@frappe.whitelist()
	def archive(self, site_name=None, reason=None, force=False):
		log_site_activity(self.name, "Archive", reason)
		agent = Agent(self.server)
		self.status = "Pending"
		self.save()
		agent.archive_site(self, site_name, force)

		server = frappe.get_all(
			"Server", filters={"name": self.server}, fields=["proxy_server"], limit=1
		)[0]

		agent = Agent(server.proxy_server, server_type="Proxy Server")
		agent.remove_upstream_site(self.server, self.name, site_name)

		self.db_set("host_name", None)

		self.delete_offsite_backups()
		frappe.db.set_value(
			"Site Backup",
			{"site": self.name, "offsite": False},
			"files_availability",
			"Unavailable",
		)
		self.disable_subscription()
		self.disable_marketplace_subscriptions()

	@frappe.whitelist()
	def cleanup_after_archive(self):
		site_cleanup_after_archive(self.name)

	def delete_offsite_backups(self):
		from press.press.doctype.remote_file.remote_file import delete_remote_backup_objects

		log_site_activity(self.name, "Drop Offsite Backups")

		sites_remote_files = []
		site_backups = frappe.get_all(
			"Site Backup",
			filters={"site": self.name, "offsite": True, "files_availability": "Available"},
			pluck="name",
			order_by="creation desc",
		)[
			1:
		]  # Keep latest backup
		for backup_files in frappe.get_all(
			"Site Backup",
			filters={"name": ("in", site_backups)},
			fields=["remote_database_file", "remote_public_file", "remote_private_file"],
			as_list=True,
			order_by="creation desc",
		):
			sites_remote_files += backup_files

		if not sites_remote_files:
			return

		frappe.db.set_value(
			"Site Backup",
			{"name": ("in", site_backups), "offsite": True},
			"files_availability",
			"Unavailable",
		)

		return delete_remote_backup_objects(sites_remote_files)

	def login(self, reason=None):
		log_site_activity(self.name, "Login as Administrator", reason=reason)
		return self.get_login_sid()

	def get_connection_as_admin(self):
		password = get_decrypted_password("Site", self.name, "admin_password")
		conn = FrappeClient(f"https://{self.name}", "Administrator", password)

		return conn

	def get_login_sid(self):
		password = get_decrypted_password("Site", self.name, "admin_password")
		response = requests.post(
			f"https://{self.name}/api/method/login",
			data={"usr": "Administrator", "pwd": password},
		)
		sid = response.cookies.get("sid")
		if not sid:
			agent = Agent(self.server)
			sid = agent.get_site_sid(self)
		if not sid or sid == "Guest":
			frappe.throw("Could not login as Administrator", frappe.ValidationError)
		return sid

	def fetch_info(self):
		agent = Agent(self.server)
		return agent.get_site_info(self)

	def fetch_analytics(self):
		agent = Agent(self.server)
		return agent.get_site_analytics(self)

	def get_disk_usages(self):
		try:
			last_usage = frappe.get_last_doc("Site Usage", {"site": self.name})
		except frappe.DoesNotExistError:
			return defaultdict(lambda: None)

		return {
			"database": last_usage.database,
			"backups": last_usage.backups,
			"public": last_usage.public,
			"private": last_usage.private,
		}

	def _sync_config_info(self, fetched_config: Dict) -> bool:
		"""Update site doc config with the fetched_config values.

		:fetched_config: Generally data passed is the config part of the agent info response
		:returns: True if value has changed
		"""
		config = {
			key: fetched_config[key]
			for key in fetched_config
			if key not in get_client_blacklisted_keys()
		}
		new_config = {**json.loads(self.config or "{}"), **config}
		current_config = json.dumps(new_config, indent=4)

		if self.config != current_config:
			self._update_configuration(new_config, save=False)
			return True
		return False

	def _sync_usage_info(self, fetched_usage: Dict):
		"""Generate a Site Usage doc for the site using the fetched_usage data.

		:fetched_usage: Requires backups, database, public, private keys with Numeric values
		"""

		def _insert_usage(usage: dict):
			current_usages = self.get_disk_usages()
			site_usage_data = {
				"site": self.name,
				"backups": usage["backups"],
				"database": usage["database"],
				"public": usage["public"],
				"private": usage["private"],
			}

			same_as_last_usage = (
				current_usages["backups"] == site_usage_data["backups"]
				and current_usages["database"] == site_usage_data["database"]
				and current_usages["public"] == site_usage_data["public"]
				and current_usages["private"] == site_usage_data["private"]
			)

			if same_as_last_usage:
				return

			equivalent_site_time = None
			if usage.get("timestamp"):
				equivalent_site_time = convert_utc_to_user_timezone(
					dateutil.parser.parse(usage["timestamp"])
				).replace(tzinfo=None)
				if frappe.db.exists(
					"Site Usage", {"site": self.name, "creation": equivalent_site_time}
				):
					return

			site_usage = frappe.get_doc({"doctype": "Site Usage", **site_usage_data}).insert()

			if equivalent_site_time:
				site_usage.db_set("creation", equivalent_site_time)

		if isinstance(fetched_usage, list):
			for usage in fetched_usage:
				_insert_usage(usage)
		else:
			_insert_usage(fetched_usage)

	def _sync_timezone_info(self, timezone: str) -> bool:
		"""Update site doc timezone with the passed value of timezone.

		:timezone: Timezone passed in part of the agent info response
		:returns: True if value has changed
		"""
		if self.timezone != timezone:
			self.timezone = timezone
			return True
		return False

	def _sync_database_name(self, config):
		database_name = config.get("db_name")
		if self.database_name != database_name:
			self.database_name = database_name
			return True
		return False

	@frappe.whitelist()
	def sync_info(self, data=None):
		"""Updates Site Usage, site.config and timezone details for site."""
		if not data:
			data = self.fetch_info()

		fetched_usage = data["usage"]
		fetched_config = data["config"]
		fetched_timezone = data["timezone"]

		self._sync_usage_info(fetched_usage)
		to_save = self._sync_config_info(fetched_config)
		to_save |= self._sync_timezone_info(fetched_timezone)
		to_save |= self._sync_database_name(fetched_config)

		if to_save:
			self.save()

	def sync_analytics(self, analytics=None):
		if not analytics:
			analytics = self.fetch_analytics()
		create_site_analytics(self.name, analytics)

	def is_setup_wizard_complete(self):
		if self.setup_wizard_complete:
			return True

		sid = self.get_login_sid()
		conn = FrappeClient(f"https://{self.name}?sid={sid}")
		value = conn.get_value("System Settings", "setup_complete", "System Settings")
		if value:
			setup_complete = cint(value["setup_complete"])
			self.setup_wizard_complete = setup_complete
			self.save()
			return setup_complete

	def _set_configuration(self, config):
		"""Similar to _update_configuration but will replace full configuration at once
		This is necessary because when you update site config from the UI, you can update the key,
		update the value, remove the key. All of this can be handled by setting the full configuration at once.

		Args:
		config (list): List of dicts with key, value, and type
		"""
		blacklisted_config = [
			x for x in self.configuration if x.key in get_client_blacklisted_keys()
		]
		self.configuration = []

		# Maintain keys that aren't accessible to Dashboard user
		for i, _config in enumerate(blacklisted_config):
			_config.idx = i + 1
			self.configuration.append(_config)

		for d in config:
			d = frappe._dict(d)
			if isinstance(d.value, (dict, list)):
				value = json.dumps(d.value)
			else:
				value = d.value
			self.append("configuration", {"key": d.key, "value": value, "type": d.type})
		self.save()

	def _update_configuration(self, config, save=True):
		"""Updates site.configuration, runs site.save which updates site.config

		Args:
		config (dict): Python dict for any suitable frappe.conf
		"""
		keys = {x.key: i for i, x in enumerate(self.configuration)}
		for key, value in config.items():
			if key in keys:
				self.configuration[keys[key]].value = convert(value)
				self.configuration[keys[key]].type = guess_type(value)
			else:
				self.append("configuration", {"key": key, "value": convert(value)})

		if save:
			self.save()

	@frappe.whitelist()
	def update_site_config(self, config=None):
		"""Updates site.configuration, site.config and runs site.save which initiates an Agent Request
		This checks for the blacklisted config keys via Frappe Validations, but not for internal usages.
		Don't expose this directly to an external API. Pass through `press.utils.sanitize_config` or use
		`press.api.site.update_config` instead.

		Args:
		config (dict): Python dict for any suitable frappe.conf
		"""
		if config is None:
			config = {}
		if isinstance(config, list):
			self._set_configuration(config)
		else:
			self._update_configuration(config)
		return Agent(self.server).update_site_config(self)

	def update_site(self):
		log_site_activity(self.name, "Update")

	def create_subscription(self, plan):
		# create a site plan change log
		self._create_initial_site_plan_change(plan)

	def update_subscription(self):
		if self.status in ["Archived", "Broken", "Suspended"]:
			self.disable_subscription()
		else:
			self.enable_subscription()

		if self.has_value_changed("team"):
			subscription = self.subscription
			if subscription:
				subscription.team = self.team
				subscription.save(ignore_permissions=True)

	def enable_subscription(self):
		subscription = self.subscription
		if subscription:
			subscription.enable()

	def disable_subscription(self):
		subscription = self.subscription
		if subscription:
			frappe.db.set_value("Subscription", subscription.name, "enabled", False)

	def disable_marketplace_subscriptions(self):
		app_subscriptions = frappe.get_all(
			"Marketplace App Subscription",
			filters={"site": self.name, "status": "Active"},
			pluck="name",
		)

		for subscription in app_subscriptions:
			subscription_doc = frappe.get_doc("Marketplace App Subscription", subscription)
			subscription_doc.disable()

	def can_change_plan(self, ignore_card_setup):
		if is_system_user(frappe.session.user):
			return

		if ignore_card_setup:
			# ignore card setup for prepaid app payments
			return

		team = frappe.get_doc("Team", self.team)

		if team.is_defaulter():
			frappe.throw("Cannot change plan because you have unpaid invoices")

		if team.payment_mode == "Partner Credits" and (
			not team.get_available_partner_credits() > 0
		):
			frappe.throw("Cannot change plan because you don't have sufficient partner credits")

		if team.payment_mode != "Partner Credits" and not (
			team.default_payment_method or team.get_balance()
		):
			frappe.throw(
				"Cannot change plan because you haven't added a card and not have enough balance"
			)

	def change_plan(self, plan, ignore_card_setup=False):
		self.can_change_plan(ignore_card_setup)
		plan_config = self.get_plan_config(plan)

		if (
			frappe.db.exists(
				"Marketplace App Subscription", {"status": "Active", "site": self.name}
			)
			and self.trial_end_date
		):
			plan_config["app_include_js"] = []

		self._update_configuration(plan_config)
		frappe.get_doc(
			{
				"doctype": "Site Plan Change",
				"site": self.name,
				"from_plan": self.plan,
				"to_plan": plan,
			}
		).insert()

		self.reload()
		if self.status == "Suspended":
			self.unsuspend_if_applicable()
		else:
			# trigger agent job only once
			self.update_site_config(plan_config)

		if self.trial_end_date:
			self.reload()
			self.trial_end_date = ""
			self.save()

	def unsuspend_if_applicable(self):
		try:
			usage = frappe.get_last_doc("Site Usage", {"site": self.name})
		except frappe.DoesNotExistError:
			# If no doc is found, it means the site was created a few moments before
			# team was suspended, potentially due to failure in payment. Don't unsuspend
			# site in that case. team.unsuspend_sites should handle that, then.
			return

		plan_name = self.plan
		# get plan from subscription
		if not plan_name:
			subscription = self.subscription
			if not subscription:
				return
			plan_name = subscription.plan

		plan = frappe.get_doc("Plan", plan_name)

		disk_usage = usage.public + usage.private
		if usage.database < plan.max_database_usage and disk_usage < plan.max_storage_usage:
			self.current_database_usage = (usage.database / plan.max_database_usage) * 100
			self.current_disk_usage = (
				(usage.public + usage.private) / plan.max_storage_usage
			) * 100
			self.unsuspend(reason="Plan Upgraded")

	@frappe.whitelist()
	def deactivate(self):
		log_site_activity(self.name, "Deactivate Site")
		self.status = "Inactive"
		self.update_site_config({"maintenance_mode": 1})
		self.update_site_status_on_proxy("deactivated")

	@frappe.whitelist()
	def activate(self):
		log_site_activity(self.name, "Activate Site")
		self.status = "Active"
		self.update_site_config({"maintenance_mode": 0})
		self.update_site_status_on_proxy("activated")
		self.reactivate_app_subscriptions()

	@frappe.whitelist()
	def suspend(self, reason=None):
		log_site_activity(self.name, "Suspend Site", reason)
		self.status = "Suspended"
		self.update_site_config({"maintenance_mode": 1})
		self.update_site_status_on_proxy("suspended")
		self.deactivate_app_subscriptions()

	def deactivate_app_subscriptions(self):
		frappe.db.set_value(
			"Marketplace App Subscription",
			{"status": "Active", "site": self.name},
			{"status": "Inactive"},
		)

	def reactivate_app_subscriptions(self):
		frappe.db.set_value(
			"Marketplace App Subscription",
			{"status": "Inactive", "site": self.name},
			{"status": "Active"},
		)

	@frappe.whitelist()
	def unsuspend(self, reason=None):
		log_site_activity(self.name, "Unsuspend Site", reason)
		self.status = "Active"
		self.update_site_config({"maintenance_mode": 0})
		self.update_site_status_on_proxy("activated")
		self.reactivate_app_subscriptions()

	@frappe.whitelist()
	def reset_site_usage(self):
		agent = Agent(self.server)
		agent.reset_site_usage(self)

	def update_site_status_on_proxy(self, status):
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.update_site_status(self.server, self.name, status)

	def setup_erpnext(self):
		account_request = frappe.get_doc("Account Request", self.account_request)
		agent = Agent(self.server)
		user = {
			"email": account_request.email,
			"first_name": account_request.first_name,
			"last_name": account_request.last_name,
		}
		config = {
			"setup_config": {
				"country": account_request.country,
				"timezone": account_request.timezone,
				"domain": account_request.domain,
				"currency": account_request.currency,
				"language": account_request.language,
				"company": account_request.company,
			}
		}
		agent.setup_erpnext(self, user, config)

	@property
	def subscription(self):
		name = frappe.db.get_value(
			"Subscription", {"document_type": "Site", "document_name": self.name}
		)
		return frappe.get_doc("Subscription", name) if name else None

	def can_charge_for_subscription(self):
		today = frappe.utils.getdate()
		return (
			self.status not in ["Archived", "Suspended"]
			and self.team
			and self.team != "Administrator"
			and not self.free
			and (
				today > get_datetime(self.trial_end_date).date() if self.trial_end_date else True
			)
		)

	def get_plan_config(self, plan=None):
		if not plan:
			plan = self.subscription_plan if hasattr(self, "subscription_plan") else self.plan
		if not plan:
			return {}
		return get_plan_config(plan)

	def _create_initial_site_plan_change(self, plan):
		frappe.get_doc(
			{
				"doctype": "Site Plan Change",
				"site": self.name,
				"from_plan": "",
				"to_plan": plan,
				"type": "Initial Plan",
				"timestamp": self.creation,
			}
		).insert(ignore_permissions=True)

	@frappe.whitelist()
	def enable_database_access(self, mode="read_only"):
		if not frappe.db.get_value("Plan", self.plan, "database_access"):
			frappe.throw(f"Database Access is not available on {self.plan} plan")
		log_site_activity(self.name, "Enable Database Access")

		server_agent = Agent(self.server)
		credentials = server_agent.create_database_access_credentials(self, mode)
		self.database_access_mode = mode
		self.database_access_user = credentials["user"]
		self.database_access_password = credentials["password"]
		self.save()

		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")

		database_server_name = frappe.db.get_value("Server", self.server, "database_server")
		database_server = frappe.get_doc("Database Server", database_server_name)

		return agent.add_proxysql_user(
			self,
			credentials["database"],
			credentials["user"],
			credentials["password"],
			database_server,
		)

	@frappe.whitelist()
	def disable_database_access(self):
		log_site_activity(self.name, "Disable Database Access")

		server_agent = Agent(self.server)
		server_agent.revoke_database_access_credentials(self)

		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")

		user = self.database_access_user

		self.database_access_mode = None
		self.database_access_user = None
		self.database_access_password = None
		self.save()
		return agent.remove_proxysql_user(self, user)

	@frappe.whitelist()
	def get_database_credentials(self):
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		config = self.fetch_info()["config"]

		return {
			"host": proxy_server,
			"port": 3306,
			"database": config["db_name"],
			"username": self.database_access_user,
			"password": self.get_password("database_access_password"),
			"mode": self.database_access_mode,
		}

	@property
	def server_logs(self):
		return Agent(self.server).get(f"benches/{self.bench}/sites/{self.name}/logs")

	def get_server_log(self, log):
		return Agent(self.server).get(f"benches/{self.bench}/sites/{self.name}/logs/{log}")

	@property
	def has_paid(self) -> bool:
		"""Has the site been paid for by customer."""
		invoice_items = frappe.get_all(
			"Invoice Item",
			{"document_type": self.doctype, "document_name": self.name, "Amount": (">", 0)},
			pluck="parent",
		)
		today = frappe.utils.getdate()
		today_last_month = today.replace(month=today.month - 1)
		last_month_last_date = frappe.utils.get_last_day(today_last_month)
		return frappe.db.exists(
			"Invoice",
			{
				"status": "Paid",
				"name": ("in", invoice_items or ["NULL"]),
				"period_end": (">=", last_month_last_date),
				# this month's or last month's invoice has been paid for
			},
		)

	@classmethod
	def get_sites_for_backup(cls, interval: int):
		sites = cls.get_sites_without_backup_in_interval(interval)
		return frappe.get_all(
			"Site",
			{"name": ("in", sites)},
			["name", "timezone", "server"],
			order_by="server",
			ignore_ifnull=True,
		)

	@classmethod
	def get_sites_without_backup_in_interval(cls, interval: int) -> List[str]:
		"""Return active sites that haven't had backup taken in interval hours."""
		interval_hrs_ago = frappe.utils.add_to_date(None, hours=-interval)
		all_sites = set(
			frappe.get_all(
				"Site",
				{
					"status": "Active",
					"creation": ("<=", interval_hrs_ago),
					"is_standby": False,
					"plan": ("not like", "%Trial"),
				},
				pluck="name",
			)
		)
		return list(all_sites - set(cls.get_sites_with_backup_in_interval(interval_hrs_ago)))
		# TODO: query using creation time of account request for actual new sites <03-09-21, Balamurali M> #

	@classmethod
	def get_sites_with_backup_in_interval(cls, interval_hrs_ago) -> List[str]:
		return frappe.get_all(
			"Site Backup",
			{
				"creation": (">=", interval_hrs_ago),
				"status": ("!=", "Failure"),
				"owner": "Administrator",
			},
			pluck="site",
			ignore_ifnull=True,
		)

	@classmethod
	def exists(cls, subdomain, domain) -> bool:
		"""Check if subdomain is available"""
		banned_domains = frappe.get_all("Blocked Domain", {"block_for_all": 1}, pluck="name")
		if banned_domains and subdomain in banned_domains:
			return True
		else:
			return bool(
				frappe.db.exists("Blocked Domain", {"name": subdomain, "root_domain": domain})
				or frappe.db.exists(
					"Site", {"subdomain": subdomain, "domain": domain, "status": ("!=", "Archived")}
				)
			)

	@frappe.whitelist()
	def run_after_migrate_steps(self):
		agent = Agent(self.server)
		agent.run_after_migrate_steps(self)


def site_cleanup_after_archive(site):
	delete_site_domains(site)
	delete_site_subdomain(site)
	release_name(site)


def delete_site_subdomain(site):
	site_doc = frappe.get_doc("Site", site)
	domain = frappe.get_doc("Root Domain", site_doc.domain)
	proxy_server = frappe.get_value("Server", site_doc.server, "proxy_server")
	site_doc.remove_dns_record(domain, proxy_server, site)


def delete_site_domains(site):
	domains = frappe.get_all("Site Domain", {"site": site})
	for domain in domains:
		frappe.delete_doc("Site Domain", domain.name)


def release_name(name):
	if ".archived" in name:
		return
	new_name = f"{name}.archived"
	new_name = append_number_if_name_exists("Site", new_name, separator=".")
	frappe.rename_doc("Site", name, new_name)


def process_new_site_job_update(job):
	other_job_types = {
		"Add Site to Upstream": ("New Site", "New Site from Backup"),
		"New Site": ("Add Site to Upstream",),
		"New Site from Backup": ("Add Site to Upstream",),
	}[job.job_type]

	first = job.status
	second = frappe.get_all(
		"Agent Job",
		fields=["status"],
		filters={"job_type": ("in", other_job_types), "site": job.site},
	)[0].status

	backup_tests = frappe.get_all(
		"Backup Restoration Test", dict(test_site=job.site, status="Running"), pluck="name"
	)

	if "Success" == first == second:
		updated_status = "Active"
		marketplace_app_hook(site=job.site, op="install")
	elif "Failure" in (first, second):
		updated_status = "Broken"
	elif "Running" in (first, second):
		updated_status = "Installing"
	else:
		updated_status = "Pending"

	status_map = {
		"Active": "Success",
		"Broken": "Failure",
		"Installing": "Running",
		"Pending": "Running",
	}

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		if backup_tests:
			frappe.db.set_value(
				"Backup Restoration Test", backup_tests[0], "status", status_map[updated_status]
			)
			frappe.db.commit()

		frappe.db.set_value("Site", job.site, "status", updated_status)


def get_remove_step_status(job):
	remove_step_name = {
		"Archive Site": "Archive Site",
		"Remove Site from Upstream": "Remove Site File from Upstream Directory",
	}[job.job_type]

	return frappe.db.get_value(
		"Agent Job Step",
		{"step_name": remove_step_name, "agent_job": job.name},
		"status",
	)


def process_archive_site_job_update(job):
	other_job_type = {
		"Remove Site from Upstream": "Archive Site",
		"Archive Site": "Remove Site from Upstream",
	}[job.job_type]

	other_job = frappe.get_last_doc(
		"Agent Job",
		filters={"job_type": other_job_type, "site": job.site},
	)

	first = get_remove_step_status(job)
	second = get_remove_step_status(other_job)

	if (
		("Success" == first == second)
		or ("Skipped" == first == second)
		or sorted(("Success", "Skipped")) == sorted((first, second))
	):
		updated_status = "Archived"
	elif "Failure" in (first, second):
		updated_status = "Broken"
	else:
		updated_status = "Pending"

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		frappe.db.set_value(
			"Site",
			job.site,
			{"status": updated_status, "archive_failed": updated_status != "Archived"},
		)
		if updated_status == "Archived":
			site_cleanup_after_archive(job.site)


def process_install_app_site_job_update(job):
	updated_status = {
		"Pending": "Active",
		"Running": "Installing",
		"Success": "Active",
		"Failure": "Active",
	}[job.status]

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		frappe.db.set_value("Site", job.site, "status", updated_status)


def process_reinstall_site_job_update(job):
	updated_status = {
		"Pending": "Pending",
		"Running": "Installing",
		"Success": "Active",
		"Failure": "Broken",
	}[job.status]

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		frappe.db.set_value("Site", job.site, "status", updated_status)


def process_migrate_site_job_update(job):
	updated_status = {
		"Pending": "Pending",
		"Running": "Updating",
		"Success": "Active",
		"Failure": "Broken",
	}[job.status]

	if updated_status == "Active":
		site = frappe.get_doc("Site", job.site)
		if site.status_before_update:
			site.reset_previous_status()
			return
	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		frappe.db.set_value("Site", job.site, "status", updated_status)


def get_rename_step_status(job):
	rename_step_name = {
		"Rename Site": "Rename Site",
		"Rename Site on Upstream": "Rename Site File in Upstream Directory",
	}[job.job_type]

	return frappe.db.get_value(
		"Agent Job Step",
		{"step_name": rename_step_name, "agent_job": job.name},
		"status",
	)


def process_rename_site_job_update(job):
	other_job_type = {
		"Rename Site": "Rename Site on Upstream",
		"Rename Site on Upstream": "Rename Site",
	}[job.job_type]

	other_job = frappe.get_last_doc(
		"Agent Job",
		filters={"job_type": other_job_type, "site": job.site},
	)
	first = get_rename_step_status(job)
	second = get_rename_step_status(other_job)

	if "Success" == first == second:
		update_records_for_rename(job)
		# update job obj with new name
		job.reload()
		updated_status = "Active"
		from press.press.doctype.site.pool import create as create_pooled_sites

		create_pooled_sites()

	elif "Failure" in (first, second):
		updated_status = "Broken"
	elif "Running" in (first, second):
		updated_status = "Updating"
	else:
		updated_status = "Pending"

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		frappe.db.set_value("Site", job.site, "status", updated_status)


def process_add_proxysql_user_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Site", job.site, "is_database_access_enabled", True)


def process_remove_proxysql_user_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Site", job.site, "is_database_access_enabled", False)


def process_move_site_to_bench_job_update(job):
	updated_status = {
		"Pending": "Pending",
		"Running": "Updating",
		"Failure": "Broken",
	}.get(job.status)
	if job.status in ("Success", "Failure"):
		dest_bench = json.loads(job.request_data).get("target")
		dest_group = frappe.db.get_value("Bench", dest_bench, "group")

		move_site_step_status = frappe.db.get_value(
			"Agent Job Step", {"step_name": "Move Site", "agent_job": job.name}, "status"
		)
		if move_site_step_status == "Success":
			frappe.db.set_value("Site", job.site, "bench", dest_bench)
			frappe.db.set_value("Site", job.site, "group", dest_group)
	if updated_status:
		frappe.db.set_value("Site", job.site, "status", updated_status)
		return
	if job.status == "Success":
		site = frappe.get_doc("Site", job.site)
		site.reset_previous_status()


def update_records_for_rename(job):
	"""Update press records for successful site rename."""
	data = json.loads(job.request_data)
	new_name = data["new_name"]
	if new_name == job.site:  # idempotency
		return

	site = frappe.get_doc("Site", job.site)
	if site.host_name == job.site:
		# Host name already updated in f server, no need to create another job
		site._update_configuration({"host_name": f"https://{new_name}"})
		site.db_set("host_name", new_name)

	frappe.rename_doc("Site", job.site, new_name)
	frappe.rename_doc("Site Domain", job.site, new_name)


def process_restore_tables_job_update(job):
	updated_status = {
		"Pending": "Pending",
		"Running": "Updating",
		"Success": "Active",
		"Failure": "Broken",
	}[job.status]

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		if updated_status == "Active":
			frappe.get_doc("Site", job.site).reset_previous_status()
		else:
			frappe.db.set_value("Site", job.site, "status", updated_status)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Site")


def prepare_site(site: str, subdomain: str = None) -> Dict:
	# prepare site details
	doc = frappe.get_doc("Site", site)
	sitename = subdomain if subdomain else "brt-" + doc.subdomain
	app_plans = [app.app for app in doc.apps]
	backups = frappe.get_all(
		"Site Backup",
		dict(
			status="Success", with_files=1, site=site, files_availability="Available", offsite=1
		),
		pluck="name",
	)
	if not backups:
		frappe.throw("Backup Files not found.")
	backup = frappe.get_doc("Site Backup", backups[0])

	files = {
		"config": "",  # not necessary for test sites
		"database": backup.remote_database_file,
		"public": backup.remote_public_file,
		"private": backup.remote_private_file,
	}
	site_dict = {
		"domain": frappe.db.get_single_value("Press Settings", "domain"),
		"plan": doc.plan,
		"name": sitename,
		"group": doc.group,
		"selected_app_plans": {},
		"apps": app_plans,
		"files": files,
	}

	return site_dict
