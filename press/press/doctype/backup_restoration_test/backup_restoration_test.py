# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from press.press.audit import get_benches_in_server
from press.press.doctype.server.server import Server
from frappe.model.document import Document
from press.agent import Agent
from press.api.site import _new
from typing import List, Dict
from random import choice
import frappe

class BackupRestorationTest(Document):
	def before_insert(self):
		self.new_sitename = "brt-" + str(self.site)

	def validate(self):
		self.check_duplicate_test()
		self.check_duplicate_active_site()

	def after_insert(self):
		self.create_test_site()

	def check_duplicate_test(self):
		# check if another backup restoration is already running
		backups = frappe.get_all("Backup Restoration Test", dict(status=("in",["Running", "Started"]), site=self.site, name=self.name), pluck="name")
		if backups:
			frappe.throw(f"Backup Restoration Test for {self.site} is already running.")

	def check_duplicate_active_site(self):
		# check if any active backup restoration test site is active
		sites = frappe.get_all("Site", dict(status="Active", name=self.new_sitename), pluck="name")
		if sites:
			frappe.throw(f"Site {self.new_sitename} is already active. Please archive the site first.")

	def create_test_site(self) -> None:
		self.status = "Running"
		site_dict = prepare_site(self.site)
		server = frappe.get_value("Site", self.site, "server")
		try:
			site_job = _new(site_dict, server)
			# print(site_job)
			self.test_site = site_job.get("site")
		except:
			frappe.log_error("Site Creation Error")
			# self.status = "Failed"

def prepare_site(site: str) -> Dict:
	doc = frappe.get_doc("Site", site)
	sitename = "brt-" + doc.subdomain
	app_plans = [app.app for app in doc.apps]
	backups = frappe.get_all("Site Backup", dict(status="Success", with_files=1, site=site, files_availability="Available", offsite=1), pluck="name")
	backup = frappe.get_doc("Site Backup", backups[0])
	files = {
		"config": '', #json.dumps(doc.config), # frappe.get_site_config()
		"database": backup.remote_database_file,
		"public": backup.remote_public_file,
		"private": backup.remote_private_file
	}
	site_dict = {
		"domain": frappe.db.get_single_value("Press Settings", "domain"),
		"plan": doc.plan,
		"name": sitename,
		"group": doc.group,
		"selected_app_plans": {},
		"apps": app_plans,
		"files": files
	}

	return site_dict