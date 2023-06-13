# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from press.runner import Ansible
from press.utils import log_error

from tldextract import extract as sdext
import time


class SelfHostedServer(Document):
	def autoname(self):
		self.name = sdext(self.server_url).fqdn

	def validate(self):
		if not self.mariadb_ip:
			self.mariadb_ip = self.private_ip
		if not self.mariadb_root_user:
			self.mariadb_root_user = "root"
		if not self.mariadb_root_password:
			self.mariadb_root_password = frappe.generate_hash(length=32)
		if not self.agent_password:
			self.agent_password = frappe.generate_hash(length=32)
		if not self.hostname or not self.domain:
			extracted_url = sdext(self.server_url)
			self.hostname = extracted_url.subdomain
			self.domain = extracted_url.registered_domain

	@frappe.whitelist()
	def fetch_apps_and_sites(self):
		frappe.enqueue_doc(self.doctype, self.name, "_get_apps", queue="long", timeout=1200)
		frappe.enqueue_doc(self.doctype, self.name, "_get_sites", queue="long", timeout=1200)

	@frappe.whitelist()
	def ping_ansible(self):
		try:
			ansible = Ansible(
				playbook="ping.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
			)
			play = ansible.run()
			if play.status == "Success" and self.status == "Unreachable":
				self.status = "Pending"
				self.save()
			self.reload()
		except Exception:
			log_error("Server Ping Exception", server=self.as_dict())

	def _get_sites(self):
		"""
		Get Sites from Existing Bench in the server
		"""
		try:
			ansible = Ansible(
				playbook="get_sites.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or "22",
				variables={"bench_path": self.bench_directory},
			)
			play = ansible.run()
			if play.status == "Success":
				self.append_to_sites()
		except Exception:
			log_error("Self Hosted Sites Issue", server=self.as_dict())

	def _get_apps(self):
		"""
		Get Apps from Existing Bench in the server
		"""
		try:
			ansible = Ansible(
				playbook="get_apps.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or "22",
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
			self.save()
			self.append_site_configs(ansible_play.name)
			self.status = "Active"
		except Exception:
			self.status = "Broken"
			log_error("Append to Sites Failed", server=self.as_dict())
		self.save()

	def append_to_apps(self):
		"""
		Append apps from existing bench to `apps` child table
		Appends app name, app version and app branch
		"""
		ansible_play = frappe.get_last_doc("Ansible Play", {"server": self.name})
		ansible_task_op = frappe.get_value(
			"Ansible Task",
			{"play": ansible_play.name, "task": "Get Versions from Current Bench"},
			"output",
		).replace("'", '"')
		task_output = json.loads(ansible_task_op)
		temp_task_result = task_output  # Removing risk of mutating the same loop variable
		for i, app in enumerate(temp_task_result):  # Rearrange JSON if frappe isn't first app
			if app["app"] == "frappe" and i > 0:
				task_output[i], task_output[0] = task_output[0], task_output[i]
		try:
			for app in task_output:
				self.append(
					"apps",
					{"app_name": app["app"], "version": app["version"], "branch": app["branch"]},
				)
				if app["app"] == "frappe":
					self.frappe_version = self.map_branch_to_version(app["branch"])
			self.status = "Active"

		except Exception:
			self.status = "Broken"
			log_error("Appending Apps Error", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def create_new_rg(self):
		"""
		Create **a** Release Group for the apps in the Existing bench
		"""
		ansible_play = frappe.get_last_doc(
			"Ansible Play",
			{"server": self.server, "play": "Get Bench data from Self Hosted Server"},
		)
		ansible_task_op = frappe.get_value(
			"Ansible Task",
			{"play": ansible_play.name, "task": "Get Apps for Release Group"},
			"output",
		).replace("'", '"')
		task_result = json.loads(ansible_task_op)
		temp_task_result = task_result  # Removing risk of mutating the same loop variable
		for i, app in enumerate(temp_task_result):  # Rearrange JSON if frappe isn't first app
			if app["app"] == "frappe" and i > 0:
				task_result[i], task_result[0] = task_result[0], task_result[i]
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
						app_source_doc.append("versions", {"version": self.frappe_version})
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
				release_group.append("servers", {"server": self.server})
		except Exception:
			self.status = "Broken"
			self.save()
			log_error("Creating RG failed", server=self.as_dict())
		release_group.team = self.team
		release_group.version = self.map_branch_to_version(max(branches))
		rg = release_group.insert()
		self.release_group = rg.name
		self.status = "Active"
		self.save()

	@frappe.whitelist()
	def create_db_server(self):
		try:
			db_server = frappe.new_doc("Database Server")
			db_server.hostname = self.hostname
			db_server.title = self.title
			db_server.is_self_hosted = True
			db_server.self_hosted_server_domain = self.domain
			db_server.ip = self.ip
			db_server.private_ip = self.private_ip
			db_server.team = self.team
			db_server.ssh_user = self.ssh_user
			db_server.ssh_port = self.ssh_port
			db_server.mariadb_root_password = self.get_password("mariadb_root_password")
			db_server.cluster = self.cluster
			db_server.agent_password = self.get_password("agent_password")
			db_server.is_server_setup = False if self.new_server else True
			_db = db_server.insert()
			_db.create_subscription("Unlimited")
			self.database_setup = True
			self.database_server = _db.name
			self.status = "Active"
			self.save()
		except Exception:
			frappe.throw("Adding Server to Database Server Doctype failed")
			self.status = "Broken"
			self.save()
			log_error("Inserting a new DB server failed")

	def append_site_configs(self, play_name):
		"""
		Append site_config.json to `sites` Child Table
		"""
		try:
			ansible_task_op = frappe.get_value(
				"Ansible Task",
				{"play": play_name, "task": "Get Site Configs from Existing Sites"},
				"output",
			)
			task_result = json.loads(
				ansible_task_op.replace("'", '"')
				.replace('"{', "{")
				.replace('}"', "}")
				.replace("\\n", "")
			)
			self.status = "Pending"
			for site in task_result:
				for _site in self.sites:
					if _site.site_name == site["site"]:
						_site.site_config = str(site["config"]).replace(
							"'", '"'
						)  # JSON Breaks since dict uses only single quotes
					self.save()
			self.status = "Active"
		except Exception as e:
			self.status = "Broken"
			frappe.throw("Fetching sites configs from Existing Bench failed", exc=e)
		self.save()

	@frappe.whitelist()
	def create_server(self):
		"""
		Add a new record to the Server doctype
		"""
		try:
			server = frappe.new_doc("Server")
			server.hostname = self.hostname
			server.title = self.title
			server.is_self_hosted = True
			server.self_hosted_server_domain = self.domain
			server.self_hosted_mariadb_server = self.private_ip
			server.team = self.team
			server.ip = self.ip
			server.private_ip = self.private_ip
			server.ssh_user = self.ssh_user
			server.ssh_port = self.ssh_port
			server.proxy_server = self.proxy_server
			server.database_server = self.database_server
			server.cluster = self.cluster
			server.agent_password = self.get_password("agent_password")
			server.self_hosted_mariadb_root_password = self.get_password("mariadb_root_password")
			new_server = server.insert()
			new_server.create_subscription("Unlimited")
			self.server = new_server.name
			self.status = "Active"
			self.server_created = True
		except Exception as e:
			self.status = "Broken"
			frappe.throw("Server Creation Error", exc=e)
		self.save()

	@frappe.whitelist()
	def create_new_sites(self):
		"""
		Create new FC sites from sites in Current Bench
		"""
		try:
			for _site in self.sites:
				if len(_site.site_name) < 5:
					sdomain = _site.site_name + "-new"
				else:
					sdomain = _site.site_name
				sdomain = sdomain.replace(".", "-")
				domain = self.domain
				if not frappe.db.exists("Site", f"{sdomain}.{domain}"):
					new_site = frappe.new_doc("Site")
					new_site.subdomain = sdomain
					new_site.domain = domain
					try:
						new_site.bench = frappe.get_last_doc(
							"Bench", {"group": self.release_group, "server": self.name}
						).name
					except Exception as e:
						frappe.throw("Site Creation Failed", exc=e)
					new_site.team = self.team
					new_site.server = self.name
					for app in _site.apps.split(","):
						new_site.append("apps", {"app": app})
					config = json.loads(_site.site_config)
					for key, value in config.items():
						new_site.append("configuration", {"key": key, "value": value})
					new_site.database_name = config["db_name"]
					_new_site = new_site.insert()
					_site.site = _new_site.name
					self.save()
					self.reload()
		except Exception:
			log_error("New Site Creation Error", server=self.as_dict())

	@frappe.whitelist()
	def restore_files(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_restore_files", queue="long", timeout=2400
		)

	def _restore_files(self):
		"""
		Copy required folder of Existing Bench to new sites
		"""
		self.status = "Pending"
		self.save()
		ex_sites = []
		nw_sites = []
		benches = []
		for _site in self.sites:
			ex_sites.append(_site.site_name)
			nw_sites.append(_site.site)
			bench = frappe.db.get_value("Site", _site.site, "bench")
			benches.append(bench)
		try:
			ansible = Ansible(
				playbook="self_hosted_restore.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"bench_path": self.bench_directory,
					"ex_sites": ex_sites,
					"new_benches": benches,
					"new_sites": nw_sites,
				},
			)
			play = ansible.run()
			if play.status == "Success":
				self.status = "Active"
		except Exception:
			self.status = "Broken"
			log_error("Self Hosted Restore error", server=self.name)
		self.save()

	@frappe.whitelist()
	def create_proxy_server(self):
		"""
		Add a new record to the Proxy Server doctype
		"""
		try:
			server = frappe.new_doc("Proxy Server")
			server.hostname = self.hostname
			server.title = self.title
			server.is_self_hosted = True
			server.domain = self.domain
			server.self_hosted_server_domain = self.domain
			server.team = self.team
			server.ip = self.ip
			server.private_ip = self.private_ip
			server.ssh_user = self.ssh_user
			server.is_primary = True
			server.cluster = self.cluster
			server.ssh_port = self.ssh_port
			new_server = server.insert()
			self.agent_password = new_server.get_password("agent_password")
			self.proxy_server = new_server.name
			self.proxy_server_ip = self.private_ip
			self.status = "Active"
			self.proxy_created = True
		except Exception as e:
			self.status = "Broken"
			frappe.throw("Server Creation Error", exc=e)
		self.save()

	@frappe.whitelist()
	def create_tls_certs(self):
		try:
			tls_cert = frappe.get_doc(
				{
					"doctype": "TLS Certificate",
					"domain": self.name,
					"team": self.team,
					"wildcard": False,
				}
			).insert()
			return tls_cert.name
		except Exception:
			log_error("TLS Certificate(SelfHosted) Creation Error")

	@frappe.whitelist()
	def _setup_nginx(self):
		frappe.enqueue_doc(self.doctype, self.name, "setup_nginx", queue="long")

	@frappe.whitelist()
	def setup_nginx(self):
		try:
			ansible = Ansible(
				playbook="self_hosted_nginx.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or "22",
				variables={"domain": self.name},
			)
			play = ansible.run()
			if play.status == "Success":
				return True
		except Exception:
			log_error("TLS Cert Generation Failed", server=self.as_dict())
			return False

	def process_tls_cert_update(self):
		server = frappe.get_doc("Server", self.name)
		db_server = frappe.get_doc("Database Server", self.name)
		if not (server.is_server_setup and db_server.is_server_setup):
			db_server.setup_server()
			time.sleep(60)
			server.setup_server()
		else:
			from press.press.doctype.tls_certificate.tls_certificate import (
				update_server_tls_certifcate,
			)

			cert = frappe.get_last_doc(
				"TLS Certificate", {"domain": self.name, "status": "Active"}
			)
			update_server_tls_certifcate(server, cert)
