# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from collections import OrderedDict
from functools import cached_property
from itertools import groupby
from typing import TYPE_CHECKING, Generator, Iterable, Literal

import frappe
import pytz
from frappe.exceptions import DoesNotExistError
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists, make_autoname
from frappe.utils import get_system_timezone

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.bench_shell_log.bench_shell_log import (
	ExecuteResult,
	create_bench_shell_log,
)
from press.press.doctype.site.site import Site
from press.utils import SupervisorProcess, flatten, log_error, parse_supervisor_status

TRANSITORY_STATES = ["Pending", "Installing"]
FINAL_STATES = ["Active", "Broken", "Archived"]

if TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_source.app_source import AppSource
	from press.press.doctype.bench_update.bench_update import BenchUpdate
	from press.press.doctype.bench_update_app.bench_update_app import BenchUpdateApp
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate

	SupervisorctlActions = Literal[
		"start",
		"stop",
		"restart",
		"clear",
		"update",
		"remove",
	]


class Bench(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.bench_app.bench_app import BenchApp
		from press.press.doctype.bench_mount.bench_mount import BenchMount
		from press.press.doctype.bench_variable.bench_variable import BenchVariable

		apps: DF.Table[BenchApp]
		auto_scale_workers: DF.Check
		background_workers: DF.Int
		bench_config: DF.Code | None
		candidate: DF.Link
		cluster: DF.Link
		config: DF.Code | None
		database_server: DF.Link | None
		docker_image: DF.Data
		environment_variables: DF.Table[BenchVariable]
		group: DF.Link
		gunicorn_threads_per_worker: DF.Int
		gunicorn_workers: DF.Int
		inplace_update_docker_image: DF.Data | None
		is_code_server_enabled: DF.Check
		is_ssh_proxy_setup: DF.Check
		last_archive_failure: DF.Datetime | None
		last_inplace_update_failed: DF.Check
		managed_database_service: DF.Link | None
		memory_high: DF.Int
		memory_max: DF.Int
		memory_swap: DF.Int
		merge_all_rq_queues: DF.Check
		merge_default_and_short_rq_queues: DF.Check
		mounts: DF.Table[BenchMount]
		port_offset: DF.Int
		resetting_bench: DF.Check
		server: DF.Link
		skip_memory_limits: DF.Check
		staging: DF.Check
		status: DF.Literal["Pending", "Installing", "Updating", "Active", "Broken", "Archived"]
		team: DF.Link
		use_rq_workerpool: DF.Check
		vcpu: DF.Int
	# end: auto-generated types

	DOCTYPE = "Bench"
	dashboard_fields = (
		"apps",
		"name",
		"group",
		"status",
		"cluster",
		"is_ssh_proxy_setup",
		"inplace_update_docker_image",
	)

	@staticmethod
	def get_list_query(query):
		Bench = frappe.qb.DocType("Bench")

		Site = frappe.qb.DocType("Site")
		site_count = (
			frappe.qb.from_(Site)
			.select(frappe.query_builder.functions.Count("*"))
			.where(Site.bench == Bench.name)
			.where(Site.status != "Archived")
		)

		benches = (
			query.select(
				Bench.is_ssh_proxy_setup, Bench.inplace_update_docker_image, site_count.as_("site_count")
			)
			.where(Bench.status != "Archived")
			.run(as_dict=1)
		)
		bench_names = [d.name for d in benches]
		benches_with_patches = frappe.get_all(
			"App Patch",
			fields=["bench"],
			filters={"bench": ["in", bench_names], "status": "Applied"},
			pluck="bench",
		)
		for bench in benches:
			bench.has_app_patch_applied = bench.name in benches_with_patches
			bench.has_updated_inplace = bool(bench.inplace_update_docker_image)
		return benches

	def get_doc(self, doc):
		user_ssh_key = frappe.db.get_all(
			"User SSH Key", {"user": frappe.session.user, "is_default": 1}, limit=1
		)
		doc.user_ssh_key = bool(user_ssh_key)
		doc.proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")

		group = frappe.db.get_value(
			"Release Group",
			self.group,
			["title", "public", "team", "central_bench"],
			as_dict=1,
		)
		doc.group_title = group.title
		doc.group_team = group.team
		doc.group_public = group.public or group.central_bench

	@staticmethod
	def with_sites(name: str):
		bench = frappe.get_doc("Bench", name)
		sites = frappe.get_all("Site", filters={"bench": name}, pluck="name")
		bench.sites = [frappe.get_doc("Site", s) for s in sites]

		return bench

	@staticmethod
	def all_with_sites(fields=None, filters=None):
		benches = frappe.get_all("Bench", filters=filters, fields=fields, pluck="name")
		return [Bench.with_sites(b) for b in benches]

	def autoname(self):
		server_name_abbreviation, server_name = frappe.db.get_value(
			"Server", self.server, ["hostname_abbreviation", "hostname"]
		)
		candidate_name = self.candidate[7:]

		self.name = self.get_bench_name(candidate_name, server_name, server_name_abbreviation)

	def get_bench_name(self, candidate_name, server_name, server_name_abbreviation):
		bench_name = f"bench-{candidate_name}-{server_name}"

		if len(bench_name) > 32:
			bench_name = f"bench-{candidate_name}-{server_name_abbreviation}"

		return append_number_if_name_exists("Bench", bench_name, separator="-")

	def update_config_with_rg_config(self, config: dict):
		release_group_common_site_config = frappe.db.get_value(
			"Release Group", self.group, "common_site_config"
		)
		if release_group_common_site_config:
			config.update(json.loads(release_group_common_site_config))

		self.config = json.dumps(config, indent=4)

	def update_bench_config_with_rg_config(self, bench_config: dict):
		release_group_bench_config = frappe.db.get_value("Release Group", self.group, "bench_config")
		if release_group_bench_config:
			bench_config.update(json.loads(release_group_bench_config))

		self.bench_config = json.dumps(bench_config, indent=4)

	def set_apps(self, candidate: "DeployCandidate"):
		if self.apps:
			return

		for release in candidate.apps:
			app_release = release.release
			app_hash = release.hash

			if release.pullable_release and release.pullable_hash:
				app_release = release.pullable_release
				app_hash = release.pullable_hash

			self.append(
				"apps",
				{
					"release": app_release,
					"source": release.source,
					"app": release.app,
					"hash": app_hash,
				},
			)

	def validate(self):
		if not self.candidate:
			candidate = frappe.get_all("Deploy Candidate", filters={"group": self.group})[0]
			self.candidate = candidate.name
		candidate = frappe.get_doc("Deploy Candidate", self.candidate)
		self.docker_image = candidate.docker_image

		self.set_apps(candidate)

		if self.is_new():
			self.port_offset = self.get_unused_port_offset()

		config = {
			"monitor": True,
			"redis_cache": "redis://localhost:13000",
			"redis_queue": "redis://localhost:11000",
			"redis_socketio": "redis://localhost:13000",
			"socketio_port": 9000,
			"webserver_port": 8000,
			"restart_supervisor_on_update": True,
		}

		db_host = frappe.db.get_value("Database Server", self.database_server, "private_ip")

		if db_host:
			config["db_host"] = db_host
			config["db_port"] = 3306

		if self.managed_database_service:
			config["rds_db"] = 1
			config["db_host"] = self.managed_database_service
			config["db_port"] = frappe.db.get_value(
				"Managed Database Service", self.managed_database_service, "port"
			)

		press_settings_common_site_config = frappe.db.get_single_value(
			"Press Settings", "bench_configuration"
		)
		if press_settings_common_site_config:
			config.update(json.loads(press_settings_common_site_config))

		self.update_config_with_rg_config(config)

		server_private_ip = frappe.db.get_value("Server", self.server, "private_ip")
		bench_config = {
			"docker_image": self.docker_image,
			"web_port": 18000 + self.port_offset,
			"socketio_port": 19000 + self.port_offset,
			"private_ip": server_private_ip,
			"ssh_port": 22000 + self.port_offset,
			"codeserver_port": 16000 + self.port_offset,
			"is_ssh_enabled": True,
			"gunicorn_workers": self.gunicorn_workers,
			"background_workers": self.background_workers,
			"http_timeout": 120,
			"statsd_host": f"{server_private_ip}:9125",
			"merge_all_rq_queues": bool(self.merge_all_rq_queues),
			"merge_default_and_short_rq_queues": bool(self.merge_default_and_short_rq_queues),
			"environment_variables": self.get_environment_variables(),
			"single_container": True,
			"gunicorn_threads_per_worker": self.gunicorn_threads_per_worker,
			"is_code_server_enabled": self.is_code_server_enabled,
			"use_rq_workerpool": self.use_rq_workerpool,
		}
		self.add_limits(bench_config)
		self.update_bench_config_with_rg_config(bench_config)

	def add_limits(self, bench_config):
		if any([self.memory_high, self.memory_max, self.memory_swap]):
			if not all([self.memory_high, self.memory_max, self.memory_swap]):
				frappe.throw("All memory limits need to be set")

			if self.memory_swap != -1 and (self.memory_max > self.memory_swap):
				frappe.throw("Memory Swap needs to be greater than Memory Max")

			if self.memory_high > self.memory_max:
				frappe.throw("Memory Max needs to be greater than Memory High")

		bench_config.update(self.get_limits())

	def get_limits(self) -> dict:
		return {
			"memory_high": self.memory_high,
			"memory_max": self.memory_max,
			"memory_swap": self.memory_swap,
			"vcpu": self.vcpu,
		}

	@frappe.whitelist()
	def force_update_limits(self):
		agent = Agent(self.server)
		agent.force_update_bench_limits(self.name, self.get_limits())

	def get_unused_port_offset(self):
		benches = frappe.get_all(
			"Bench",
			fields=["port_offset"],
			filters={"server": self.server, "status": ("!=", "Archived")},
		)
		all_offsets = range(0, 1000)
		used_offsets = map(lambda x: x.port_offset, benches)
		available_offsets = set(all_offsets) - set(used_offsets)
		return min(available_offsets)

	def on_update(self):
		self.update_bench_config()

	def update_bench_config(self, force=False):
		if force:
			bench_config = json.loads(self.bench_config)
			config = json.loads(self.config)
			self.update_config_with_rg_config(config)
			self.update_bench_config_with_rg_config(bench_config)
			self.save()
			return
		old = self.get_doc_before_save()
		if old and (old.config != self.config or old.bench_config != self.bench_config):
			agent = Agent(self.server)
			agent.update_bench_config(self)

	def after_insert(self):
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.server)
		agent.new_bench(self)

	@dashboard_whitelist()
	def archive(self):
		self.status = "Pending"
		self.save()  # lock 1
		unarchived_sites = frappe.db.get_value(
			"Site",
			{"bench": self.name, "status": ("!=", "Archived")},
			"name",
			for_update=True,  # lock 2
		)
		if unarchived_sites:
			frappe.throw("Cannot archive bench with active sites.")
		self.check_ongoing_job()
		agent = Agent(self.server)
		agent.archive_bench(self)

	def check_ongoing_job(self):
		ongoing_jobs = frappe.db.exists(
			"Agent Job", {"bench": self.name, "status": ("in", ["Running", "Pending"])}
		)
		if ongoing_jobs:
			frappe.throw("Cannot archive bench with ongoing jobs.")

	@frappe.whitelist()
	def sync_info(self):
		"""Initiates a Job to update Site Usage, site.config.encryption_key and timezone details for all sites on Bench."""
		try:
			sites = frappe.get_all(
				"Site", filters={"bench": self.name, "status": ("!=", "Archived")}, pluck="name"
			)
			last_synced_time = round(
				convert_user_timezone_to_utc(
					frappe.get_all(
						"Site Usage",
						filters=[["site", "in", sites]],
						limit_page_length=1,
						order_by="creation desc",
						pluck="creation",
						ignore_ifnull=True,
					)[0]
				).timestamp()
			)
		except IndexError:
			last_synced_time = None

		agent = Agent(self.server)
		if agent.should_skip_requests():
			return
		data = agent.get_sites_info(self, since=last_synced_time)
		if data:
			for site, info in data.items():
				if not frappe.db.exists("Site", site):
					continue
				try:
					frappe.get_doc("Site", site, for_update=True).sync_info(info)
					frappe.db.commit()
				except frappe.DoesNotExistError:
					# Ignore: Site got renamed or deleted
					pass
				except Exception:
					log_error(
						"Site Sync Error",
						site=site,
						info=info,
						reference_doctype="Bench",
						reference_name=self.name,
					)
					frappe.db.rollback()

	@frappe.whitelist()
	def sync_analytics(self):
		agent = Agent(self.server)
		if agent.should_skip_requests():
			return
		data = agent.get_sites_analytics(self)
		if not data:
			return
		for site, analytics in data.items():
			if not frappe.db.exists("Site", site):
				return
			try:
				frappe.get_doc("Site", site).sync_analytics(analytics)
				frappe.db.commit()
			except Exception:
				log_error(
					"Site Analytics Sync Error",
					site=site,
					analytics=analytics,
					reference_doctype="Bench",
					reference_name=self.name,
				)
				frappe.db.rollback()

	@dashboard_whitelist()
	def update_all_sites(self):
		sites = frappe.get_all(
			"Site",
			{
				"bench": self.name,
				"status": ("in", ("Active", "Inactive", "Suspended")),
			},
			pluck="name",
		)
		for site in sites:
			try:
				site = frappe.get_doc("Site", site)
				site.schedule_update()
				frappe.db.commit()
			except Exception:
				import traceback

				traceback.print_exc()
				frappe.db.rollback()

	@frappe.whitelist()
	def add_ssh_user(self):
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.add_ssh_user(self)

	@frappe.whitelist()
	def remove_ssh_user(self):
		proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
		agent = Agent(proxy_server, server_type="Proxy Server")
		agent.remove_ssh_user(self)

	@frappe.whitelist()
	def generate_nginx_config(self):
		agent = Agent(self.server)
		agent.update_bench_config(self)

	@cached_property
	def workload(self) -> float:
		"""
		Score representing load on the bench put on by sites.

		= sum of cpu time per day
		"""
		return (
			frappe.db.sql_list(
				# minimum plan is taken as 10
				f"""
			SELECT SUM(plan.cpu_time_per_day)
			FROM tabSite site

			JOIN tabSubscription subscription
			ON site.name = subscription.document_name

			JOIN `tabSite Plan` plan
			ON subscription.plan = plan.name

			WHERE site.bench = "{self.name}"
			AND site.status in ("Active", "Pending", "Updating")
				"""
			)[0]
			or 0
		)

	@property
	def server_logs(self):
		return Agent(self.server).get(f"benches/{self.name}/logs")

	def get_server_log(self, log):
		return Agent(self.server).get(f"benches/{self.name}/logs/{log}")

	@frappe.whitelist()
	def move_sites(self, server: str):
		try:
			destination_bench = frappe.get_last_doc(
				"Bench",
				{
					"status": "Active",
					"candidate": self.candidate,
					"server": server,
				},
			)
		except DoesNotExistError:
			frappe.throw("Bench of corresponding Deploy Candidate not found in server")
			return
		sites = frappe.get_all("Site", {"bench": self.name, "status": "Active"}, pluck="name")
		for idx, site in enumerate(sites):
			frappe.get_doc(
				{
					"doctype": "Site Migration",
					"site": site,
					"destination_bench": destination_bench.name,
					"scheduled_time": frappe.utils.add_to_date(None, minutes=5 * idx),
				}
			).insert()

	@frappe.whitelist()
	def retry_bench(self):
		if frappe.get_value("Deploy Candidate", self.candidate, "status") != "Success":
			frappe.throw(f"Deploy Candidate {self.candidate} is not Active")

		candidate = frappe.get_doc("Deploy Candidate", self.candidate)
		candidate._create_deploy([self.server])

	@dashboard_whitelist()
	def rebuild(self):
		return Agent(self.server).rebuild_bench(self)

	@dashboard_whitelist()
	def restart(self, web_only=False):
		agent = Agent(self.server)
		agent.restart_bench(self, web_only=web_only)

	def get_environment_variables(self):
		return {v.key: v.value for v in self.environment_variables}

	def allocate_workers(
		self,
		server_workload,
		max_gunicorn_workers,
		max_bg_workers,
		set_memory_limits=False,
		gunicorn_memory=150,
		bg_memory=3 * 80,
	):
		"""
		Mostly makes sense when called from Server's auto_scale_workers

		Allocates workers and memory if required
		"""
		try:
			max_gn, min_gn, max_bg, min_bg = frappe.db.get_values(
				"Release Group",
				self.group,
				(
					"max_gunicorn_workers",
					"min_gunicorn_workers",
					"max_background_workers",
					"min_background_workers",
				),
			)[0]
			self.gunicorn_workers = min(
				max_gn or 24,
				max(
					min_gn or 2, round(self.workload / server_workload * max_gunicorn_workers)
				),  # min 2 max 24
			)
			self.background_workers = min(
				max_bg or 8,
				max(min_bg or 1, round(self.workload / server_workload * max_bg_workers)),  # min 1 max 8
			)
		except ZeroDivisionError:  # when total_workload is 0
			self.gunicorn_workers = 2
			self.background_workers = 1
		if set_memory_limits:
			if self.skip_memory_limits:
				self.memory_max = frappe.db.get_value("Server", self.server, "ram")
				self.memory_high = self.memory_max - 1024
			else:
				self.memory_high = 512 + (
					self.gunicorn_workers * gunicorn_memory + self.background_workers * bg_memory
				)
				self.memory_max = self.memory_high + gunicorn_memory + bg_memory
			self.memory_swap = self.memory_max * 2
		else:
			self.memory_high = 0
			self.memory_max = 0
			self.memory_swap = 0
		self.save()
		return self.gunicorn_workers, self.background_workers

	def docker_execute(
		self,
		cmd: str,
		subdir: str | None = None,
		save_output: bool = True,
		create_log: bool = True,
	) -> ExecuteResult:
		if self.status not in ["Active", "Broken"]:
			raise Exception(f"Bench {self.name} has status {self.status}, docker_execute cannot be run")

		data = {"command": cmd}
		if subdir:
			data["subdir"] = subdir

		result: ExecuteResult = Agent(self.server).post(f"benches/{self.name}/docker_execute", data)

		if create_log:
			create_bench_shell_log(result, self.name, cmd, subdir, save_output)
		return result

	def supervisorctl(
		self,
		action: "SupervisorctlActions",
		programs: str | list[str] = "all",
	) -> None:
		"""
		If programs list is empty then all programs are selected
		For reference check: http://supervisord.org/running.html#supervisorctl-actions
		"""
		if type(programs) is str:
			programs = [programs]

		return Agent(self.server).call_supervisorctl(
			self.name,
			action,
			programs,
		)

	def supervisorctl_status(self):
		result = self.docker_execute("supervisorctl status")
		if result["status"] != "Success" or not result["output"]:
			# Check Bench Shell Log for traceback if present
			raise Exception("Could not fetch supervisorctl status")

		output = result["output"]
		processes = parse_supervisor_status(output)
		return sort_supervisor_processes(processes)

	def update_inplace(self, apps: "list[BenchUpdateApp]", sites: "list[str]") -> str:
		self.set_self_and_site_status(sites, status="Updating", site_status="Updating")
		self.save()
		job = Agent(self.server).create_agent_job(
			"Update Bench In Place",
			path=f"benches/{self.name}/update_inplace",
			bench=self.name,
			data={
				"sites": sites,
				"apps": self.get_inplace_update_apps(apps),
				"image": self.get_next_inplace_update_docker_image(),
			},
		)
		return job.name

	def get_inplace_update_apps(self, apps: "list[BenchUpdateApp]"):
		inplace_update_apps = []
		for app in apps:
			source: "AppSource" = frappe.get_doc("App Source", app.source)
			inplace_update_apps.append(
				{
					"app": app.app,
					"url": source.get_repo_url(),
					"hash": app.hash,
				}
			)
		return inplace_update_apps

	def get_next_inplace_update_docker_image(self):
		sep = "-inplace-"
		default = self.docker_image + sep + "01"
		if not self.inplace_update_docker_image:
			return default

		splits = self.inplace_update_docker_image.split(sep)
		if len(splits) != 2:
			return default

		try:
			count = int(splits[1]) + 1
		except ValueError:
			return default

		return self.docker_image + f"{sep}{count:02}"

	@staticmethod
	def process_update_inplace(job: "AgentJob"):
		bench: "Bench" = frappe.get_doc("Bench", job.bench)
		bench._process_update_inplace(job)
		bench.save()

	def _process_update_inplace(self, job: "AgentJob"):
		req_data = json.loads(job.request_data) or {}
		if job.status in ["Undelivered", "Delivery Failure"]:
			self.set_self_and_site_status(
				req_data.get("sites", []),
				status="Active",
				site_status="Active",
			)

		elif job.status in ["Pending", "Running"]:
			self.set_self_and_site_status(
				req_data.get("sites", []),
				status="Updating",
				site_status="Updating",
			)

		elif job.status == "Failure":
			self._handle_inplace_update_failure(req_data)

		elif job.status == "Success":
			self._handle_inplace_update_success(req_data, job)

		else:
			# no-op
			raise NotImplementedError("Unexpected case reached")

	def _handle_inplace_update_failure(self, req_data: dict):
		sites = req_data.get("sites", [])
		self.set_self_and_site_status(
			sites=sites,
			status="Broken",
			site_status="Broken",
		)
		self.last_inplace_update_failed = True
		self.recover_update_inplace(sites)

	def recover_update_inplace(self, sites: list[str]):
		"""Used to attempt recovery if `update_inplace` fails"""
		self.resetting_bench = True
		self.save()

		# `inplace_update_docker_image` is the last working inplace update image
		docker_image = self.inplace_update_docker_image or self.docker_image

		Agent(self.server).create_agent_job(
			"Recover Update In Place",
			path=f"benches/{self.name}/recover_update_inplace",
			bench=self.name,
			data={
				"sites": sites,
				"image": docker_image,
			},
		)

	@staticmethod
	def process_recover_update_inplace(job: "AgentJob"):
		bench: "Bench" = frappe.get_doc("Bench", job.bench)
		bench._process_recover_update_inplace(job)
		bench.save()

	def _process_recover_update_inplace(self, job: "AgentJob"):
		self.resetting_bench = job.status not in ["Running", "Pending"]
		if job.status != "Success" and job.status != "Failure":
			return

		req_data = json.loads(job.request_data) or {}
		status = "Active" if job.status == "Success" else "Broken"

		self.set_self_and_site_status(
			req_data.get("sites", []),
			status=status,
			site_status=status,
		)

	def _handle_inplace_update_success(self, req_data: dict, job: "AgentJob"):
		if job.get_step_status("Bench Restart") == "Success":
			docker_image = req_data.get("image")
			self.inplace_update_docker_image = docker_image

			bench_config = json.loads(self.bench_config)
			bench_config.update({"docker_image": docker_image})
			self.bench_config = json.dumps(bench_config, indent=4)

			self.update_apps_after_inplace_update(
				update_apps=req_data.get("apps", []),
			)

		self.set_self_and_site_status(
			req_data.get("sites", []),
			status="Active",
			site_status="Active",
		)
		self.last_inplace_update_failed = False

	def set_self_and_site_status(
		self,
		sites: list[str],
		status: str,
		site_status: str,
	):
		self.status = status
		for site in sites:
			frappe.set_value("Site", site, "status", site_status)

	def update_apps_after_inplace_update(
		self,
		update_apps: list[dict],
	):
		apps_map = {a.app: a for a in self.apps}
		for ua in update_apps:
			name = ua.get("app") or ""
			if not (bench_app := apps_map.get(name)):
				continue

			bench_app.hash = ua.get("hash")

			# Update release by creating one
			source: "AppSource" = frappe.get_doc("App Source", bench_app.source)
			if release := source.create_release(True, commit_hash=bench_app.hash):
				bench_app.release = release

	@classmethod
	def get_workloads(cls, sites: list[str]) -> Generator[tuple[str, float, str], None, None]:
		benches = frappe.get_all("Site", filters={"name": ["in", sites]}, pluck="bench", order_by="bench")
		for bench_name in benches:
			bench = cls(cls.DOCTYPE, bench_name)
			yield bench.name, bench.workload, bench.server


