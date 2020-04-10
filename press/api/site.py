# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import dns.resolver

import frappe
import json
from press.press.doctype.agent_job.agent_job import job_detail
from press.utils import log_error, get_current_team
from frappe.utils import cint


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
			"enable_scheduled_backups": site["backups"],
			"enable_uptime_monitoring": site["monitor"],
			"team": team,
			"plan": site["plan"],
		},
	).insert(ignore_permissions=True)
	return site.name


@frappe.whitelist()
def jobs(name):
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters={"site": name},
		limit=10,
	)
	return jobs


@frappe.whitelist()
def job(name):
	job = frappe.get_doc("Agent Job", name)
	job = job.as_dict()
	job.steps = frappe.get_all(
		"Agent Job Step",
		filters={"agent_job": name},
		fields=["step_name", "status", "start", "end", "duration", "output", "traceback"],
		order_by="creation",
	)
	return job


@frappe.whitelist()
def running_jobs(name):
	jobs = frappe.get_all(
		"Agent Job", filters={"status": ("in", ("Pending", "Running")), "site": name}
	)
	return [job_detail(job.name) for job in jobs]


@frappe.whitelist()
def backups(name):
	backups = frappe.get_all(
		"Site Backup",
		fields=["name", "`database`", "size", "url", "creation", "status"],
		filters={"site": name},
		limit=5,
	)
	return backups


@frappe.whitelist()
def domains(name):
	domains = frappe.get_all(
		"Site Domain", fields=["name", "domain", "status"], filters={"site": name}
	)
	return domains


@frappe.whitelist()
def activities(name):
	activities = frappe.get_all(
		"Site Activity",
		fields=["action", "creation", "owner"],
		filters={"site": name},
		limit=5,
	)
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

	domain, trial_sites_count = frappe.db.get_value(
		"Press Settings", "Press Settings", ["domain", "trial_sites_count"]
	)
	trial_sites_count = cint(trial_sites_count)
	team = get_current_team()
	has_subscription = bool(frappe.db.get_value("Subscription", {"team": team}))

	plans = frappe.db.get_all(
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
	# disable site creation if subscription not created and trial sites are exhausted
	disable_site_creation = bool(
		not has_subscription and frappe.db.count("Site", {"team": team}) >= trial_sites_count
	)

	return {
		"domain": domain,
		"groups": sorted(groups, key=lambda x: not x.default),
		"plans": plans,
		"has_subscription": has_subscription,
		"disable_site_creation": disable_site_creation,
		"trial_sites_count": trial_sites_count,
	}


@frappe.whitelist()
def all():
	sites = frappe.get_list(
		"Site", fields=["name", "status", "modified"], order_by="creation desc"
	)
	return sites


@frappe.whitelist()
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
		"config": json.loads(site.config),
		"creation": site.creation,
		"last_updated": site.modified,
	}


@frappe.whitelist()
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
def login(name):
	return frappe.get_doc("Site", name).login()


@frappe.whitelist()
def backup(name):
	frappe.get_doc("Site", name).backup()


@frappe.whitelist()
def archive(name):
	frappe.get_doc("Site", name).archive()


@frappe.whitelist()
def exists(subdomain):
	return bool(frappe.db.exists("Site", {"subdomain": subdomain}))


@frappe.whitelist()
def setup_wizard_complete(name):
	return frappe.get_doc("Site", name).setup_wizard_complete()


@frappe.whitelist()
def check_dns(name, domain):
	try:
		answer = dns.resolver.query(domain, "CNAME")[0].to_text()
		mapped_domain = answer.rsplit(".", 1)[0]
		if mapped_domain == name:
			return True
	except Exception:
		log_error("DNS Query Exception", site=name, domain=domain)
	return False


@frappe.whitelist()
def add_domain(name, domain):
	frappe.get_doc("Site", name).add_domain(domain)


@frappe.whitelist()
def install_app(name, app):
	frappe.get_doc("Site", name).install_app(app)


@frappe.whitelist()
def update_config(name, config):
	print(name, config)
	allowed_keys = [
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
	frappe.get_doc("Site", name).update_site_config(config)
