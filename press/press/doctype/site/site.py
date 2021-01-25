# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import re
from typing import Dict, List

import dateutil.parser
import frappe
import requests
from frappe.core.utils import find
from frappe.frappeclient import FrappeClient
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cint, convert_utc_to_user_timezone, cstr
from frappe.utils.password import get_decrypted_password

from press.agent import Agent
from press.api.site import check_dns
from press.press.doctype.plan.plan import get_plan_config
from press.press.doctype.site_activity.site_activity import log_site_activity
from press.utils import convert, get_client_blacklisted_keys, guess_type, log_error


class Site(Document):
	def autoname(self):
		domain = frappe.db.get_single_value("Press Settings", "domain")
		self.name = f"{self.subdomain}.{domain}"

	def validate(self):
		# validate site name
		site_regex = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$"
		if len(self.subdomain) < 5:
			frappe.throw("Subdomain too short. Use 5 or more characters")
		if len(self.subdomain) > 32:
			frappe.throw("Subdomain too long. Use 32 or less characters")
		if not re.match(site_regex, self.subdomain):
			frappe.throw(
				"Subdomain contains invalid characters. Use lowercase"
				" characters, numbers and hyphens"
			)

		# set site.admin_password if doesn't exist
		if not self.admin_password:
			self.admin_password = frappe.generate_hash(length=16)

		# validate site creation and initialize site.config
		if self.is_new() and frappe.session.user != "Administrator":
			self.can_create_site()

			if not self.subscription_plan:
				frappe.throw("Cannot create site without plan")

			self._update_configuration(get_plan_config(self.subscription_plan), save=False)

		# validate apps to be installed on site
		bench_apps = frappe.get_doc("Bench", self.bench).apps
		for app in self.apps:
			if not find(bench_apps, lambda x: x.app == app.app):
				frappe.throw(f"Frappe App {app.app} is not available on Bench {self.bench}.")
		frappe_app = self.apps[0]
		if not frappe.db.get_value("Frappe App", frappe_app.app, "frappe"):
			frappe.throw("First app to be installed on site must be frappe.")
		apps = [app.app for app in self.apps]
		if len(apps) != len(set(apps)):
			frappe.throw("Can't install same app twice.")

		# set or update site.host_name
		if self.is_new():
			self.host_name = self._create_default_site_domain().name
			self._update_configuration({"host_name": f"https://{self.host_name}"}, save=False)
		elif self.has_value_changed("host_name"):
			self._validate_host_name()

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

	def on_update(self):
		if self.status == "Active" and self.has_value_changed("host_name"):
			self.update_site_config({"host_name": f"https://{self.host_name}"})
			self._update_redirects_for_all_site_domains()
			frappe.db.set_value("Site Domain", self.host_name, "redirect_to_primary", False)

		if self.status in ["Inactive", "Archived", "Suspended"]:
			self.disable_subscription()
		if self.status == "Active":
			self.enable_subscription()

	def rename_upstream(self, new_name: str):
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.rename_upstream_site(self.server, new_name)

	def rename(self, new_name: str):
		agent = Agent(self.server)
		agent.rename_site(self, new_name)
		self.rename_upstream(new_name)

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

	def uninstall_app(self, app):
		app_doc = find(self.apps, lambda x: x.app == app)
		log_site_activity(self.name, "Uninstall App")
		self.remove(app_doc)
		agent = Agent(self.server)
		agent.uninstall_app_site(self, app_doc.app)
		self.status = "Pending"
		self.save()

	def can_create_site(self):
		if self.team:
			# validate site creation for team
			team = frappe.get_doc("Team", self.team)
			[allow_creation, why] = team.can_create_site()
			if not allow_creation:
				frappe.throw(why)

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
		).insert(ignore_if_duplicate=True, ignore_links=True)

	def after_insert(self):
		# log activity
		log_site_activity(self.name, "Create")
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.server)
		if self.remote_database_file and self.remote_private_file and self.remote_public_file:
			agent.new_site_from_backup(self)
		else:
			agent.new_site(self)

		server = frappe.get_all(
			"Server", filters={"name": self.server}, fields=["proxy_server"], limit=1
		)[0]

		agent = Agent(server.proxy_server, server_type="Proxy Server")
		agent.new_upstream_site(self.server, self.name)

	def reinstall(self):
		log_site_activity(self.name, "Reinstall")
		agent = Agent(self.server)
		agent.reinstall_site(self)
		self.status = "Pending"
		self.save()

	def migrate(self):
		log_site_activity(self.name, "Migrate")
		agent = Agent(self.server)
		agent.migrate_site(self)
		self.status = "Pending"
		self.save()

	def restore_site(self):
		if not frappe.get_doc("Remote File", self.remote_database_file).exists():
			raise Exception(
				"Remote File {0} is unavailable on S3".format(self.remote_database_file)
			)

		log_site_activity(self.name, "Restore")
		agent = Agent(self.server)
		agent.restore_site(self)
		self.status = "Pending"
		self.save()

	def backup(self, with_files=False, offsite=False):
		if frappe.db.count(
			"Site Backup", {"site": self.name, "status": ("in", ["Running", "Pending"])}
		):
			raise Exception("Too many pending backups")

		log_site_activity(self.name, "Backup")
		frappe.get_doc(
			{
				"doctype": "Site Backup",
				"site": self.name,
				"with_files": with_files,
				"offsite": offsite,
			}
		).insert()

	def schedule_update(self):
		log_site_activity(self.name, "Update")
		self.status_before_update = self.status
		self.status = "Pending"
		self.save()
		frappe.get_doc({"doctype": "Site Update", "site": self.name}).insert()

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

	def add_domain_to_config(self, domain):
		agent = Agent(self.server)
		agent.add_domain(self, domain)

	def remove_domain_from_config(self, domain):
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
				msg="Only active domains can be primary", exc=frappe.LinkValidationError,
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
			self.set_redirects_in_proxy(domains)

	def _remove_redirects_for_all_site_domains(self):
		domains = self._get_redirected_domains()
		if domains:
			self.unset_redirects_in_proxy(domains)

	def set_redirects_in_proxy(self, domains: List[str]):
		target = self.host_name
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.setup_redirects(self.name, domains, target)

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

	def archive(self):
		log_site_activity(self.name, "Archive")
		agent = Agent(self.server)
		self.status = "Pending"
		self.save()
		agent.archive_site(self)

		server = frappe.get_all(
			"Server", filters={"name": self.server}, fields=["proxy_server"], limit=1
		)[0]

		agent = Agent(server.proxy_server, server_type="Proxy Server")
		agent.remove_upstream_site(self.server, self.name)

		self.db_set("host_name", None)

		self.delete_offsite_backups()
		frappe.db.set_value(
			"Site Backup",
			{"site": self.name, "offsite": False},
			"files_availability",
			"Unavailable",
		)

	def delete_offsite_backups(self):
		from press.press.doctype.remote_file.remote_file import delete_remote_backup_objects

		log_site_activity(self.name, "Drop Offsite Backups")

		sites_remote_files = [
			remote_file
			for backup_files in frappe.get_all(
				"Site Backup",
				filters={"site": self.name, "offsite": True, "files_availability": "Available"},
				fields=["remote_database_file", "remote_public_file", "remote_private_file"],
				as_list=True,
			)
			for remote_file in backup_files
		]

		if not sites_remote_files:
			return

		frappe.db.set_value(
			"Site Backup",
			{"site": self.name, "offsite": True},
			"files_availability",
			"Unavailable",
		)

		return delete_remote_backup_objects(sites_remote_files)

	def login(self):
		log_site_activity(self.name, "Login as Administrator")
		return self.get_login_sid()

	def get_login_sid(self):
		password = get_decrypted_password("Site", self.name, "admin_password")
		response = requests.post(
			f"https://{self.name}/api/method/login",
			data={"usr": "Administrator", "pwd": password},
		)
		sid = response.cookies.get("sid")
		if sid:
			return sid
		else:
			agent = Agent(self.server)
			return agent.get_site_sid(self)

	def fetch_info(self):
		agent = Agent(self.server)
		return agent.get_site_info(self)

	def get_disk_usages(self):
		last_usage = frappe.get_last_doc("Site Usage", {"site": self.name})
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

			site_usage = frappe.get_doc({"doctype": "Site Usage", **site_usage_data}).insert()

			if usage.get("timestamp"):
				equivalent_site_time = convert_utc_to_user_timezone(
					dateutil.parser.parse(usage["timestamp"])
				)
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

		if to_save:
			self.save()

	def is_setup_wizard_complete(self):
		if self.setup_wizard_complete:
			return True

		password = get_decrypted_password("Site", self.name, "admin_password")
		conn = FrappeClient(
			f"https://{self.name}", username="Administrator", password=password
		)
		value = conn.get_value("System Settings", "setup_complete", "System Settings")
		if value:
			setup_complete = cint(value["setup_complete"])
			self.db_set("setup_wizard_complete", setup_complete)
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

	def update_site_config(self, config):
		"""Updates site.configuration, site.config and runs site.save which initiates an Agent Request
		This checks for the blacklisted config keys via Frappe Validations, but not for internal usages.
		Don't expose this directly to an external API. Pass through `press.utils.sanitize_config` or use
		`press.api.site.update_config` instead.

		Args:
		config (dict): Python dict for any suitable frappe.conf
		"""
		if isinstance(config, list):
			self._set_configuration(config)
		else:
			self._update_configuration(config)
		Agent(self.server).update_site_config(self)

	def update_site(self):
		log_site_activity(self.name, "Update")

	def create_subscription(self, plan):
		# create a site plan change log
		self._create_initial_site_plan_change(plan)

	def enable_subscription(self):
		subscription = self.subscription
		if subscription:
			subscription.enable()

	def disable_subscription(self):
		subscription = self.subscription
		if subscription:
			subscription.disable()

	def can_change_plan(self):
		team = frappe.get_doc("Team", self.team)

		if team.is_defaulter():
			frappe.throw("Cannot change plan because you have unpaid invoices")

		if not (team.default_payment_method or team.get_balance()):
			frappe.throw(
				"Cannot change plan because you haven't added a card and not have enough balance"
			)

	def change_plan(self, plan):
		self.can_change_plan()
		plan_config = get_plan_config(plan)
		self.update_site_config(plan_config)
		frappe.get_doc(
			{
				"doctype": "Site Plan Change",
				"site": self.name,
				"from_plan": self.plan,
				"to_plan": plan,
			}
		).insert()
		if self.status == "Suspended":
			self.unsuspend_if_applicable()

	def unsuspend_if_applicable(self):
		try:
			usage = frappe.get_last_doc("Site Usage", {"site": self.name})
		except frappe.DoesNotExistError:
			# If no doc is found, it means the site was created a few moments before
			# team was suspended, potentially due to failure in payment. Don't unsuspend
			# site in that case. team.unsuspend_sites should handle that, then.
			return

		disk_usage = usage.public + usage.private
		plan = frappe.get_doc("Plan", self.plan)

		if usage.database < plan.max_database_usage and disk_usage < plan.max_storage_usage:
			self.current_database_usage = (usage.database / plan.max_database_usage) * 100
			self.current_disk_usage = (
				(usage.public + usage.private) / plan.max_storage_usage
			) * 100
			self.unsuspend(reason="Plan Upgraded")

	def deactivate(self):
		log_site_activity(self.name, "Deactivate Site")
		self.status = "Inactive"
		self.update_site_config({"maintenance_mode": 1})
		self.update_site_status_on_proxy("deactivated")

	def activate(self):
		log_site_activity(self.name, "Activate Site")
		self.status = "Active"
		self.update_site_config({"maintenance_mode": 0})
		self.update_site_status_on_proxy("activated")

	def suspend(self, reason=None):
		log_site_activity(self.name, "Suspend Site", reason)
		self.status = "Suspended"
		self.update_site_config({"maintenance_mode": 1})
		self.update_site_status_on_proxy("suspended")

	def unsuspend(self, reason=None):
		log_site_activity(self.name, "Unsuspend Site", reason)
		self.status = "Active"
		self.update_site_config({"maintenance_mode": 0})
		self.update_site_status_on_proxy("activated")

	def update_site_status_on_proxy(self, status):
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.update_site_status(self.server, self.name, status)

	def create_usage_ledger_entry(self):
		doc = frappe.new_doc("Payment Ledger Entry")
		doc.site = self.name
		doc.purpose = "Site Consumption"
		doc.insert()
		frappe.db.commit()
		try:
			doc.submit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Submit Payment Ledger Entry", doc=doc.name)
			doc.reload()
			doc.increment_failed_attempt()
			doc.add_comment(text=f"<pre><code>{frappe.get_traceback()}</code></pre>")
		return doc

	@property
	def subscription(self):
		name = frappe.db.get_value(
			"Subscription", {"document_type": "Site", "document_name": self.name},
		)
		return frappe.get_doc("Subscription", name) if name else None

	@property
	def plan(self):
		return frappe.db.get_value(
			"Subscription",
			filters={"document_type": "Site", "document_name": self.name},
			fieldname="plan",
		)

	def can_charge_for_subscription(self):
		return (
			self.status == "Active"
			and self.team
			and self.team != "Administrator"
			and not self.free
		)

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

	@property
	def server_logs(self):
		return Agent(self.server).get(f"benches/{self.bench}/sites/{self.name}/logs")

	def get_server_log(self, log):
		return Agent(self.server).get(f"benches/{self.bench}/sites/{self.name}/logs/{log}")