class StagingSite(Site):
	def __init__(self, bench: Bench):
		plan = frappe.db.get_value("Press Settings", None, "staging_plan")
		if not plan:
			frappe.throw("Staging plan not set in settings")
			log_error(title="Staging plan not set in settings")
		super().__init__(
			{
				"doctype": "Site",
				"subdomain": make_autoname("staging-.########"),
				"staging": True,
				"bench": bench.name,
				"apps": [{"app": app.app} for app in bench.apps],
				"team": frappe.db.get_value("Team", {"user": "Administrator"}, "name"),
				"subscription_plan": plan,
			}
		)

	@classmethod
	def archive_expired(cls):
		expiry = frappe.db.get_single_value("Press Settings", "staging_expiry") or 24
		sites = frappe.get_all(
			"Site",
			{"staging": True, "creation": ("<", frappe.utils.add_to_date(None, hours=-expiry))},
		)
		for site_name in sites:
			site = frappe.get_doc("Site", site_name)
			site.archive()

	@classmethod
	def create_if_needed(cls, bench: Bench):
		if not bench.staging:
			return
		try:
			cls(bench).insert()
		except Exception as e:
			log_error("Staging Site creation error", exception=e)


def archive_staging_sites():
	StagingSite.archive_expired()


def process_new_bench_job_update(job):
	bench = frappe.get_doc("Bench", job.bench)

	updated_status = {
		"Pending": "Pending",
		"Running": "Installing",
		"Success": "Active",
		"Failure": "Broken",
		"Delivery Failure": "Broken",
	}[job.status]
	if updated_status == bench.status:
		return

	frappe.db.set_value("Bench", job.bench, "status", updated_status)

	# check if new bench related to a site group deploy
	site_group_deploy = frappe.db.get_value(
		"Site Group Deploy",
		{
			"release_group": bench.group,
			"site": ("is", "not set"),
			"bench": ("is", "not set"),
		},
	)
	if site_group_deploy:
		frappe.get_doc("Site Group Deploy", site_group_deploy).update_site_group_deploy_on_process_job(job)

	if updated_status != "Active":
		return

	StagingSite.create_if_needed(bench)
	bench = frappe.get_doc("Bench", job.bench)
	frappe.enqueue(
		"press.press.doctype.bench.bench.archive_obsolete_benches",
		enqueue_after_commit=True,
		group=bench.group,
		server=bench.server,
	)
	bench.add_ssh_user()

	dc_status = frappe.get_value("Deploy Candidate", bench.candidate, "status")
	if dc_status != "Success":
		return

	bench_updates = frappe.get_all(
		"Bench Update",
		{"candidate": bench.candidate},
		pluck="name",
		limit=1,
	)
	if len(bench_updates) != 0:
		bench_update: "BenchUpdate" = frappe.get_doc(
			"Bench Update",
			bench_updates[0],
		)
		bench_update.update_sites_on_server(job.bench, bench.server)


