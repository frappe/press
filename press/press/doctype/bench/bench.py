# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

import json
from datetime import datetime, timedelta

import frappe

from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists, make_autoname

from press.agent import Agent
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.site.site import Site
from press.utils import log_error


class Bench(Document):
	@staticmethod
	def with_sites(name: str):
		bench = frappe.get_doc("Bench", name)
		sites = frappe.get_all("Site", filters={"bench": name}, pluck="name")
		bench.sites = [frappe.get_doc("Site", s) for s in sites]

		return bench

	@staticmethod
	def all_with_sites(fields=None, filters=None):
		benches = frappe.get_all("Bench", filters=filters, fields=fields, pluck="name")
		benches = [Bench.with_sites(b) for b in benches]

		return benches

	def autoname(self):
		server_name = frappe.db.get_value("Server", self.server, "hostname")
		candidate_name = self.candidate[7:]
		bench_name = f"bench-{candidate_name}-{server_name}"
		self.name = append_number_if_name_exists("Bench", bench_name, separator="-")

	def validate(self):
		if not self.candidate:
			candidate = frappe.get_all("Deploy Candidate", filters={"group": self.group})[0]
			self.candidate = candidate.name
		candidate = frappe.get_doc("Deploy Candidate", self.candidate)
		self.docker_image = candidate.docker_image
		self.is_single_container = candidate.is_single_container
		self.is_ssh_enabled = candidate.is_ssh_enabled

		if not self.apps:
			for release in candidate.apps:
				self.append(
					"apps",
					{
						"release": release.release,
						"source": release.source,
						"app": release.app,
						"hash": release.hash,
					},
				)

		if self.is_new():
			self.port_offset = self.get_unused_port_offset()

		db_host = frappe.db.get_value("Database Server", self.database_server, "private_ip")
		config = {
			"db_host": db_host,
			"monitor": True,
			"redis_cache": "redis://redis-cache:6379",
			"redis_queue": "redis://redis-queue:6379",
			"redis_socketio": "redis://redis-socketio:6379",
			"socketio_port": 9000,
			"webserver_port": 8000,
			"restart_supervisor_on_update": True,
		}
		if self.is_single_container:
			config.update(
				{
					"redis_cache": "redis://localhost:13000",
					"redis_queue": "redis://localhost:11000",
					"redis_socketio": "redis://localhost:12000",
				}
			)

		press_settings_common_site_config = frappe.db.get_single_value(
			"Press Settings", "bench_configuration"
		)
		if press_settings_common_site_config:
			config.update(json.loads(press_settings_common_site_config))

		release_group_common_site_config = frappe.db.get_value(
			"Release Group", self.group, "common_site_config"
		)
		if release_group_common_site_config:
			config.update(json.loads(release_group_common_site_config))

		self.config = json.dumps(config, indent=4)

		server_private_ip = frappe.db.get_value("Server", self.server, "private_ip")
		bench_config = {
			"docker_image": self.docker_image,
			"web_port": 18000 + self.port_offset,
			"socketio_port": 19000 + self.port_offset,
			"private_ip": server_private_ip,
			"ssh_port": 22000 + self.port_offset,
			"is_ssh_enabled": bool(self.is_ssh_enabled),
			"gunicorn_workers": self.gunicorn_workers,
			"background_workers": self.background_workers,
			"http_timeout": 120,
			"statsd_host": f"{server_private_ip}:9125",
		}
		if self.is_single_container:
			bench_config.update({"single_container": True})

		release_group_bench_config = frappe.db.get_value(
			"Release Group", self.group, "bench_config"
		)
		if release_group_bench_config:
			bench_config.update(json.loads(release_group_bench_config))

		self.bench_config = json.dumps(bench_config, indent=4)

	def get_unused_port_offset(self):
		benches = frappe.get_all(
			"Bench",
			fields=["port_offset"],
			filters={"server": self.server, "status": ("!=", "Archived")},
		)
		all_offsets = range(0, 100)
		used_offsets = map(lambda x: x.port_offset, benches)
		available_offsets = set(all_offsets) - set(used_offsets)
		return min(available_offsets)

	def on_update(self):
		self.update_bench_config()

	def update_bench_config(self):
		old = self.get_doc_before_save()
		if old and (old.config != self.config or old.bench_config != self.bench_config):
			agent = Agent(self.server)
			agent.update_bench_config(self)

	def after_insert(self):
		self.create_agent_request()

	def create_agent_request(self):
		agent = Agent(self.server)
		agent.new_bench(self)

	@frappe.whitelist()
	def archive(self):
		unarchived_sites = frappe.db.exists(
			"Site", {"bench": self.name, "status": ("!=", "Archived")}
		)
		if unarchived_sites:
			frappe.throw("Cannot archive bench with active sites.")
		agent = Agent(self.server)
		agent.archive_bench(self)

	@frappe.whitelist()
	def sync_info(self):
		"""Initiates a Job to update Site Usage, site.config.encryption_key and timezone details for all sites on Bench."""
		try:
			sites = frappe.get_all(
				"Site", filters={"bench": self.name, "status": ("!=", "Archived")}, pluck="name"
			)
			last_synced_time = round(
				frappe.get_all(
					"Site Usage",
					filters=[["site", "in", sites]],
					limit_page_length=1,
					order_by="creation desc",
					pluck="creation",
					ignore_ifnull=True,
				)[0].timestamp()
			)
		except IndexError:
			last_synced_time = None

		agent = Agent(self.server)
		data = agent.get_sites_info(self, since=last_synced_time)
		for site, info in data.items():
			try:
				frappe.get_doc("Site", site).sync_info(info)
				frappe.db.commit()
			except Exception:
				log_error("Site Sync Error", site=site, info=info)
				frappe.db.rollback()

	@frappe.whitelist()
	def update_all_sites(self):
		sites = frappe.get_all(
			"Site",
			{"bench": self.name, "status": ("in", ("Active", "Inactive", "Suspended"))},
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

	@property
	def work_load(self) -> float:
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

			JOIN tabPlan plan
			ON subscription.plan = plan.name

			WHERE site.bench = "{self.name}"
				AND site.status = "Active"
				"""
			)[0]
			or 0
		)

	@property
	def server_logs(self):
		return Agent(self.server).get(f"benches/{self.name}/logs")

	def get_server_log(self, log):
		return Agent(self.server).get(f"benches/{self.name}/logs/{log}")


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
				"team": "Administrator",
				"subscription_plan": plan,
			}
		)

	@classmethod
	def archive_expired(cls):
		expiry = frappe.db.get_value("Press Settings", None, "staging_expiry") or 24
		sites = frappe.get_all(
			"Site",
			{"staging": True, "created_on": ("<", datetime.now() - timedelta(hours=expiry))},
		)
		for site_name in sites:
			site = frappe.doc("Site", site_name)
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
	}[job.status]

	if updated_status != bench.status:
		frappe.db.set_value("Bench", job.bench, "status", updated_status)
		if updated_status == "Active":
			StagingSite.create_if_needed(bench)
			frappe.enqueue(
				"press.press.doctype.bench.bench.archive_obsolete_benches",
				enqueue_after_commit=True,
			)
			frappe.get_doc("Bench", job.bench).add_ssh_user()


def process_archive_bench_job_update(job):
	bench_status = frappe.get_value("Bench", job.bench, "status")

	updated_status = {
		"Pending": "Pending",
		"Running": "Pending",
		"Success": "Archived",
		"Failure": "Broken",
	}[job.status]

	if updated_status != bench_status:
		frappe.db.set_value("Bench", job.bench, "status", updated_status)
		is_ssh_proxy_setup = frappe.db.get_value("Bench", job.bench, "is_ssh_proxy_setup")
		if updated_status == "Archived" and is_ssh_proxy_setup:
			frappe.get_doc("Bench", job.bench).remove_ssh_user()


def process_add_ssh_user_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Bench", job.bench, "is_ssh_proxy_setup", True)


def process_remove_ssh_user_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Bench", job.bench, "is_ssh_proxy_setup", False)


def archive_obsolete_benches():
	benches = frappe.get_all(
		"Bench", fields=["name", "candidate"], filters={"status": "Active"}
	)
	for bench in benches:
		# If this bench is already being archived then don't do anything.
		active_archival_jobs = frappe.db.exists(
			"Agent Job",
			{
				"job_type": "Archive Bench",
				"bench": bench.name,
				"status": ("in", ("Pending", "Running", "Success")),
			},
		)
		if active_archival_jobs:
			continue

		# Don't try archiving benches with sites
		if frappe.db.count("Site", {"bench": bench.name, "status": ("!=", "Archived")}):
			continue
		# If there isn't a Deploy Candidate Difference with this bench's candidate as source
		# That means this is the most recent bench and should be skipped.
		if not frappe.db.exists("Deploy Candidate Difference", {"source": bench.candidate}):
			continue

		# This bench isn't most recent.
		# But if none of the recent versions of this bench are yet active then this bench is still useful.

		# If any of the recent versions are active then, this bench can be safely archived.
		differences = frappe.get_all(
			"Deploy Candidate Difference",
			fields=["destination"],
			filters={"source": bench.candidate},
		)
		for difference in differences:
			if frappe.db.exists(
				"Bench", {"candidate": difference.destination, "status": "Active"}
			):
				try:
					frappe.get_doc("Bench", bench.name).archive()
					return
				except Exception:
					log_error("Bench Archival Error", bench=bench.name)


def scale_workers():
	benches = frappe.get_all(
		"Bench", filters={"status": "Active", "auto_scale_workers": True}, pluck="name"
	)
	for bench_name in benches:
		bench = frappe.get_doc("Bench", bench_name)
		work_load = bench.work_load

		if work_load <= 10:
			background_workers, gunicorn_workers = 1, 2
		elif work_load <= 20:
			background_workers, gunicorn_workers = 2, 4
		elif work_load <= 30:
			background_workers, gunicorn_workers = 3, 6
		elif work_load <= 50:
			background_workers, gunicorn_workers = 4, 8
		elif work_load <= 100:
			background_workers, gunicorn_workers = 6, 12
		elif work_load <= 250:
			background_workers, gunicorn_workers = 8, 16
		elif work_load <= 500:
			background_workers, gunicorn_workers = 16, 32
		else:
			background_workers, gunicorn_workers = 24, 48

		if (bench.background_workers, bench.gunicorn_workers) != (
			background_workers,
			gunicorn_workers,
		):
			bench = frappe.get_doc("Bench", bench.name)
			bench.background_workers, bench.gunicorn_workers = (
				background_workers,
				gunicorn_workers,
			)
			bench.save()


def sync_benches():
	benches = frappe.get_all("Bench", {"status": "Active"}, pluck="name")
	for bench in benches:
		frappe.enqueue(
			"press.press.doctype.bench.bench.sync_bench",
			queue="long",
			name=bench,
			enqueue_after_commit=True,
		)
	frappe.db.commit()


def sync_bench(name):
	bench = frappe.get_doc("Bench", name)
	try:
		bench.sync_info()
		frappe.db.commit()
	except Exception:
		log_error("Bench Sync Error", bench=bench.name)
		frappe.db.rollback()


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Bench")
