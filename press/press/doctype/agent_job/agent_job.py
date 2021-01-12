# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
from datetime import datetime, timedelta
from itertools import groupby

import frappe
import pytz
import requests
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils import (
	convert_utc_to_user_timezone,
	get_url_to_form,
	pretty_date,
)
from press.agent import Agent
from press.telegram import Telegram
from press.utils import log_error


class AgentJob(Document):
	def after_insert(self):
		self.create_agent_job_steps()
		self.enqueue_http_request()

	def enqueue_http_request(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"create_http_request",
			timeout=600,
			enqueue_after_commit=True,
		)

	def create_http_request(self):
		try:
			agent = Agent(self.server, server_type=self.server_type)
			data = json.loads(self.request_data)
			files = json.loads(self.request_files)

			self.job_id = agent.request(self.request_method, self.request_path, data, files)[
				"job"
			]
			self.status = "Pending"
			self.save()
		except Exception:
			self.status = "Failure"
			self.save()
			process_job_updates(self.name)
			frappe.db.set_value(
				"Agent Job", self.name, "status", "Undelivered", for_update=False
			)

	def create_agent_job_steps(self):
		job_type = frappe.get_doc("Agent Job Type", self.job_type)
		for step in job_type.steps:
			doc = frappe.get_doc(
				{
					"doctype": "Agent Job Step",
					"agent_job": self.name,
					"status": "Pending",
					"step_name": step.step_name,
					"duration": "00:00:00",
				}
			)
			doc.insert()

	def retry(self):
		job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"status": "Undelivered",
				"job_type": self.job_type,
				"server_type": self.server_type,
				"server": self.server,
				"bench": self.bench,
				"site": self.site,
				"upstream": self.upstream,
				"host": self.host,
				"request_path": self.request_path,
				"request_data": self.request_data,
				"request_files": self.request_files,
				"request_method": self.request_method,
			}
		).insert()
		return job

	def on_trash(self):
		steps = frappe.get_all("Agent Job Step", filters={"agent_job": self.name})
		for step in steps:
			frappe.delete_doc("Agent Job Step", step.name)


def job_detail(job):
	job = frappe.get_doc("Agent Job", job)
	steps = []
	current = {}
	for index, job_step in enumerate(
		frappe.get_all(
			"Agent Job Step",
			filters={"agent_job": job.name},
			fields=["step_name", "status"],
			order_by="creation",
		)
	):
		step = {"name": job_step.step_name, "status": job_step.status, "index": index}
		if job_step.status == "Running":
			current = step
		steps.append(step)

	if job.status == "Pending":
		current = {"name": job.job_type, "status": "Waiting", "index": -1}
	elif job.status in ("Success", "Failure"):
		current = {"name": job.job_type, "status": job.status, "index": len(steps)}

	current["total"] = len(steps)

	message = {
		"id": job.name,
		"name": job.job_type,
		"server": job.server,
		"bench": job.bench,
		"site": job.site,
		"status": job.status,
		"steps": steps,
		"current": current,
	}
	return message


def publish_update(job):
	message = job_detail(job)
	job_owner = frappe.db.get_value("Agent Job", job, "owner")
	frappe.publish_realtime(event="agent_job_update", message=message, user=job_owner)


def collect_server_status():
	servers = frappe.get_all("Server", fields=["name"], filters={"status": "Active"})
	for server in servers:
		agent = Agent(server.name)
		status = agent.fetch_server_status()
		doc = {
			"doctype": "Server Status",
			"server": server.name,
			"timestamp": status["timestamp"],
			"systemd_nginx_status": status["nginx"],
			"supervisor_status": json.dumps(status["supervisor"], indent=True),
			"mariadb_process_list": json.dumps(status["mariadb"], indent=True),
			"process_list": json.dumps(status["processes"], indent=True),
			"memory_usage": json.dumps(status["stats"]["memory"], indent=True),
			"ram_used": status["stats"]["memory"]["mem"]["used"],
			"ram_total": status["stats"]["memory"]["mem"]["total"],
			"memory_used": status["stats"]["memory"]["total"]["used"],
			"memory_total": status["stats"]["memory"]["total"]["total"],
			"cpu_usage": json.dumps(status["stats"]["cpu"], indent=True),
			"cpu_utilization": status["stats"]["cpu"]["usage"]["cpu"],
			"cpu_count": status["stats"]["cpu"]["count"],
			"load_average_1": status["stats"]["cpu"]["load_average"]["1"],
			"load_average_5": status["stats"]["cpu"]["load_average"]["5"],
			"load_average_15": status["stats"]["cpu"]["load_average"]["15"],
		}
		try:
			frappe.get_doc(doc).insert()
		except Exception:
			log_error(
				"Agent Server Status Collection Exception", server=server, status=status, doc=doc
			)


