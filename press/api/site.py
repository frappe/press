# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import dns.resolver

import builtins
import gzip
import io
import json
from pathlib import Path
import tarfile
import wrapt
import frappe
from press.agent import Agent
from press.press.doctype.agent_job.agent_job import job_detail
from press.press.doctype.site_update.site_update import (
	is_update_available_for_site,
	sites_with_available_update,
)
from press.utils import log_error, get_current_team
from frappe.utils import cint, flt, time_diff_in_hours


def protected():
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		site = kwargs.get("name") or args[0]
		team = get_current_team()
		owner = frappe.db.get_value("Site", site, "team")
		if frappe.session.data.user_type == "System User" or owner == team:
			return wrapped(*args, **kwargs)
		else:
			raise frappe.PermissionError

	return wrapper


@frappe.whitelist()
def new(site):
	team = get_current_team()
	bench = frappe.get_all(
		"Bench",
		fields=["name", "server"],
		filters={"status": "Active", "group": site["group"]},
		order_by="creation desc",
		limit=1,
	)[0].name
	site = frappe.get_doc(
		{
			"doctype": "Site",
			"subdomain": site["name"],
			"bench": bench,
			"apps": [{"app": app} for app in site["apps"]],
			"team": team,
			"plan": site["plan"],
			"database_file": site["files"]["database"],
			"public_file": site["files"]["public"],
			"private_file": site["files"]["private"],
		},
	).insert(ignore_permissions=True)
	return site.name


@frappe.whitelist()
@protected()
def jobs(name):
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters={"site": name},
		limit=10,
	)
	return jobs


@frappe.whitelist()
@protected()
def job(name, job):
	job = frappe.get_doc("Agent Job", job)
	job = job.as_dict()
	job.steps = frappe.get_all(
		"Agent Job Step",
		filters={"agent_job": job.name},
		fields=["step_name", "status", "start", "end", "duration", "output"],
		order_by="creation",
	)
	return job


@frappe.whitelist()
@protected()
def running_jobs(name):
	jobs = frappe.get_all(
		"Agent Job", filters={"status": ("in", ("Pending", "Running")), "site": name}
	)
	return [job_detail(job.name) for job in jobs]


@frappe.whitelist()
@protected()
def backups(name):
	backups = frappe.get_all(
		"Site Backup",
		fields=[
			"name",
			"with_files",
			"database_file",
			"database_size",
			"database_url",
			"private_file",
			"private_size",
			"private_url",
			"public_file",
			"public_size",
			"public_url",
			"creation",
			"status",
		],
		filters={"site": name, "status": ("!=", "Failure")},
		limit=5,
	)
	return backups


@frappe.whitelist()
@protected()
def domains(name):
	domains = frappe.get_all(
		"Site Domain",
		fields=["name", "domain", "status", "retry_count"],
		filters={"site": name},
	)
	return domains


@frappe.whitelist()
@protected()
def activities(name):
	activities = frappe.get_all(
		"Site Activity",
		fields=["action", "reason", "creation", "owner"],
		filters={"site": name},
		limit=20,
	)

	for activity in activities:
		if activity.action == "Create":
			activity.action = "Site created"

	return activities


@frappe.whitelist()
def options_for_new():
	groups = frappe.get_all(
		"Release Group", fields=["name", "`default`"], filters={"public": True}
	)
	for group in groups:
		group_doc = frappe.get_doc("Release Group", group.name)
		group_apps = frappe.get_all(
			"Frappe App",
			fields=["name", "frappe", "branch", "scrubbed", "url"],
			filters={"name": ("in", [row.app for row in group_doc.apps])},
		)
		order = {row.app: row.idx for row in group_doc.apps}
		group["apps"] = sorted(group_apps, key=lambda x: order[x.name])

	domain = frappe.db.get_value("Press Settings", "Press Settings", ["domain"])
	team = get_current_team()

	team_doc = frappe.get_doc("Team", team)
	# disable site creation if card not added
	disable_site_creation = not team_doc.default_payment_method and not team_doc.erpnext_partner
	allow_partner = team_doc.is_partner_and_has_enough_credits()

	return {
		"domain": domain,
		"groups": sorted(groups, key=lambda x: not x.default),
		"plans": get_plans(),
		"has_card": team_doc.default_payment_method,
		"free_account": team_doc.free_account,
		"allow_partner": allow_partner,
		"disable_site_creation": disable_site_creation,
	}


@frappe.whitelist()
def get_plans():
	return frappe.db.get_all(
		"Plan",
		fields=[
			"name",
			"plan_title",
			"price_usd",
			"price_inr",
			"concurrent_users",
			"cpu_time_per_day",
			"trial_period",
		],
		filters={"enabled": True},
		order_by="price_usd asc",
	)


