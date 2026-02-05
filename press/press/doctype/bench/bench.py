# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from collections import OrderedDict
from functools import cached_property
from itertools import groupby
from typing import TYPE_CHECKING, Literal

import frappe
import pytz
from frappe.exceptions import DoesNotExistError
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists, make_autoname
from frappe.utils import get_system_timezone

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.api.server import usage
from press.exceptions import ArchiveBenchError
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.bench_shell_log.bench_shell_log import (
	ExecuteResult,
	create_bench_shell_log,
)
from press.press.doctype.site.site import Site
from press.runner import Ansible
from press.utils import (
	SupervisorProcess,
	flatten,
	get_datetime,
	log_error,
	parse_supervisor_status,
)
from press.utils.jobs import has_job_timeout_exceeded
from press.utils.webhook import create_webhook_event

if TYPE_CHECKING:
	from collections.abc import Generator, Iterable

	from frappe.types import DF

	from press.press.doctype.release_group.release_group import ReleaseGroup


TRANSITORY_STATES = ["Pending", "Installing"]
FINAL_STATES = ["Active", "Broken", "Archived"]

EMPTY_BENCH_COURTESY_DAYS = 3

MAX_GUNICORN_WORKERS = 36
MIN_GUNICORN_WORKERS = 2
MAX_BACKGROUND_WORKERS = 8
MIN_BACKGROUND_WORKERS = 1