def site_cleanup_after_archive(site):
	delete_logs(site)
	delete_site_domains(site)
	release_name(site)


def delete_logs(site):
	frappe.db.delete("Site Job Log", {"site": site})
	frappe.db.delete("Site Request Log", {"site": site})
	frappe.db.delete("Site Uptime Log", {"site": site})


def delete_site_domains(site):
	domains = frappe.get_all("Site Domain", {"site": site})
	for domain in domains:
		frappe.delete_doc("Site Domain", domain.name)


def release_name(name):
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

	if "Success" == first == second:
		updated_status = "Active"
	elif "Failure" in (first, second):
		updated_status = "Broken"
	elif "Running" in (first, second):
		updated_status = "Installing"
	else:
		updated_status = "Pending"

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		frappe.db.set_value("Site", job.site, "status", updated_status)


def process_archive_site_job_update(job):
	other_job_type = {
		"Remove Site from Upstream": "Archive Site",
		"Archive Site": "Remove Site from Upstream",
	}[job.job_type]

	first = job.status
	second = frappe.get_all(
		"Agent Job",
		fields=["status"],
		filters={"job_type": other_job_type, "site": job.site},
	)[0].status

	if "Success" == first == second:
		updated_status = "Archived"
	elif "Failure" in (first, second):
		updated_status = "Broken"
	else:
		updated_status = "Pending"

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		frappe.db.set_value("Site", job.site, "status", updated_status)
		if updated_status == "Archived":
			site_cleanup_after_archive(job.site)


def process_install_app_site_job_update(job):
	updated_status = {
		"Pending": "Active",
		"Running": "Installing",
		"Success": "Active",
		"Failure": "Broken",
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

	site_status = frappe.get_value("Site", job.site, "status")
	if updated_status != site_status:
		frappe.db.set_value("Site", job.site, "status", updated_status)


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return ""

	team = get_current_team()

	return f"(`tabSite`.`team` = {frappe.db.escape(team)})"