def collect_site_analytics():
	benches = frappe.get_all(
		"Bench", fields=["name", "server"], filters={"status": "Active"}
	)
	for bench in benches:
		agent = Agent(bench.server)
		logs = agent.fetch_monitor_data(bench.name)
		for log in logs:
			try:
				doc = {
					"name": log["uuid"],
					"site": log["site"],
					"timestamp": log["timestamp"],
					"duration": log["duration"],
				}

				if log["transaction_type"] == "request":
					doc.update(
						{
							"doctype": "Site Request Log",
							"url": log["request"]["path"],
							"ip": log["request"]["ip"],
							"http_method": log["request"]["method"],
							"length": log["request"]["response_length"],
							"status_code": log["request"]["status_code"],
							"reset": log["request"].get("reset"),
							"counter": log["request"].get("counter"),
						}
					)
				elif log["transaction_type"] == "job":
					doc.update(
						{
							"doctype": "Site Job Log",
							"job_name": log["job"]["method"],
							"scheduled": log["job"]["scheduled"],
							"wait": log["job"]["wait"] / 1000,
							"duration": log["duration"] / 1000,
						}
					)
				frappe.get_doc(doc).db_insert()
			except frappe.exceptions.DuplicateEntryError:
				pass
			except Exception:
				log_error("Agent Analytics Collection Exception", log=log, doc=doc)


def collect_site_uptime():
	benches = frappe.get_all(
		"Bench", fields=["name", "server"], filters={"status": "Active"},
	)
	online_sites = frappe.get_all("Site", filters={"status": "Active"})
	online_sites = set(site.name for site in online_sites)
	for bench in benches:
		try:
			agent = Agent(bench.server)
			bench_status = agent.fetch_bench_status(bench.name)
			if not bench_status:
				continue
			for site, status in bench_status["sites"].items():
				if site in online_sites:
					doc = {
						"doctype": "Site Uptime Log",
						"site": site,
						"web": status["web"],
						"scheduler": status["scheduler"],
						"timestamp": bench_status["timestamp"],
					}
					frappe.get_doc(doc).db_insert()
			frappe.db.commit()
		except Exception:
			log_error("Agent Uptime Collection Exception", bench=bench, status=bench_status)


def report_site_downtime():
	# Report sites that are offline for at least last two minutes
	# Also report how long they have been offline if possible
	now = datetime.utcnow()
	offline_site_logs = frappe.get_all(
		"Site Uptime Log",
		fields=["site", "count(site) as count"],
		filters={"web": "False", "timestamp": (">", now - timedelta(minutes=2))},
		group_by="site",
		ignore_ifnull=True,
	)
	offline_sites = set(log.site for log in offline_site_logs if log.count >= 2)
	if offline_sites:
		last_online_logs = frappe.get_all(
			"Site Uptime Log",
			fields=["site", "max(timestamp) as last_online"],
			filters={"site": ("in", offline_sites), "web": True},
			group_by="site",
		)
		last_online_map = {log.site: log.last_online for log in last_online_logs}
		sites = []
		for site in offline_sites:
			last_request = frappe.get_all(
				"Site Request Log",
				fields=["status_code"],
				filters={"site": site},
				order_by="timestamp desc",
				limit=1,
			)
			if last_request and last_request[0].status_code == "429":
				continue
			try:
				if requests.get(f"https://{site}").status_code == 429:
					continue
			except Exception:
				pass

			last_online = last_online_map.get(site)
			if last_online:
				timestamp = convert_utc_to_user_timezone(last_online).replace(tzinfo=None)
				human = pretty_date(timestamp)
			else:
				timestamp = datetime.min
				human = "Forever"
			sites.append(
				{
					"site": site,
					"human": human,
					"timestamp": timestamp,
					"url": get_url_to_form("Site", site),
				}
			)

		if not sites:
			return

		template = """*CRITICAL* - {{sites | len}} Sites offline

{% for site in sites -%}
	{{ site.human }} - [{{ site.site }}]({{ site.url }})
{% endfor %}
"""
		message = frappe.render_template(
			template, {"sites": sorted(sites, key=lambda x: x["timestamp"])}
		)
		telegram = Telegram()
		telegram.send(message)