def process_archive_bench_job_update(job):
	bench_status = frappe.get_value("Bench", job.bench, "status")

	updated_status = {
		"Pending": "Pending",
		"Running": "Pending",
		"Success": "Archived",
		"Failure": "Broken",
		"Delivery Failure": "Active",
	}[job.status]

	if job.status == "Failure":
		if job.traceback and "Bench has sites" in job.traceback:  # custom exception hardcoded in agent
			updated_status = "Active"
		frappe.db.set_value("Bench", job.bench, "last_archive_failure", frappe.utils.now_datetime())

	if updated_status != bench_status:
		frappe.db.set_value("Bench", job.bench, "status", updated_status)
		is_ssh_proxy_setup = frappe.db.get_value("Bench", job.bench, "is_ssh_proxy_setup")
		if updated_status == "Archived" and is_ssh_proxy_setup:
			frappe.get_doc("Bench", job.bench).remove_ssh_user()


def process_add_ssh_user_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Bench", job.bench, "is_ssh_proxy_setup", True, update_modified=False)


def process_remove_ssh_user_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Bench", job.bench, "is_ssh_proxy_setup", False, update_modified=False)


def get_archive_jobs(bench: str):
	frappe.db.commit()
	return frappe.get_all(
		"Agent Job",
		{
			"job_type": "Archive Bench",
			"bench": bench,
			"status": ("in", ("Pending", "Running", "Success")),
			"creation": (">", frappe.utils.add_to_date(None, hours=-6)),
		},
		limit=1,
		ignore_ifnull=True,
		order_by="job_type",
	)


