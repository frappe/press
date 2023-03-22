# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document

from press.runner import Ansible
from press.utils import log_error


class SelfHostedServer(Document):
	def autoname(self):
		self.name = f"{self.hostname}.{self.domain}"  # ?

	@frappe.whitelist()
	def fetch_apps_and_sites(self):
		frappe.enqueue_doc(self.doctype, self.name, "_get_apps", queue="long", timeout=1200)
		frappe.enqueue_doc(self.doctype, self.name, "_get_sites", queue="long", timeout=1200)

	def after_insert(self):
		if not self.mariadb_ip:
			self.mariadb_ip = self.private_ip
		if not self.mariadb_root_user:
			self.mariadb_root_user = "root"

	def _get_old_sites(self):
		"""
		Get Sites from Existing Bench in the server
		"""
		try:
			ansible = Ansible(
				playbook="get_sites.yml",
				server=self,
				user=self.ssh_user,
				variables={"bench_path": self.bench_directory},
			)
			play = ansible.run()
			if play.status == "Success":
				self.append_to_sites()
		except Exception:
			log_error("Self Hosted Sites Issue", server=self.as_dict())

	def _get_old_apps(self):
		"""
		Get Apps from Existing Bench in the server
		"""
		try:
			ansible = Ansible(
				playbook="get_apps.yml",
				server=self,
				user=self.ssh_user,
				variables={"bench_path": self.bench_directory},
			)
			play = ansible.run()
			if play.status == "Success":
				self.append_to_apps()
		except Exception:
			log_error("Self Hosted Apps Issue", server=self.as_dict())

	def map_branch_to_version(self, branch):
		versions = {
			"version-13": "Version 13",
			"version-14": "Version 14",
			"develop": "Nightly",
		}
		return versions[branch]

	def append_to_sites(self):
		"""
		Append Sites and the app used by each site from existing bench to Sites Child table
		"""
		ansible_play = frappe.get_last_doc("Ansible Play", {"server": self.name})
		ansible_task_op = frappe.get_value(
			"Ansible Task",
			{"play": ansible_play.name, "task": "Get Sites from Current Bench"},
			"output",
		)
		sites = json.loads(ansible_task_op)
		try:
			for k, v in sites.items():
				self.append("sites", {"site_name": k, "apps": ",".join(map(str, v))})
			self.append_site_configs(ansible_play.name)
		except Exception:
			log_error("Append to Sites Failed", server=self.as_dict())
		self.save()

	def append_to_apps(self):
		"""
		Append apps from existing bench to Apps Child table
		Appends app name, app version and app branch
		"""
		ansible_play = frappe.get_last_doc("Ansible Play", {"server": self.name})
		ansible_task_op = frappe.get_value(
			"Ansible Task",
			{"play": ansible_play.name, "task": "Get Versions from Current Bench"},
			"output",
		).replace("'", '"')
		task_output = json.loads(ansible_task_op)
		try:
			for app in task_output:
				self.append(
					"apps",
					{"app_name": app["app"], "version": app["version"], "branch": app["branch"]},
				)
				if app["app"] == "frappe":
					self.frappe_version = self.map_branch_to_version(app["branch"])
		except Exception:
			log_error("Appending Apps Error", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def create_new_rg(self):
		"""
		Create **a** Release Group for the apps in the Existing bench
		"""
		ansible_play = frappe.get_last_doc("Ansible Play", {"server": self.server})
		ansible_task_op = frappe.get_value(
			"Ansible Task",
			{"play": ansible_play.name, "task": "Get Apps for Release Group"},
			"output",
		).replace("'", '"')
		task_result = json.loads(ansible_task_op)
		release_group = frappe.new_doc("Release Group")
		release_group.title = f"{self.server}-bench"
		branches = []
		try:
			for app in task_result:
				branches.append(app["branch"])
				if not frappe.db.exists("App Source", {"app": app["app"], "branch": app["branch"]}):
					if not frappe.db.exists("App", {"_newname": app["app"]}):
						app_doc = frappe.get_doc(
							{
								"doctype": "App",
								"_newname": app["app"],
								"title": app["app"].title(),
								"name": app["app"],
							}
						)
						app_doc.insert()
						app_source_doc = frappe.get_doc(
							{
								"doctype": "App Source",
								"app": app["app"],
								"repository_url": app["remote"],
								"team": "Administrator",
								"branch": app["branch"],
							}
						)
						app_source_doc.append(
							"versions", {"version": self.map_branch_to_version(max(branches))}
						)
						app_source_doc.insert()
						frappe.db.commit()
						release_group.append("apps", {"app": app["app"], "source": app_source_doc.name})
				release_group.append(
					"apps",
					{
						"app": app["app"],
						"source": frappe.get_value(
							"App Source",
							{
								"app": app["app"],
								"branch": app["branch"],
							},
							"name",
						),
					},
				)
		except Exception:
			log_error("Creating RG failed", server=self.as_dict())
		release_group.team = self.team
		release_group.version = self.map_branch_to_version(max(branches))
		rg = release_group.insert()
		self.release_group = rg.name
		self.save()

	@frappe.whitelist()
	def create_db_server(self):
		try:
			server = frappe.get_doc("Server", self.name)
			db_server = frappe.new_doc("Database Server")
			db_server.hostname = server.hostname
			db_server.self_hosted_server_domain = server.self_hosted_server_domain
			db_server.is_self_hosted = True
			db_server.ip = self.ip
			db_server.private_ip = self.private_ip
			db_server.team = self.team
			db_server.ssh_user = self.ssh_user
			db_server.mariadb_root_password = self.mariadb_root_password
			db_server.cluster = server.cluster
			db_server.agent_password = server.agent_password
			db_server.is_server_setup = True
			db = db_server.insert()
			self.database_server = db.name
			self.save()
			frappe.msgprint("New DB Server Up and Running")
		except Exception:
			frappe.throw("Adding Server to Database Server Doctype failed")
			log_error("Inserting a new DB server failed")

	def append_site_configs(self, play_name):
		"""
		Append site_config.json to `sites` Child Table
		"""
		ansible_task_op = frappe.get_value(
			"Ansible Task",
			{"play": play_name, "task": "Get Site Configs from Existing Sites"},
			"output",
		).replace("'", '"')
		task_result = json.loads(
			ansible_task_op.replace('"{', "{").replace('}"', "}").replace("\\n", "")
		)
		for site in task_result:
			for _site in self.sites:
				if _site.site_name == site["site"]:
					_site.site_config = site["config"]
				self.save()

	@frappe.whitelist()
	def create_new_sites(self):
		"""
		Create new FC sites from sites in Current Bench
		"""
		try:
			for site in self.sites:
				new_site = frappe.new_doc("Site")
				if len(site.site_name) < 5:
					sdomain = site.site_name + "-new"
				else:
					sdomain = site.site_name
				new_site.subdomain = sdomain
				new_site.domain = frappe.db.get_list("Root Domain", pluck="name")[0]
				try:
					new_site.bench = frappe.get_last_doc("Bench", {"group": site.release_group})
				except Exception as e:
					frappe.throw("Site Creation Failed", exc=e)
				new_site.team = self.team
				new_site.server = self.server
				for app in site.apps.split(","):
					new_site.append("apps", {"app": app})
				config = json.loads(site.site_config)
				for key, value in config.items():
					new_site.append("configuration", {"key": key, "value": value})
				new_site.database_name = config["db_name"]
				new_site.insert()
		except Exception:
			log_error("New Site Creation Error", server=self.as_dict())