@frappe.whitelist()
def all():
	if frappe.session.data.user_type == "System User":
		filters = {}
	else:
		filters = {"team": get_current_team()}
	filters.update({"status": ("!=", "Archived")})
	sites = frappe.get_list(
		"Site",
		fields=["name", "status", "modified"],
		filters=filters,
		order_by="creation desc",
	)
	sites_with_updates = set(site.name for site in sites_with_available_update())
	for site in sites:
		if site.name in sites_with_updates:
			site.update_available = True

	return sites


@frappe.whitelist()
@protected()
def get(name):
	site = frappe.get_doc("Site", name)
	bench = frappe.get_doc("Bench", site.bench)
	bench_apps = {app.app: app.idx for app in bench.apps}
	installed_apps = [app.app for app in site.apps]
	available_apps = list(filter(lambda x: x not in installed_apps, bench_apps.keys()))
	installed_apps = frappe.get_all(
		"Frappe App",
		fields=["name", "repo_owner as owner", "scrubbed as repo", "url", "branch"],
		filters={"name": ("in", installed_apps)},
	)
	available_apps = frappe.get_all(
		"Frappe App",
		fields=["name", "repo_owner as owner", "scrubbed as repo", "url", "branch"],
		filters={"name": ("in", available_apps)},
	)

	return {
		"name": site.name,
		"status": site.status,
		"installed_apps": sorted(installed_apps, key=lambda x: bench_apps[x.name]),
		"available_apps": sorted(available_apps, key=lambda x: bench_apps[x.name]),
		"setup_wizard_complete": site.setup_wizard_complete,
		"config": json.loads(site.config),
		"creation": site.creation,
		"last_updated": site.modified,
		"update_available": is_update_available_for_site(site.name),
	}


@frappe.whitelist()
@protected()
def analytics(name, period="1 hour"):
	interval, divisor, = {
		"1 hour": ("1 HOUR", 60),
		"6 hours": ("6 HOUR", 5 * 60),
		"24 hours": ("24 HOUR", 30 * 60),
		"7 days": ("7 DAY", 3 * 60 * 60),
		"30 days": ("30 DAY", 12 * 60 * 60),
	}[period]

	def get_data(doctype, fields):
		query = f"""
			SELECT
				{fields},
				FROM_UNIXTIME({divisor} * (UNIX_TIMESTAMP(timestamp) DIV {divisor})) as _timestamp
			FROM
				`tab{doctype}`
			WHERE
				site = %s AND timestamp >= UTC_TIMESTAMP() - INTERVAL {interval}
			GROUP BY
				_timestamp
		"""
		result = frappe.db.sql(query, name, as_dict=True, debug=False)
		for row in result:
			row["timestamp"] = row.pop("_timestamp")
		return result

	request_data = get_data(
		"Site Request Log", "COUNT(name) as request_count, SUM(duration) as request_duration"
	)
	job_data = get_data(
		"Site Job Log", "COUNT(name) as job_count, SUM(duration) as job_duration"
	)
	uptime_data = get_data(
		"Site Uptime Log",
		"AVG(web) AS web, AVG(scheduler) AS scheduler, AVG(socketio) AS socketio",
	)
	return {
		"request_count": [
			{"value": r.request_count, "timestamp": r.timestamp} for r in request_data
		],
		"request_cpu_time": [
			{"value": r.request_duration, "timestamp": r.timestamp} for r in request_data
		],
		"job_count": [{"value": r.job_count, "timestamp": r.timestamp} for r in job_data],
		"job_cpu_time": [
			{"value": r.job_duration, "timestamp": r.timestamp} for r in job_data
		],
		"uptime": uptime_data,
	}


@frappe.whitelist()
@protected()
def current_plan(name):
	plan_name = frappe.db.get_value("Site", name, "plan")
	plan = frappe.get_doc("Plan", plan_name)
	site_plan_changes = frappe.db.get_all(
		"Site Plan Change",
		filters={"site": name},
		fields=["name", "type", "owner", "to_plan", "timestamp"],
		order_by="timestamp desc",
		limit=5,
	)

	result = frappe.db.sql(
		"""SELECT
			SUM(duration) as total_cpu_usage
		FROM
			`tabSite Request Log` t
		WHERE
			t.site = %s
			and date(timestamp) = CURDATE();""",
		(name,),
		as_dict=True,
	)

	# cpu usage in microseconds
	total_cpu_usage = result[0].total_cpu_usage or 0
	# convert into hours
	total_cpu_usage_hours = flt(total_cpu_usage / (3.6 * (10 ** 9)), 5)

	# number of hours until cpu usage resets
	now = frappe.utils.now_datetime()
	today_end = now.replace(hour=23, minute=59, second=59)
	hours_left_today = flt(time_diff_in_hours(today_end, now), 2)

	return {
		"current_plan": plan,
		"history": site_plan_changes,
		"total_cpu_usage_hours": total_cpu_usage_hours,
		"hours_until_reset": hours_left_today,
	}


@frappe.whitelist()
@protected()
def change_plan(name, plan):
	frappe.get_doc("Site", name).change_plan(plan)


@frappe.whitelist()
@protected()
def deactivate(name):
	frappe.get_doc("Site", name).deactivate()


