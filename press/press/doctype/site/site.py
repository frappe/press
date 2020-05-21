# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import re
import frappe
import requests
from frappe.model.document import Document
from press.press.doctype.agent_job.agent_job import Agent
from frappe.utils.password import get_decrypted_password
from press.press.doctype.site_activity.site_activity import log_site_activity
from frappe.frappeclient import FrappeClient
from frappe.utils import cint
from press.api.site import check_dns
from frappe.core.utils import find


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
				"Subdomain contains invalid characters. Use lowercase characters, numbers and hyphens"
			)
		if not self.admin_password:
			self.admin_password = frappe.generate_hash(length=16)

		if self.is_new() and frappe.session.user != "Administrator":
			self.can_create_site()

	def install_app(self, app):
		if not find(self.apps, lambda x: x.app == app):
			log_site_activity(self.name, "Install App")
			self.append("apps", {"app": app})
			agent = Agent(self.server)
			agent.install_app_site(self, app)
			self.status = "Pending"
			self.save()

	def can_create_site(self):
		if not self.plan:
			frappe.throw("Cannot create site without plan")

		if self.has_subscription():
			return

		# if a site is created with a plan without trial_period, throw
		trial_period = frappe.db.get_value("Plan", self.plan, ["trial_period"])
		if not trial_period:
			frappe.throw("Cannot create site without subscription")

		# if trial sites reach their limit, throw
		trial_sites_count = cint(
			frappe.db.get_single_value("Press Settings", "trial_sites_count")
		)
		if frappe.db.count("Site", {"team": self.team}) >= trial_sites_count:
			frappe.throw("Cannot create site without subscription")

	def has_subscription(self):
		return bool(frappe.db.get_value("Subscription", {"team": self.team}))

	def after_insert(self):
		# create a site plan change log
		self._create_initial_site_plan_change()
		# log activity
		log_site_activity(self.name, "Create")
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.server)
		if self.database_file and self.private_file and self.public_file:
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

	def restore(self):
		log_site_activity(self.name, "Restore")
		agent = Agent(self.server)
		agent.restore_site(self)
		self.status = "Pending"
		self.save()

	def backup(self):
		if frappe.db.count(
			"Site Backup", {"site": self.name, "status": ("in", ["Running", "Pending"])}
		):
			raise Exception("Too many pending backups")
		log_site_activity(self.name, "Backup")
		frappe.get_doc({"doctype": "Site Backup", "site": self.name}).insert()

	def schedule_update(self):
		log_site_activity(self.name, "Update")
		frappe.get_doc({"doctype": "Site Update", "site": self.name}).insert()
		self.status = "Pending"
		self.save()

	def add_domain(self, domain):
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

	def login(self):
		log_site_activity(self.name, "Login as Administrator")
		return self.get_login_sid()

	def get_login_sid(self):
		password = get_decrypted_password("Site", self.name, "admin_password")
		response = requests.post(
			f"https://{self.name}/api/method/login",
			data={"usr": "Administrator", "pwd": password},
		)
		return response.cookies.get("sid")

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

	def update_site_config(self, config):
		self.config = json.dumps(config, indent=4)
		self.save()
		log_site_activity(self.name, "Update Configuration")
		agent = Agent(self.server)
		agent.update_site_config(self)

	def update_site(self):
		log_site_activity(self.name, "Update")

	def change_plan(self, plan):
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


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return ""

	team = get_current_team()

	return f"(`tabSite`.`team` = {frappe.db.escape(team)})"