def get_ongoing_jobs(bench: str):
	frappe.db.commit()
	return frappe.db.exists("Agent Job", {"bench": bench, "status": ("in", ["Running", "Pending"])})


def get_active_site_updates(bench: str):
	frappe.db.commit()
	return frappe.get_all(
		"Site Update",
		{
			"status": ("in", ["Pending", "Running", "Failure", "Scheduled"]),
		},
		or_filters={
			"source_bench": bench,
			"destination_bench": bench,
		},
		limit=1,
		ignore_ifnull=True,
		order_by="destination_bench",
	)


def get_unfinished_site_migrations(bench: str):
	frappe.db.commit()
	return frappe.db.exists(
		"Site Migration",
		{"status": ("in", ["Scheduled", "Pending", "Running"]), "destination_bench": bench},
	)


def get_unarchived_sites(bench: str):
	frappe.db.commit()
	return frappe.db.exists("Site", {"bench": bench, "status": ("!=", "Archived")})


def get_scheduled_version_upgrades(bench: dict):
	frappe.db.commit()
	sites = frappe.qb.DocType("Site")
	version_upgrades = frappe.qb.DocType("Version Upgrade")
	return (
		frappe.qb.from_(sites)
		.join(version_upgrades)
		.on(sites.name == version_upgrades.site)
		.select("name")
		.where(sites.server == bench.server)
		.where(version_upgrades.destination_group == bench.group)
		.where(version_upgrades.status.isin(["Scheduled", "Pending", "Running"]))
		.run()
	)