def suspend_sites():
	"""Suspend sites if they have exceeded database or disk limits"""

	if not frappe.db.get_single_value("Press Settings", "enforce_storage_limits"):
		return

	free_teams = frappe.get_all(
		"Team", filters={"free_account": True, "enabled": True}, pluck="name"
	)
	active_sites = frappe.get_all(
		"Site",
		filters={"status": "Active", "free": False, "team": ("not in", free_teams)},
		fields=["name", "team", "current_database_usage", "current_disk_usage"],
	)

	for site in active_sites:
		if site.current_database_usage > 100 or site.current_disk_usage > 100:
			frappe.get_doc("Site", site.name).suspend(reason="Site Usage Exceeds Plan limits")


def schedule_backups():
	sites = frappe.get_all(
		"Site", fields=["name", "timezone"], filters={"status": "Active"},
	)
	plans_without_offsite_backups = frappe.get_all(
		"Plan", filters={"offsite_backups": 0}, pluck="name"
	)
	sites_without_offsite_backups = set(
		frappe.get_all(
			"Subscription",
			filters={"document_type": "Site", "plan": ("in", plans_without_offsite_backups)},
			pluck="document_name",
		)
	)
	interval = frappe.db.get_single_value("Press Settings", "backup_interval") or 6
	offsite_setup = any(
		frappe.db.get_value(
			"Press Settings",
			"Press Settings",
			["aws_s3_bucket", "offsite_backups_access_key_id"],
		)
	)

	for site in sites:
		try:
			server_time = datetime.now()
			timezone = site.timezone or "Asia/Kolkata"
			site_timezone = pytz.timezone(timezone)
			site_time = server_time.astimezone(site_timezone)

			if site_time.hour % interval == 0:
				today = site_time.date()
				common_filters = {
					"creation": ("between", [today, today]),
					"site": site.name,
					"status": "Success",
				}
				offsite = (
					offsite_setup
					and site.name not in sites_without_offsite_backups
					and not frappe.get_all(
						"Site Backup",
						fields=["count(*) as total"],
						filters={**common_filters, "offsite": 1},
					)[0]["total"]
				)
				with_files = (
					not frappe.get_all(
						"Site Backup",
						fields=["count(*) as total"],
						filters={**common_filters, "with_files": 1},
					)[0]["total"]
					or offsite
				)

				frappe.get_doc("Site", site.name).backup(with_files=with_files, offsite=offsite)

		except Exception:
			log_error("Site Backup Exception", site=site)


def poll_pending_jobs():
	pending_jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "server", "server_type", "job_id", "status"],
		filters={"status": ("in", ["Pending", "Running"]), "job_id": ("!=", 0)},
		order_by="server, job_id",
	)
	for server, server_jobs in groupby(pending_jobs, lambda x: x.server):
		server_jobs = list(server_jobs)
		agent = Agent(server_jobs[0].server, server_type=server_jobs[0].server_type)
		pending_ids = [j.job_id for j in server_jobs]
		polled_jobs = agent.get_jobs_status(pending_ids)
		for polled_job in polled_jobs:
			job = find(server_jobs, lambda x: x.job_id == polled_job["id"])
			try:
				# Update Job Status
				# If it is worthy of an update
				if job.status != polled_job["status"]:
					update_job(job.name, polled_job)

				# Update Steps' Status
				update_steps(job.name, polled_job)
				publish_update(job.name)
				if polled_job["status"] in ("Success", "Failure", "Undelivered"):
					skip_pending_steps(job.name)

				process_job_updates(job.name)
				frappe.db.commit()
			except Exception:
				log_error("Agent Job Poll Exception", job=job, polled=polled_job)
				frappe.db.rollback()