if TYPE_CHECKING:
	from collections.abc import Generator, Iterable

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_source.app_source import AppSource
	from press.press.doctype.bench_update.bench_update import BenchUpdate
	from press.press.doctype.bench_update_app.bench_update_app import BenchUpdateApp
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
	from press.press.doctype.press_settings.press_settings import PressSettings

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
		build: DF.Link | None
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
		Server = frappe.qb.DocType("Server")
		Site = frappe.qb.DocType("Site")

		site_count = (
			frappe.qb.from_(Site)
			.select(frappe.query_builder.functions.Count("*"))
			.where(Site.bench == Bench.name)
			.where(Site.status != "Archived")
		)

		benches = (
			query.select(
				Bench.is_ssh_proxy_setup,
				Bench.inplace_update_docker_image,
				site_count.as_("site_count"),
				Server.public.as_("on_public_server"),
			)
			.where(Bench.status != "Archived")
			.join(Server)
			.on(Server.name == Bench.server)
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
		bench = Bench("Bench", name)
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

	def build_redis_uri(self, port: int) -> str:
		"""Get passworded protected redis uri if configured"""
		set_redis_password = frappe.get_cached_value("Press Settings", None, "set_redis_password")

		if not set_redis_password:
			return f"redis://localhost:{port}"

		redis_password = frappe.get_cached_doc("Release Group", self.group).get_redis_password()
		return f"redis://:{redis_password}@localhost:{port}"

	def validate(self):
		if not self.candidate:
			candidate = frappe.get_all("Deploy Candidate", filters={"group": self.group})[0]
			self.candidate = candidate.name
		candidate = frappe.get_doc("Deploy Candidate", self.candidate)

		self.set_apps(candidate)

		if self.is_new():
			self.port_offset = self.get_unused_port_offset()

		config = {
			"monitor": True,
			"redis_cache": self.build_redis_uri(13000),
			"redis_queue": self.build_redis_uri(11000),
			"redis_socketio": self.build_redis_uri(13000),
			"socketio_port": 9000,
			"webserver_port": 8000,
			"restart_supervisor_on_update": True,
		}

		if self.database_server:
			db_host, db_port = frappe.db.get_value(
				"Database Server", self.database_server, ["private_ip", "db_port"]
			)
		else:
			db_host, db_port = None, 3306

		if db_host:
			config["db_host"] = db_host
			config["db_port"] = db_port

		if self.managed_database_service:
			config["rds_db"] = 1
			config["db_host"] = self.managed_database_service
			config["db_port"] = frappe.db.get_value(
				"Managed Database Service", self.managed_database_service, "port"
			)

		press_settings_common_site_config: str = frappe.db.get_single_value(
			"Press Settings", "bench_configuration"
		)
		if press_settings_common_site_config:
			config.update(json.loads(press_settings_common_site_config))

		self.update_config_with_rg_config(config)

		if not (server_private_ip := frappe.db.get_value("Server", self.server, "private_ip")):
			frappe.throw("Server must have a private IP to create Bench")

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

		self.update_bench_config_with_rq_port(bench_config)
		self.add_limits(bench_config)
		self.update_bench_config_with_rg_config(bench_config)

	def update_bench_config_with_rq_port(self, bench_config):
		if self.is_new():
			bench_config["rq_port"] = 11000 + self.port_offset
			bench_config["rq_cache_port"] = 13000 + self.port_offset
		elif old := self.get_doc_before_save():
			config = json.loads(old.bench_config)
			if config.get("rq_port"):
				bench_config["rq_port"] = config["rq_port"]
			if config.get("rq_cache_port"):
				bench_config["rq_cache_port"] = config["rq_cache_port"]

	@cached_property
	def max_possible_memory_limit(self):
		return int(frappe.db.get_value("Server", self.server, "ram")) or 0

	def add_limits(self, bench_config):
		if self.skip_memory_limits:
			bench_config.update(self.get_limits(max_possible=True))
			return

		if any([self.memory_high, self.memory_max, self.memory_swap]):
			if not all([self.memory_high, self.memory_max, self.memory_swap]):
				frappe.throw("All memory limits need to be set")

			if self.memory_swap != -1 and (self.memory_max > self.memory_swap):
				frappe.throw("Memory Swap needs to be greater than Memory Max")

			if self.memory_high > self.memory_max:
				frappe.throw("Memory Max needs to be greater than Memory High")

		bench_config.update(self.get_limits())

	@cached_property
	def max_possible_memory_high_limit(self):
		return max(self.max_possible_memory_limit - 1024, 0)  # avoid negative value

	def get_limits(self, max_possible=False) -> dict:
		if max_possible:
			return {
				"memory_high": self.max_possible_memory_high_limit,
				"memory_max": self.max_possible_memory_limit,
				"memory_swap": self.max_possible_memory_limit * 2,
				"vcpu": self.vcpu,
			}
		return {
			"memory_high": self.memory_high,
			"memory_max": self.memory_max,
			"memory_swap": self.memory_swap,
			"vcpu": self.vcpu,
		}

	@frappe.whitelist()
	def correct_bench_permissions(self):
		"""Give all permissions to frappe:frappe in (container:/home/frappe)"""
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_correct_bench_permissions",
			queue="long",
			timeout=1800,
		)

	def _correct_bench_permissions(self):
		try:
			server = frappe.get_cached_doc("Server", self.server)

			ansible = Ansible(
				playbook="correct_bench_permissions.yml",
				server=server,
				user=server._ssh_user(),
				port=server._ssh_port(),
				variables={"bench_name": self.name},
			)
			ansible.run()
		except Exception:
			log_error("Bench Permissions Correction Exception", server=self.as_dict())

	@frappe.whitelist()
	def force_update_limits(self):
		agent = Agent(self.server)
		agent.force_update_bench_limits(self.name, self.get_limits())

	def get_unused_port_offset(self):
		benches = frappe.db.sql(
			"""SELECT `port_offset` FROM `tabBench`
			WHERE `tabBench`.server = %s
			AND `tabBench`.status != 'Archived'
			FOR UPDATE;
			""",
			(self.server,),
			as_dict=True,
		)
		all_offsets = range(0, 1000)
		used_offsets = map(lambda x: x.port_offset, benches)
		available_offsets = set(all_offsets) - set(used_offsets)
		return min(available_offsets)

	def on_update(self):
		self.update_bench_config()
		if self.has_value_changed("status") and self.team != "Administrator":
			create_webhook_event("Bench Status Update", self, self.team)

	def update_bench_config(self, force=False):
		if force:
			bench_config = json.loads(self.bench_config)
			config = json.loads(self.config)
			self.update_config_with_rg_config(config)
			self.update_bench_config_with_rg_config(bench_config)
			self.save()  # triggers on_update
			return

		if (
			hasattr(self, "flags")
			and hasattr(self.flags, "avoid_triggerring_update_bench_config_job")
			and self.flags.avoid_triggerring_update_bench_config_job
		):
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

	def _mark_applied_patch_as_archived(self):
		frappe.db.set_value(
			"App Patch",
			{"bench": self.name, "status": "Applied"},
			"status",
			"Archived",
		)
		frappe.db.commit()

	@dashboard_whitelist()
	def archive(self):
		self.ready_to_archive()
		self.status = "Pending"
		self.save()  # lock 1

		self.check_unarchived_sites()

		self._mark_applied_patch_as_archived()
		agent = Agent(self.server)
		agent.archive_bench(self)

	@dashboard_whitelist()
	def take_process_snapshot(self):
		process_snapshot = frappe.get_doc(
			{"doctype": "Process Snapshot", "bench": self.name, "server": self.server}
		)
		process_snapshot.insert()
		return process_snapshot.name

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

	def sync_product_site_users(self):
		agent = Agent(self.server)
		if agent.should_skip_requests():
			return
		data = agent.get_sites_analytics(self)
		if not data:
			return

		items = list(data.items())

		# Split into chunk, so that bg job ends faster
		chunk_size = 20
		for i in range(0, len(items), chunk_size):
			frappe.enqueue_doc(
				"Bench",
				self.name,
				"_process_sync_product_site_user_data",
				enqueue_after_commit=True,
				data=items[i : i + chunk_size],
				queue="sync",
			)

	def _process_sync_product_site_user_data(self, data: list):
		for site, analytics in data:
			if not frappe.db.exists("Site", site):
				return
			if has_job_timeout_exceeded():
				return
			try:
				frappe.get_doc("Site", site).sync_users_to_product_site(analytics)
				frappe.db.commit()
			except Exception:
				log_error(
					"Site Users Sync Error",
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
				site: Site = frappe.get_doc("Site", site)
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

	def get_server_log_for_log_browser(self, log):
		return Agent(self.server).get(f"benches/{self.name}/logs_v2/{log}")

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
		if frappe.get_value("Deploy Candidate Build", self.build, "status") != "Success":
			frappe.throw(f"Deploy Candidate Build {self.build} is not Active")

		deploy_candidate_build: "DeployCandidateBuild" = frappe.get_doc("Deploy Candidate Build", self.build)
		deploy_candidate_build._create_deploy([self.server])

	def get_free_memory(self):
		return usage(self.server).get("free_memory")

	def get_memory_info(self) -> tuple[bool, float, float]:
		"""Returns a tuple: (is_info_available, free_memory_in_gb, required_memory_in_gb)"""
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		required_memory_gb = press_settings.minimum_rebuild_memory

		free_memory_bytes = self.get_free_memory()
		if not free_memory_bytes:
			return False, 0.0, required_memory_gb

		free_memory_gb = free_memory_bytes / (1024**3)
		return True, free_memory_gb, required_memory_gb

	@dashboard_whitelist()
	def rebuild(self, force: bool = False):
		is_public = frappe.get_cached_value("Server", self.server, "public")
		if is_public:
			frappe.throw("Bench rebuild is not allowed on public servers!")

		has_info, free_memory_gb, required_memory_gb = self.get_memory_info()

		if force or not has_info or free_memory_gb >= required_memory_gb:
			return Agent(self.server).rebuild_bench(self)

		frappe.throw(
			f"Insufficient memory for rebuild: {free_memory_gb:.2f} GB available, "
			f"{required_memory_gb:.2f} GB required.",
			frappe.ValidationError,
		)

		return None

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
				max_gn or MAX_GUNICORN_WORKERS,
				max(
					min_gn or MIN_GUNICORN_WORKERS,
					round(self.workload / server_workload * max_gunicorn_workers),
				),  # min 2 max 36
			)
			if self.gunicorn_threads_per_worker:
				# Allocate fewer workers if threaded workers are used
				# Roughly workers / threads_per_worker = total number of workers
				# 1. At least one worker
				# 2. Slightly more workers than required
				self.gunicorn_workers = min(
					max_gn or MAX_GUNICORN_WORKERS,
					max(
						frappe.utils.ceil(self.gunicorn_workers / self.gunicorn_threads_per_worker),
						min_gn
						or 1,  # 1 instead of MIN_GUNICORN_WORKERS because that's what we're doing right now
					),
				)
			self.background_workers = min(
				max_bg or MAX_BACKGROUND_WORKERS,
				max(
					min_bg or MIN_BACKGROUND_WORKERS, round(self.workload / server_workload * max_bg_workers)
				),  # min 1 max 8
			)
		except ZeroDivisionError:  # when total_workload is 0
			self.gunicorn_workers = MIN_GUNICORN_WORKERS
			self.background_workers = MIN_BACKGROUND_WORKERS
		if set_memory_limits:
			if self.skip_memory_limits:
				self.memory_max = self.max_possible_memory_limit
				self.memory_high = self.max_possible_memory_high_limit
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
		self.save(ignore_permissions=True)
		return self.gunicorn_workers, self.background_workers

	def docker_execute(
		self,
		cmd: str,
		subdir: str | None = None,
		save_output: bool = True,
		create_log: bool = True,
		as_root: bool = False,
	) -> ExecuteResult:
		if self.status not in ["Active", "Broken"]:
			raise Exception(f"Bench {self.name} has status {self.status}, docker_execute cannot be run")

		data = {"command": cmd, "as_root": as_root}
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

	def is_this_version_or_above(self, version: int) -> bool:
		group: ReleaseGroup = frappe.get_cached_doc("Release Group", self.group)
		return group.is_this_version_or_above(version)

	def remove_scheduler_status(self, processes: list[SupervisorProcess]) -> list[SupervisorProcess]:
		if self.is_this_version_or_above(14):
			processes = [
				p
				for p in processes
				if not (p["name"] == "frappe-bench-frappe-schedule" and p["status"] == "Exited")
			]
		return processes

	def supervisorctl_status(self):
		result = self.docker_execute("supervisorctl status")
		if result["status"] != "Success" or not result["output"]:
			# Check Bench Shell Log for traceback if present
			raise Exception("Could not fetch supervisorctl status")

		output = result["output"]
		processes = parse_supervisor_status(output)
		# remove scheduler from the list
		processes = sort_supervisor_processes(processes)
		return self.remove_scheduler_status(processes)

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
		bench: "Bench" = Bench("Bench", job.bench)
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
		bench: "Bench" = Bench("Bench", job.bench)
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

			bench_config = json.loads(self.bench_config or "{}")
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

	def check_archive_jobs(self):
		frappe.db.commit()
		if frappe.get_all(
			"Agent Job",
			{
				"job_type": "Archive Bench",
				"bench": self.name,
				"status": ("in", ("Pending", "Running", "Success")),
				"creation": (">", frappe.utils.add_to_date(None, hours=-6)),
			},
			limit=1,
			ignore_ifnull=True,
			order_by="job_type",
		):
			frappe.throw("Bench is already archived", ArchiveBenchError)

	def check_ongoing_jobs(self):
		frappe.db.commit()
		if frappe.db.exists(
			"Agent Job", {"bench": self.name, "status": ("in", ["Running", "Pending", "Undelivered"])}
		):
			frappe.throw("Cannot archive bench because of ongoing jobs.", ArchiveBenchError)

	def check_ongoing_site_updates(self):
		frappe.db.commit()
		site_updates = frappe.qb.DocType("Site Update")

		ongoing_site_updates = (
			frappe.qb.from_(site_updates)
			.select(site_updates.name)
			.where((site_updates.source_bench == self.name) | (site_updates.destination_bench == self.name))
			.where(site_updates.status.isin(["Pending", "Running", "Failure", "Recovering", "Scheduled"]))
			.limit(1)
		).run()

		if ongoing_site_updates:
			frappe.throw("Cannot archive due to ongoing site update.", ArchiveBenchError)

		fatal_site_updates = (
			frappe.qb.from_(site_updates)
			.select(site_updates.name)
			.where((site_updates.source_bench == self.name) | (site_updates.destination_bench == self.name))
			.where(
				(site_updates.status == "Fatal")
				& (site_updates.creation > frappe.utils.add_to_date(None, days=-EMPTY_BENCH_COURTESY_DAYS))
			)
			.limit(1)
		).run()

		if fatal_site_updates:
			frappe.throw("Cannot archive due to recent fatal site update.", ArchiveBenchError)

	def check_unarchived_sites(self):
		frappe.db.commit()
		if frappe.db.exists("Site", {"bench": self.name, "status": ("!=", "Archived")}):
			frappe.throw("Cannot archive bench due to unarchived sites on bench.", ArchiveBenchError)

	def check_scaled_up_server(self):
		scaled_up = frappe.db.get_value("Server", self.server, "scaled_up")
		if scaled_up:
			frappe.throw("Can not archive bench as server is currently scaled up", ArchiveBenchError)

	def check_bench_resetting(self):
		if self.resetting_bench:
			frappe.throw("Cannot archive bench due to ongoing in-place updates.", ArchiveBenchError)

	def check_last_archive(self):
		if self.last_archive_failure and get_datetime(self.last_archive_failure) > frappe.utils.add_to_date(
			None, hours=-24
		):
			frappe.throw("Cannot archive as previous archive failed in the last 24 hours.", ArchiveBenchError)

	def ready_to_archive(self):
		self.check_scaled_up_server()
		self.check_bench_resetting()
		self.check_last_archive()
		self.check_archive_jobs()
		self.check_ongoing_jobs()
		self.check_ongoing_site_updates()
		self.check_unarchived_sites()
		if get_scheduled_version_upgrades(self):
			frappe.throw("Cannot archive bench due to ongoing scheduled version upgrades", ArchiveBenchError)

		if get_unfinished_site_migrations(self):
			frappe.throw("Cannot archive bench due to pending site migrations", ArchiveBenchError)

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
	bench = Bench("Bench", job.bench)

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
	if bench.team != "Administrator":
		bench.status = updated_status  # just to ensure the status got changed in webhook payload, reload_doc is costly here
		create_webhook_event("Bench Status Update", bench, bench.team)

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

	# check if new bench is for site  version upgrade flow
	version_upgrade = frappe.db.get_value(
		"Version Upgrade",
		{"destination_group": bench.group, "deploy_private_bench": 1},
	)
	if version_upgrade:
		frappe.get_doc("Version Upgrade", version_upgrade).update_version_upgrade_on_process_job(job)

	if updated_status != "Active":
		return

	StagingSite.create_if_needed(bench)
	bench = Bench("Bench", job.bench)
	frappe.enqueue(
		"press.press.doctype.bench.bench.archive_obsolete_benches",
		enqueue_after_commit=True,
		group=bench.group,
		server=bench.server,
	)
	bench.add_ssh_user()

	if frappe.get_value("Deploy Candidate Build", bench.build, "status") != "Success":
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
	bench = Bench("Bench", job.bench)

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

	if updated_status != bench.status:
		frappe.db.set_value("Bench", job.bench, "status", updated_status)
		is_ssh_proxy_setup = frappe.db.get_value("Bench", job.bench, "is_ssh_proxy_setup")
		if updated_status == "Archived" and is_ssh_proxy_setup:
			Bench("Bench", job.bench).remove_ssh_user()

		if bench.team != "Administrator":
			bench.status = updated_status  # just to ensure the status got changed in webhook payload, reload_doc is costly here
			create_webhook_event("Bench Status Update", bench, bench.team)