def try_archive(bench: str):
	try:
		frappe.get_doc("Bench", bench).archive()
		frappe.db.commit()
		return True
	except Exception:
		log_error(
			"Bench Archival Error",
			bench=bench,
			reference_doctype="Bench",
			reference_name=bench,
		)
		frappe.db.rollback()
		return False


def archive_obsolete_benches(group: str | None = None, server: str | None = None):
	query_substr = ""
	if group and server:
		query_substr = f"AND bench.group = '{group}' AND bench.server = '{server}'"
	benches = frappe.db.sql(
		f"""
		SELECT
			bench.name, bench.server, bench.group, bench.candidate, bench.creation, bench.last_archive_failure, bench.resetting_bench, g.public, g.central_bench
		FROM
			tabBench bench
		LEFT JOIN
			`tabRelease Group` g
		ON
			bench.group = g.name
		WHERE
			bench.status = "Active" {query_substr}
		ORDER BY
			bench.server
	""",
		as_dict=True,
	)
	benches_by_server = groupby(benches, lambda x: x.server)
	for server_benches in benches_by_server:
		frappe.enqueue(
			"press.press.doctype.bench.bench.archive_obsolete_benches_for_server",
			queue="long",
			job_id=f"archive_obsolete_benches:{server_benches[0]}",
			deduplicate=True,
			benches=list(server_benches[1]),
		)