def update_job(job_name, job):
	job_data = json.dumps(job["data"], indent=4, sort_keys=True)
	frappe.db.set_value(
		"Agent Job",
		job_name,
		{
			"start": job["start"],
			"end": job["end"],
			"duration": job["duration"],
			"status": job["status"],
			"data": job_data,
			"output": job["data"].get("output"),
			"traceback": job["data"].get("traceback"),
		},
		for_update=False,
	)


def update_steps(job_name, job):
	step_names = [polled_step["name"] for polled_step in job["steps"]]
	steps = frappe.db.get_all(
		"Agent Job Step",
		fields=["name", "status", "step_name"],
		filters={
			"agent_job": job_name,
			"status": ("in", ["Pending", "Running"]),
			"step_name": ("in", step_names),
		},
	)
	for polled_step in job["steps"]:
		step = find(steps, lambda x: x.step_name == polled_step["name"])
		if step and step.status != polled_step["status"]:
			update_step(step.name, polled_step)


def update_step(step_name, step):
	step_data = json.dumps(step["data"], indent=4, sort_keys=True)
	frappe.db.set_value(
		"Agent Job Step",
		step_name,
		{
			"start": step["start"],
			"end": step["end"],
			"duration": step["duration"],
			"status": step["status"],
			"data": step_data,
			"output": step["data"].get("output"),
			"traceback": step["data"].get("traceback"),
		},
		for_update=False,
	)


def skip_pending_steps(job_name):
	frappe.db.sql(
		"""UPDATE  `tabAgent Job Step` SET  status = 'Skipped'
		WHERE status = 'Pending' AND agent_job = %s""",
		job_name,
	)


def process_job_updates(job_name):
	job = frappe.get_doc("Agent Job", job_name)
	try:
		from press.press.doctype.bench.bench import (
			process_archive_bench_job_update,
			process_new_bench_job_update,
		)
		from press.press.doctype.server.server import process_new_server_job_update
		from press.press.doctype.site.site import (
			process_archive_site_job_update,
			process_install_app_site_job_update,
			process_migrate_site_job_update,
			process_new_site_job_update,
			process_reinstall_site_job_update,
		)
		from press.press.doctype.site_backup.site_backup import process_backup_site_job_update
		from press.press.doctype.site_domain.site_domain import process_new_host_job_update
		from press.press.doctype.site_update.site_update import (
			process_update_site_job_update,
			process_update_site_recover_job_update,
		)

		if job.job_type == "Add Upstream to Proxy":
			process_new_server_job_update(job)
		if job.job_type == "New Bench":
			process_new_bench_job_update(job)
		if job.job_type == "Archive Bench":
			process_archive_bench_job_update(job)
		if job.job_type == "New Site":
			process_new_site_job_update(job)
		if job.job_type == "New Site from Backup":
			process_new_site_job_update(job)
		if job.job_type == "Restore Site":
			process_reinstall_site_job_update(job)
		if job.job_type == "Reinstall Site":
			process_reinstall_site_job_update(job)
		if job.job_type == "Migrate Site":
			process_migrate_site_job_update(job)
		if job.job_type == "Install App on Site":
			process_install_app_site_job_update(job)
		if job.job_type == "Uninstall App from Site":
			process_install_app_site_job_update(job)
		if job.job_type == "Add Site to Upstream":
			process_new_site_job_update(job)
		if job.job_type == "Backup Site":
			process_backup_site_job_update(job)
		if job.job_type == "Archive Site":
			process_archive_site_job_update(job)
		if job.job_type == "Remove Site from Upstream":
			process_archive_site_job_update(job)
		if job.job_type == "Add Host to Proxy":
			process_new_host_job_update(job)
		if job.job_type == "Update Site Migrate":
			process_update_site_job_update(job)
		if job.job_type == "Update Site Pull":
			process_update_site_job_update(job)
		if job.job_type == "Recover Failed Site Migrate":
			process_update_site_recover_job_update(job)
		if job.job_type == "Recover Failed Site Pull":
			process_update_site_recover_job_update(job)
		if job.job_type == "Recover Failed Site Update":
			process_update_site_recover_job_update(job)

	except Exception as e:
		log_error("Agent Job Callback Exception", job=job.as_dict())
		raise e
