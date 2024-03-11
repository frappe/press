# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.runner import Ansible
from press.utils import log_error
from frappe.model.naming import make_autoname

import json

# from tldextract import extract as sdext


class SelfHostedServer(Document):
	def autoname(self):
		series = make_autoname("SHS-.#####")
		self.name = f"{series}.{self.hybrid_domain}"

		self.hostname = series
		self.domain = self.hybrid_domain

	def validate(self):
		self.set_proxy_details()
		self.set_mariadb_config()

		if not self.agent_password:
			self.agent_password = frappe.generate_hash(length=32)

	def set_proxy_details(self):
		if self.proxy_created or self.proxy_server:
			self.proxy_public_ip, self.proxy_private_ip = frappe.db.get_value(
				"Proxy Server", self.proxy_server, ["ip", "private_ip"]
			)

	def set_mariadb_config(self):
		if not self.mariadb_ip:
			self.mariadb_ip = self.ip
		if not self.mariadb_private_ip:
			self.mariadb_private_ip = self.private_ip
		if not self.mariadb_root_user:
			self.mariadb_root_user = "root"
		if not self.mariadb_root_password:
			self.mariadb_root_password = frappe.generate_hash(length=32)

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

	def get_database_plan(self):
		if not self.different_database_server:
			try:
				frappe.get_last_doc("Server Plan", "Unlimited")
			except frappe.DoesNotExists:
				self._create_server_plan("Unlimited")

			self.database_plan = "Unlimited"

	def _create_server_plan(self, plan_name):
		plan = frappe.new_doc("Server Plan")
		plan.name = plan_name
		plan.title = plan_name
		plan.save()

	@frappe.whitelist()
	def create_db_server(self):
		try:
			if not self.mariadb_ip:
				frappe.throw("Public IP for MariaDB not found")

			db_server = frappe.new_doc(
				"Database Server",
				**{
					"hostname": self.get_hostname("Database Server"),
					"title": f"{self.title} DB",
					"is_self_hosted": True,
					"domain": self.hybrid_domain,
					"self_hosted_server_domain": self.hybrid_domain,
					"ip": self.mariadb_ip,
					"private_ip": self.mariadb_private_ip,
					"team": self.team,
					"ssh_user": self.ssh_user,
					"ssh_port": self.ssh_port,
					"mariadb_root_password": self.get_password("mariadb_root_password"),
					"cluster": self.cluster,
					"agent_password": self.get_password("agent_password"),
					"is_server_setup": False if self.new_server else True,
					"plan": self.database_plan,
				},
			).insert()

			db_server.create_subscription(self.database_plan)
			self.database_setup = True
			self.database_server = db_server.name
			self.status = "Active"
			self.save()

			if not frappe.flags.in_test:
				db_server.create_dns_record()

			frappe.msgprint(f"Databse server record {db_server.name} created")
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
			server = frappe.new_doc(
				"Server",
				**{
					"hostname": self.get_hostname("Server"),
					"title": f"{self.title} App",
					"is_self_hosted": True,
					"domain": self.hybrid_domain,
					"self_hosted_server_domain": self.hybrid_domain,
					"team": self.team,
					"ip": self.ip,
					"private_ip": self.private_ip,
					"ssh_user": self.ssh_user,
					"ssh_port": self.ssh_port,
					"proxy_server": self.proxy_server,
					"database_server": self.database_server,
					"cluster": self.cluster,
					"agent_password": self.get_password("agent_password"),
					"self_hosted_mariadb_root_password": self.get_password("mariadb_root_password"),
					"ram": self.ram,
					"new_worker_allocation": True,
					"plan": self.plan,
				},
			).insert()

			server.create_subscription(self.plan)
			self.server = server.name
			self.status = "Active"
			self.server_created = True

			if not frappe.flags.in_test:
				server.create_dns_record()

		except Exception as e:
			self.status = "Broken"
			frappe.throw("Server Creation Error", exc=e)

		self.save()

		frappe.msgprint(f"Server record {server.name} created")
		return server

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

	def get_hostname(self, server_type):
		symbolic_name = get_symbolic_name(server_type)
		series = f"{symbolic_name}-{self.cluster}.#####"

		index = make_autoname(series)[-5:]

		return f"{symbolic_name}-{index}-{self.cluster}".lower()

	@property
	def hybrid_domain(self):
		return frappe.db.get_single_value("Press Settings", "hybrid_domain")

	@frappe.whitelist()
	def create_proxy_server(self):
		"""
		Add a new record to the Proxy Server doctype
		"""
		try:
			proxy_server = frappe.new_doc(
				"Proxy Server",
				**{
					"hostname": self.get_hostname("Proxy Server"),
					"title": self.title,
					"is_self_hosted": True,
					"domain": self.hybrid_domain,
					"self_hosted_server_domain": self.hybrid_domain,
					"team": self.team,
					"ip": self.proxy_public_ip,
					"private_ip": self.proxy_private_ip,
					"is_primary": True,
					"cluster": self.cluster,
					"ssh_user": self.ssh_user,
					"ssh_port": self.ssh_port,
				},
			).insert()

			self.agent_password = proxy_server.get_password("agent_password")
			self.proxy_server = proxy_server.name
			self.status = "Active"
			self.proxy_created = True
		except Exception as e:
			self.status = "Broken"
			frappe.throw("Self Hosted Proxy Server Creation Error", exc=e)
		self.save()

		frappe.msgprint(f"Proxy server record {proxy_server.name} created")

	@frappe.whitelist()
	def create_tls_certs(self, domain):
		try:
			tls_cert = frappe.db.get_value("TLS Certificate", {"domain": f"{domain}"})

			if not tls_cert:
				tls_cert = frappe.new_doc(
					"TLS Certificate",
					**{
						"domain": domain,
						"team": self.team,
						"wildcard": False,
					},
				).insert()
				tls_cert = tls_cert.name

			return tls_cert
		except Exception:
			log_error("TLS Certificate(SelfHosted) Creation Error")

	@frappe.whitelist()
	def _setup_nginx(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_nginx_on_app", queue="long")

		if self.different_database_server:
			frappe.enqueue_doc(self.doctype, self.name, "_setup_nginx_on_db", queue="long")

	def _setup_nginx_on_app(self):
		server = frappe._dict(
			{
				"doctype": "Server",
				"name": self.server,
				"ssh_user": self.ssh_user or "root",
				"ssh_port": self.ssh_port or "22",
				"ip": self.ip,
			}
		)

		if self.setup_nginx(server):
			self.create_tls_certs(self.server)

			if not self.different_database_server:
				self.create_tls_certs(self.database_server)

			return True

		return False

	def _setup_nginx_on_db(self):
		if not self.different_database_server:
			return True

		server = frappe._dict(
			{
				"doctype": "Database Server",
				"name": self.database_server,
				"ssh_user": self.ssh_user or "root",
				"ssh_port": self.ssh_port or "22",
				"ip": self.mariadb_ip,
			}
		)

		if self.setup_nginx(server):
			self.create_tls_certs(self.database_server)
			return True

		return False

	def setup_nginx(self, server):
		try:
			ansible = Ansible(
				playbook="self_hosted_nginx.yml",
				server=server,
				user=server.ssh_user or "root",
				port=server.ssh_port or "22",
				variables={
					"domain": self.name,
					"press_domain": frappe.db.get_single_value(
						"Press Settings", "domain"
					),  # for ssl renewal
				},
			)
			play = ansible.run()
			if play.status == "Success":
				return True
		except Exception:
			log_error("Nginx setup failed for self hosted server", server=self.as_dict())
			return False

	@frappe.whitelist()
	def update_tls(self):
		from press.press.doctype.tls_certificate.tls_certificate import (
			update_server_tls_certifcate,
		)

		try:
			cert = frappe.get_last_doc(
				"TLS Certificate", {"domain": self.server, "status": "Active"}
			)
		except frappe.DoesNotExistError:
			cert = frappe.get_last_doc(
				"TLS Certificate", {"domain": self.name, "status": "Active"}
			)

		update_server_tls_certifcate(self, cert)

	def process_tls_cert_update(self):
		self.update_tls()

	def setup_server(self):
		self._setup_db_server()

		if self.different_database_server:
			self._setup_app_server()

	def _setup_db_server(self):
		db_server = frappe.get_doc("Database Server", self.database_server)
		db_server.setup_server()

	def _setup_app_server(self):
		app_server = frappe.get_doc("Server", self.server)
		app_server.setup_server()

	def create_subscription(self):
		frappe.new_doc(
			"Plan Change",
			**{
				"document_type": self.doctype,
				"document_name": self.name,
				"from_plan": "",
				"to_plan": self.plan,
				"type": "Initial Plan",
				"timestamp": self.creation,
			},
		).insert(ignore_permissions=True)

	@frappe.whitelist()
	def fetch_system_ram(self, play_id=None):
		"""
		Fetch the RAM from the Ping Ansible Play
		"""
		if not play_id:
			play_id = frappe.get_last_doc(
				"Ansible Play", {"server": self.name, "play": "Ping Server"}
			).name
		play = frappe.get_doc(
			"Ansible Task", {"status": "Success", "play": play_id, "task": "Gather Facts"}
		)
		try:
			result = json.loads(play.result)
			self.ram = result["ansible_facts"]["memtotal_mb"]
			self.save()
		except Exception:
			log_error("Fetching RAM failed", server=self.as_dict())

	@property
	def subscription(self):
		name = frappe.db.get_value(
			"Subscription", {"document_type": self.doctype, "document_name": self.name}
		)
		return frappe.get_doc("Subscription", name) if name else None

	def can_charge_for_subscription(self, subscription=None):
		return (
			self.status not in ["Archived", "Unreachable", "Pending"]
			and self.team
			and self.team != "Administrator"
		)

	@frappe.whitelist()
	def fetch_private_ip(self):
		"""
		Fetch the Private IP from the Ping Ansible Play
		"""
		play_id = frappe.get_last_doc(
			"Ansible Play", {"server": self.name, "play": "Ping Server"}
		).name
		play = frappe.get_doc(
			"Ansible Task", {"status": "Success", "play": play_id, "task": "Gather Facts"}
		)
		try:
			result = json.loads(play.result)
			self.private_ip = fetch_private_ip_based_on_vendor(result)
			self.save()
		except Exception:
			log_error("Fetching Private IP failed", server=self.as_dict())

	@frappe.whitelist()
	def fetch_system_specifications(self, play_id=None):
		"""
		Fetch the RAM from the Ping Ansible Play
		"""
		if not play_id:
			play_id = frappe.get_last_doc(
				"Ansible Play", {"server": self.name, "play": "Ping Server"}
			).name
		play = frappe.get_doc(
			"Ansible Task", {"status": "Success", "play": play_id, "task": "Gather Facts"}
		)
		try:
			result = json.loads(play.result)
			self.vendor = result["ansible_facts"]["system_vendor"]
			self.ram = result["ansible_facts"]["memtotal_mb"]
			self.vcpus = result["ansible_facts"]["processor_vcpus"]
			self.swap_total = result["ansible_facts"]["swaptotal_mb"]
			self.architecture = result["ansible_facts"]["architecture"]
			self.instance_type = result["ansible_facts"]["product_name"]
			self.processor = result["ansible_facts"]["processor"][2]
			self.distribution = result["ansible_facts"]["lsb"]["description"]
			match self.vendor:
				case "DigitalOcean":
					self.total_storage = result["ansible_facts"]["devices"]["vda"]["size"]
				case "Amazon EC2":
					self.total_storage = result["ansible_facts"]["devices"]["nvme0n1"]["size"]
				case _:
					self.total_storage = result["ansible_facts"]["devices"]["sda"]["size"]
			self.save()
		except Exception:
			log_error("Fetching System Details Failed", server=self.as_dict())

	def check_minimum_specs(self):
		"""
		Check if the server meets the minimum requirements
		ie: RAM >= 4GB,vCPUs >= 2,Storage >= 40GB
		"""

		if round(int(self.ram), -3) < 4000:  # Round to nearest thousand
			frappe.throw(
				f"Minimum RAM requirement not met, Minumum is 4GB and available is {self.ram} MB"
			)
		if int(self.vcpus) < 2:
			frappe.throw(
				f"Minimum vCPU requirement not met, Minumum is 2 Cores and available is {self.vcpus}"
			)
		if round(int(float(self.total_storage.split()[0])), -1) < 40:
			frappe.throw(
				f"Minimum Storage requirement not met, Minumum is 50GB and available is {self.total_storage}"
			)
		return True


def fetch_private_ip_based_on_vendor(play_result: dict):
	vendor = play_result["ansible_facts"]["system_vendor"]
	match vendor:
		case "DigitalOcean":
			return play_result["ansible_facts"]["all_ipv4_addresses"][1]
		case "Hetzner":
			return play_result["ansible_facts"]["all_ipv4_addresses"][2]
		case "Amazon EC2":
			return play_result["ansible_facts"]["default_ipv4"]["address"]
		case "Microsoft Corporation":
			return play_result["ansible_facts"]["all_ipv4_addresses"][0]
		case "Google":
			return play_result["ansible_facts"]["default_ipv4"]["address"]
		case _:
			return play_result["ansible_facts"]["default_ipv4"]["address"]


def get_symbolic_name(server_type):
	return {
		"Proxy Server": "hybrid-n",
		"Server": "hybrid-f",
		"Database Server": "hybrid-m",
	}.get(server_type, "hybrid-f")