def archive_obsolete_benches_for_server(benches: Iterable[dict]):
	for bench in benches:
		# Bench is Broken but a reset to a working state is being attempted
		if (
			bench.resetting_bench
			or bench.last_archive_failure
			and bench.last_archive_failure > frappe.utils.add_to_date(None, hours=-24)
			or get_archive_jobs(bench.name)  # already being archived
			or get_ongoing_jobs(bench.name)
			or get_active_site_updates(bench.name)
			or get_unfinished_site_migrations(bench.name)
			or get_unarchived_sites(bench.name)
		):
			continue

		if (
			not (bench.public or bench.central_bench)
			and bench.creation < frappe.utils.add_days(None, -3)
			and not get_scheduled_version_upgrades(bench)
		):
			try_archive(bench.name)
			continue

		# If there isn't a Deploy Candidate Difference with this bench's candidate as source
		# That means this is the most recent bench and should be skipped.

		differences = frappe.db.get_all(
			"Deploy Candidate Difference", ["destination"], {"source": bench.candidate}
		)
		if not differences:
			continue

		# This bench isn't most recent.
		# But if none of the recent versions of this bench are yet active then this bench is still useful.

		# If any of the recent versions are active then, this bench can be safely archived.
		for difference in differences:
			if frappe.db.exists(
				"Bench", {"candidate": difference.destination, "status": "Active"}
			) and try_archive(bench.name):
				break