def process_add_ssh_user_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Bench", job.bench, "is_ssh_proxy_setup", True, update_modified=False)


def process_remove_ssh_user_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Bench", job.bench, "is_ssh_proxy_setup", False, update_modified=False)


class BenchLike(frappe._dict):
	name: str
	server: str
	group: str


def get_scheduled_version_upgrades(bench: BenchLike | Bench):
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


def get_unfinished_site_migrations(bench: BenchLike | Bench):
	frappe.db.commit()
	return frappe.db.exists(
		"Site Migration",
		{"status": ("in", ["Scheduled", "Pending", "Running"]), "destination_bench": bench.name},
	)


def try_archive(bench: str):
	try:
		Bench("Bench", bench).archive()
		frappe.db.commit()
		return True
	except ArchiveBenchError as e:
		if frappe.flags.in_test:
			print(f"Bench Archival Error: {e}")

		frappe.db.rollback()
		return False
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


class BenchesToArchive(frappe._dict):
	name: str
	candidate: str
	creation: DF.Datetime
	public: bool
	central_bench: bool


def archive_obsolete_benches_for_server(benches: Iterable[BenchesToArchive]):
	for bench in benches:
		# If the bench is a private one and has been created more than EMPTY_BENCH_COURTESY_DAYS ago,
		# then we can attempt to archive it.
		if not (bench.public or bench.central_bench) and bench.creation < frappe.utils.add_days(
			None, -EMPTY_BENCH_COURTESY_DAYS
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
	bench = Bench("Bench", name)
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
	bench = Bench("Bench", name)
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

	# In case not all statuses have been accounted for
	for group_grouped in status_grouped.values():
		sorted_process_groups.extend(group_grouped.values())

	return flatten(sorted_process_groups)


def group_supervisor_processes(processes: list[SupervisorProcess]):
	status_grouped: OrderedDict[str | None, OrderedDict[str | None, list[SupervisorProcess]]] = OrderedDict()
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
