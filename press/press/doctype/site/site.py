# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import re
import frappe
import requests
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from press.agent import Agent
from frappe.utils.password import get_decrypted_password
from press.press.doctype.site_activity.site_activity import log_site_activity
from frappe.frappeclient import FrappeClient
from frappe.utils import cint, cstr
from press.api.site import check_dns
from frappe.core.utils import find
from press.utils import log_error, get_client_blacklisted_keys
from press.press.doctype.plan.plan import get_plan_config


class Site(Document):
	def autoname(self):
		domain = frappe.db.get_single_value("Press Settings", "domain")
		self.name = f"{self.subdomain}.{domain}"

	def validate(self):
		site_regex = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$"

		if len(self.subdomain) < 5:
			frappe.throw("Subdomain too short. Use 5 or more characters")
		if len(self.subdomain) > 32:
			frappe.throw("Subdomain too long. Use 32 or less characters")
		if not re.match(site_regex, self.subdomain):
			frappe.throw(
				"Subdomain contains invalid characters. Use lowercase characters,"
				" numbers and hyphens"
			)
		if not self.admin_password:
			self.admin_password = frappe.generate_hash(length=16)

		if self.is_new() and frappe.session.user != "Administrator":
			self.can_create_site()

			if not self.plan:
				frappe.throw("Cannot create site without plan")

			config = json.loads(self.config)
			config.update(get_plan_config(self.plan))
			self.config = json.dumps(config, indent=4)

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

		# this is a little hack to remember which key is being removed from the site config
		old_keys = json.loads(self.config)
		new_keys = [x.key for x in self.configuration]
		self._keys_removed_in_last_update = json.dumps(
			[x for x in old_keys if x not in new_keys]
		)

		self.update_config_preview()

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

	def after_insert(self):
		# create a site plan change log
		self._create_initial_site_plan_change()
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
			status_map = {402: "Inactive", 503: "Suspended"}
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

	def set_host_name(self, domain):
		self.host_name = domain
		self.save()
		self.update_site_config({"host_name": f"https://{domain}"})

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

		self.delete_offsite_backups()

	def delete_offsite_backups(self):
		# self._del_obj and self._s3_response are object properties available when this method is called
		from boto3 import resource

		log_site_activity(self.name, "Drop Offsite Backups")

		self._del_obj = {}
		offsite_backups = [
			frappe.db.get_value(
				"Site Backup",
				doc["name"],
				["remote_database_file", "remote_public_file", "remote_private_file"],
			)
			for doc in frappe.get_all("Site Backup", filters={"site": self.name, "offsite": 1})
		]
		offsite_bucket = {
			"bucket": frappe.db.get_single_value("Press Settings", "aws_s3_bucket"),
			"access_key_id": frappe.db.get_single_value(
				"Press Settings", "offsite_backups_access_key_id"
			),
			"secret_access_key": get_decrypted_password(
				"Press Settings", "Press Settings", "offsite_backups_secret_access_key"
			),
		}
		s3 = resource(
			"s3",
			aws_access_key_id=offsite_bucket["access_key_id"],
			aws_secret_access_key=offsite_bucket["secret_access_key"],
			region_name="ap-south-1",
		)

		for remote_files in offsite_backups:
			for file in remote_files:
				if file:
					self._del_obj[file] = frappe.db.get_value("Remote File", file, "file_path")

		if not self._del_obj:
			return

		self._s3_response = s3.Bucket(offsite_bucket["bucket"]).delete_objects(
			Delete={"Objects": [{"Key": x} for x in self._del_obj.values()]}
		)

		for key in self._del_obj:
			frappe.db.set_value("Remote File", key, "status", "Unavailable")

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

	def sync_site_config(self):
		agent = Agent(self.server)
		agent.update_site_config(self)

	def sync_info(self):
		"""Updates Site Usage, site.config.encryption_key and timezone details for site."""
		save = False
		agent = Agent(self.server)
		data = agent.get_site_info(self)
		fetched_config = data["config"]
		fetched_usage = data["usage"]
		config = {
			key: fetched_config[key]
			for key in fetched_config
			if key not in get_client_blacklisted_keys()
		}
		new_config = json.loads(self.config)
		new_config.update(config)
		current_config = json.dumps(new_config, indent=4)

		if self.timezone != data["timezone"]:
			self.timezone = data["timezone"]
			save = True

		if self.config != current_config:
			self.update_configuration(new_config)
			save = False

		if save:
			self.save()

		frappe.get_doc(
			{
				"doctype": "Site Usage",
				"site": self.name,
				"database": fetched_usage["database"],
				"public": fetched_usage["public"],
				"private": fetched_usage["private"],
				"backups": fetched_usage["backups"],
			}
		).insert()

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

	def set_configuration(self, config):
		"""Similar to update_configuration but will replace full configuration at once
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

	def update_configuration(self, config):
		"""Updates site.configuration, runs site.save which updates site.config

		Args:
			config (dict): Python dict for any suitable frappe.conf
		"""

		def is_json(string):
			if isinstance(string, str):
				string = string.strip()
				return string.startswith("{") and string.endswith("}")
			elif isinstance(string, dict):
				return True

		def guess_type(value):
			type_dict = {int: "Number", float: "Number", bool: "Boolean", dict: "JSON"}
			value_type = type(value)

			if value_type in type_dict:
				return type_dict[value_type]
			else:
				if is_json(value):
					return "JSON"
				return "String"

		def convert(string):
			if isinstance(string, str):
				if is_json(string):
					return json.loads(string)
				else:
					return string
			if isinstance(string, dict):
				return json.dumps(string)
			return string

		keys = {x.key: i for i, x in enumerate(self.configuration)}
		for key, value in config.items():
			if key in keys:
				self.configuration[keys[key]].value = convert(value)
				self.configuration[keys[key]].type = guess_type(value)
			else:
				self.append(
					"configuration", {"key": key, "value": convert(value)}
				)
		self.save()

	def update_site_config(self, config):
		"""Updates site.configuration, site.config, runs site.save and initiates an Agent Request
		This checks for the blacklisted config keys via Frappe Validations, but not for internal usages.
		Don't expose this directly to an external API. Pass through `press.utils.sanitize_config` or use
		`press.api.site.update_config` instead.

		Args:
			config (dict): Python dict for any suitable frappe.conf
		"""
		if isinstance(config, list):
			self.set_configuration(config)
		else:
			self.update_configuration(config)
		agent = Agent(self.server)
		agent.update_site_config(self)

	def update_site(self):
		log_site_activity(self.name, "Update")

	def change_plan(self, plan):
		plan_config = get_plan_config(plan)
		self.update_site_config(plan_config)
		frappe.get_doc(
			{"doctype": "Site Plan Change", "site": self.name, "to_plan": plan}
		).insert()

	def deactivate(self):
		self.update_site_config({"maintenance_mode": 1})
		log_site_activity(self.name, "Deactivate Site")
		self.status = "Inactive"
		self.save()
		self.update_site_status_on_proxy("deactivated")

	def activate(self):
		self.update_site_config({"maintenance_mode": 0})
		log_site_activity(self.name, "Activate Site")
		self.status = "Active"
		self.save()
		self.update_site_status_on_proxy("activated")

	def suspend(self, reason=None):
		self.update_site_config({"maintenance_mode": 1})
		log_site_activity(self.name, "Suspend Site", reason)
		self.status = "Suspended"
		self.save()
		self.update_site_status_on_proxy("suspended")

	def unsuspend(self, reason=None):
		self.update_site_config({"maintenance_mode": 0})
		log_site_activity(self.name, "Unsuspend Site", reason)
		self.status = "Active"
		self.save()
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

	def _create_initial_site_plan_change(self):
		frappe.get_doc(
			{
				"doctype": "Site Plan Change",
				"site": self.name,
				"from_plan": "",
				"to_plan": self.plan,
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
		"Agent Job", fields=["status"], filters={"job_type": other_job_type, "site": job.site}
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


def sync_sites():
	benches = frappe.get_all("Bench", {"status": "Active"})
	for bench in benches:
		frappe.enqueue(
			"press.press.doctype.site.site.sync_bench_sites",
			queue="long",
			bench=bench,
			enqueue_after_commit=True,
		)
	frappe.db.commit()


def sync_bench_sites(bench):
	sites = frappe.get_all("Site", {"status": ("!=", "Archived"), "bench": bench.name})
	for site in sites:
		site_doc = frappe.get_doc("Site", site.name)
		try:
			site_doc.sync_info()
			frappe.db.commit()
		except Exception:
			log_error("Site Sync Error", site=site.name, bench=bench.name)