def sync_benches():
	benches = frappe.get_all("Bench", {"status": "Active"}, pluck="name")
	for bench in benches:
		frappe.enqueue(
			"press.press.doctype.bench.bench.sync_bench",
			queue="sync",
			name=bench,
			job_id=f"sync_bench:{bench}",
			deduplicate=True,
			enqueue_after_commit=True,
		)
	frappe.db.commit()


def sync_bench(name):
	bench = frappe.get_doc("Bench", name)
	try:
		active_archival_jobs = frappe.get_all(
			"Agent Job",
			{
				"job_type": "Archive Bench",
				"bench": bench.name,
				"status": ("in", ("Pending", "Running", "Success")),
			},
			limit=1,
			ignore_ifnull=True,
			order_by="job_type",
		)
		if active_archival_jobs:
			return
		bench.sync_info()
		frappe.db.commit()
	except Exception:
		log_error(
			"Bench Sync Error",
			bench=bench.name,
			reference_doctype="Bench",
			reference_name=bench.name,
		)
		frappe.db.rollback()


def sync_analytics():
	benches = frappe.get_all("Bench", {"status": "Active"}, pluck="name")
	for bench in benches:
		frappe.enqueue(
			"press.press.doctype.bench.bench.sync_bench_analytics",
			queue="sync",
			name=bench,
			job_id=f"sync_bench_analytics:{bench}",
			deduplicate=True,
			enqueue_after_commit=True,
		)
	frappe.db.commit()