@frappe.whitelist()
@protected()
def activate(name):
	frappe.get_doc("Site", name).activate()


@frappe.whitelist()
@protected()
def login(name):
	return frappe.get_doc("Site", name).login()


@frappe.whitelist()
@protected()
def update(name):
	return frappe.get_doc("Site", name).schedule_update()


@frappe.whitelist()
@protected()
def backup(name, with_files=False):
	frappe.get_doc("Site", name).backup(with_files)


@frappe.whitelist()
@protected()
def archive(name):
	frappe.get_doc("Site", name).archive()


@frappe.whitelist()
@protected()
def reinstall(name):
	frappe.get_doc("Site", name).reinstall()


@frappe.whitelist()
@protected()
def restore(name, files):
	site = frappe.get_doc("Site", name)
	site.database_file = files["database"]
	site.public_file = files["public"]
	site.private_file = files["private"]
	site.save()
	site.restore()


@frappe.whitelist()
def exists(subdomain):
	return bool(
		frappe.db.exists("Site", {"subdomain": subdomain, "status": ("!=", "Archived")})
	)


@frappe.whitelist()
@protected()
def setup_wizard_complete(name):
	return frappe.get_doc("Site", name).is_setup_wizard_complete()


@frappe.whitelist()
@protected()
def check_dns(name, domain):
	def check_dns_cname(name, domain):
		try:
			answer = dns.resolver.query(domain, "CNAME")[0].to_text()
			mapped_domain = answer.rsplit(".", 1)[0]
			if mapped_domain == name:
				return True
		except Exception:
			log_error("DNS Query Exception - CNAME", site=name, domain=domain)
		return False

	def check_dns_a(name, domain):
		try:
			domain_ip = dns.resolver.query(domain, "A")[0].to_text()
			site_ip = dns.resolver.query(name, "A")[0].to_text()
			if domain_ip == site_ip:
				return True
		except Exception:
			log_error("DNS Query Exception - A", site=name, domain=domain)
		return False

	return check_dns_cname(name, domain) or check_dns_a(name, domain)


@frappe.whitelist()
@protected()
def add_domain(name, domain):
	frappe.get_doc("Site", name).add_domain(domain)


@frappe.whitelist()
@protected()
def retry_add_domain(name, domain):
	frappe.get_doc("Site", name).retry_add_domain(domain)


@frappe.whitelist()
@protected()
def install_app(name, app):
	frappe.get_doc("Site", name).install_app(app)


@frappe.whitelist()
@protected()
def logs(name):
	site = frappe.get_doc("Site", name)
	return Agent(site.server).get(f"benches/{site.bench}/sites/{name}/logs")


@frappe.whitelist()
@protected()
def log(name, log):
	site = frappe.get_doc("Site", name)
	return Agent(site.server).get(f"benches/{site.bench}/sites/{name}/logs/{log}")


@frappe.whitelist()
@protected()
def update_config(name, config):
	allowed_keys = [
		"encryption_key",
		"mail_server",
		"mail_port",
		"mail_login",
		"mail_password",
		"use_ssl",
		"auto_email_id",
		"mute_emails",
		"server_script_enabled",
		"disable_website_cache",
		"disable_global_search",
		"max_file_size",
	]
	if any(key not in allowed_keys for key in config.keys()):
		return

	# Remove keys with empty values
	config = {key: value for key, value in config.items() if value != ""}

	for key in ["max_file_size", "mail_port"]:
		if key in config:
			config[key] = cint(config[key])

	frappe.get_doc("Site", name).update_site_config(config)


def validate_database_backup(filename, content):
	try:
		with gzip.open(io.BytesIO(content)) as f:
			line = f.readline().decode().lower()
			if "mysql" in line or "mariadb" in line:
				return True
	except Exception:
		log_error("Invalid Database Backup File", filename=filename, content=content[:1024])


def validate_files_backup(filename, content, type):
	try:
		with tarfile.TarFile.open(fileobj=io.BytesIO(content), mode="r:") as f:
			files = f.getnames()
			if files:
				path = Path(files[0])
				if (
					path.name == "files"
					and path.parent.name == type
					and path.parent.parent.parent.name == ""
					and builtins.all(file.startswith(files[0]) for file in files)
				):
					return True
	except tarfile.TarError:
		log_error("Invalid Files Backup File", filename=filename, content=content[:1024])


def validate_backup(filename, content, type):
	if type == "database":
		return validate_database_backup(filename, content)
	else:
		return validate_files_backup(filename, content, type)


@frappe.whitelist()
def upload_backup():
	content = frappe.local.uploaded_file
	filename = frappe.local.uploaded_filename
	if validate_backup(filename, content, frappe.form_dict.type):
		file = frappe.get_doc(
			{
				"doctype": "File",
				"folder": "Home/Backup Uploads",
				"file_name": filename,
				"is_private": 1,
				"content": content,
			}
		)
		file.save(ignore_permissions=True)
		return file.file_url
	else:
		frappe.throw("Invalid Backup File")