def sync_bench_analytics(name):
	bench = frappe.get_doc("Bench", name)
	# Skip syncing analytics for benches that have been archived (after the job was enqueued)
	if bench.status != "Active":
		return
	try:
		bench.sync_analytics()
		frappe.db.commit()
	except Exception:
		log_error(
			"Bench Analytics Sync Error",
			bench=bench.name,
			reference_doctype="Bench",
			reference_name=bench.name,
		)
		frappe.db.rollback()


def convert_user_timezone_to_utc(datetime):
	timezone = pytz.timezone(get_system_timezone())
	return timezone.localize(datetime).astimezone(pytz.utc)


def sort_supervisor_processes(processes: "list[SupervisorProcess]"):
	"""
	Sorts supervisor processes according to `status_order` and groups them
	by process group.
	"""

	status_order = [
		"Starting",
		"Backoff",
		"Running",
		"Stopping",
		"Stopped",
		"Exited",
		"Fatal",
		"Unknown",
	]
	status_grouped = group_supervisor_processes(processes)
	sorted_process_groups: "list[list[SupervisorProcess]]" = []
	for status in status_order:
		if not (group_grouped := status_grouped.get(status)):
			continue

		sorted_process_groups.extend(group_grouped.values())
		del status_grouped[status]

	# Incase not all statuses have been accounted for
	for group_grouped in status_grouped.values():
		sorted_process_groups.extend(group_grouped.values())

	return flatten(sorted_process_groups)


def group_supervisor_processes(processes: "list[SupervisorProcess]"):
	status_grouped: "OrderedDict[str, OrderedDict[str, list[SupervisorProcess]]]" = OrderedDict()
	for p in processes:
		status = p.get("status")
		group = p.get("group", "NONE")

		if status not in status_grouped:
			status_grouped[status] = OrderedDict()

		group_grouped = status_grouped[status]
		if group not in group_grouped:
			group_grouped[group] = []

		group_grouped[group].append(p)
	return status_grouped


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Bench")
