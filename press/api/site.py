# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import builtins
import gzip
import io
import json
import tarfile
from pathlib import Path

import dns.resolver
import wrapt
from boto3 import client
from botocore.exceptions import ClientError

import frappe
from frappe.core.utils import find
from frappe.desk.doctype.tag.tag import add_tag
from frappe.utils import cint, flt, time_diff_in_hours
from frappe.utils.password import get_decrypted_password
from press.press.doctype.agent_job.agent_job import job_detail
from press.press.doctype.plan.plan import get_plan_config
from press.press.doctype.remote_file.remote_file import get_remote_key
from press.press.doctype.site_update.site_update import (
	benches_with_available_update,
	should_try_update,
)
from press.utils import (
	get_current_team,
	log_error,
	verify_frappe_site,
	get_frappe_backups,
)


def protected(doctype):
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		name = kwargs.get("name") or args[0]
		team = get_current_team()
		owner = frappe.db.get_value(doctype, name, "team")
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
			"remote_database_file": site["files"]["database"],
			"remote_public_file": site["files"]["public"],
			"remote_private_file": site["files"]["private"],
		},
	).insert(ignore_permissions=True)
	return site.name


@frappe.whitelist()
@protected("Site")
def jobs(name):
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters={"site": name},
		limit=10,
	)
	return jobs


@frappe.whitelist()
@protected("Site")
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
@protected("Site")
def running_jobs(name):
	jobs = frappe.get_all(
		"Agent Job", filters={"status": ("in", ("Pending", "Running")), "site": name}
	)
	return [job_detail(job.name) for job in jobs]


@frappe.whitelist()
@protected("Site")
def backups(name):
	available_offsite_backups = (
		frappe.db.get_single_value("Press Settings", "offsite_backups_count") or 30
	)
	fields = [
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
		"offsite",
	]
	latest_backups = frappe.get_all(
		"Site Backup",
		fields=fields,
		filters={"site": name, "status": ("!=", "Failure"), "offsite": 0},
		limit=5,
	)
	offsite_backups = frappe.get_all(
		"Site Backup",
		fields=fields,
		filters={"site": name, "status": ("!=", "Failure"), "offsite": 1},
		limit=available_offsite_backups,
	)
	return sorted(
		latest_backups + offsite_backups, key=lambda x: x["creation"], reverse=True
	)


@frappe.whitelist()
@protected("Site")
def get_backup_link(name, backup, file):
	try:
		remote_file = frappe.db.get_value("Site Backup", backup, f"remote_{file}_file")
		return frappe.get_doc("Remote File", remote_file).download_link
	except ClientError:
		log_error(title="Offsite Backup Response Exception")


@frappe.whitelist()
@protected("Site")
def domains(name):
	domains = frappe.get_all(
		"Site Domain",
		fields=["name", "domain", "status", "retry_count"],
		filters={"site": name},
	)
	host_name = frappe.db.get_value("Site", name, "host_name")
	primary = find(domains, lambda x: x.domain == host_name)
	if primary:
		primary.primary = True
	return domains


@frappe.whitelist()
def activities(name, start=0):
	activities = frappe.get_all(
		"Site Activity",
		fields=["action", "reason", "creation", "owner"],
		filters={"site": name},
		start=start,
		limit=20,
	)

	for activity in activities:
		if activity.action == "Create":
			activity.action = "Site created"

	return activities


@frappe.whitelist()
@protected("Site")
def request_logs(name, start=0):
	logs = frappe.get_all(
		"Site Request Log",
		fields=["*"],
		filters={"site": name, "url": ("!=", "/api/method/ping")},
		start=start,
		limit=20,
	)
	return logs


@frappe.whitelist()
def options_for_new():
	team = get_current_team()
	groups = frappe.get_all(
		"Release Group",
		fields=["name", "`default`"],
		or_filters={"public": True, "team": team},
	)
	deployed_groups = []
	for group in groups:
		benches = frappe.get_all(
			"Bench",
			filters={"status": "Active", "group": group.name},
			order_by="creation desc",
			limit=1,
		)
		if not benches:
			continue
		bench = benches[0].name
		bench_doc = frappe.get_doc("Bench", bench)
		group_apps = frappe.get_all(
			"Frappe App",
			fields=["name", "frappe", "branch", "scrubbed", "repo_owner", "repo"],
			filters={"name": ("in", [row.app for row in bench_doc.apps])},
			or_filters={"team": team, "public": True},
		)
		order = {row.app: row.idx for row in bench_doc.apps}
		group["apps"] = sorted(group_apps, key=lambda x: order[x.name])
		deployed_groups.append(group)

	domain = frappe.db.get_value("Press Settings", "Press Settings", ["domain"])

	team_doc = frappe.get_doc("Team", team)
	# disable site creation if card not added
	disable_site_creation = (
		not team_doc.default_payment_method and not team_doc.erpnext_partner
	)
	allow_partner = team_doc.is_partner_and_has_enough_credits()

	return {
		"domain": domain,
		"groups": sorted(deployed_groups, key=lambda x: not x.default),
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
	sites = frappe.get_list(
		"Site",
		fields=["name", "status", "modified", "bench"],
		filters={"team": get_current_team(), "status": ("!=", "Archived")},
		order_by="creation desc",
	)
	benches_with_updates = set(benches_with_available_update())
	for site in sites:
		if site.bench in benches_with_updates:
			site.update_available = True

	return sites


@frappe.whitelist()
@protected("Site")
def get(name):
	team = get_current_team()
	site = frappe.get_doc("Site", name)
	installed_apps = [app.app for app in site.apps]
	bench = frappe.get_doc("Bench", site.bench)
	bench_apps = {}
	for app in bench.apps:
		app_team, app_public = frappe.db.get_value("Frappe App", app.app, ["team", "public"])
		if app.app in installed_apps or app_public or app_team == team:
			bench_apps[app.app] = app.idx

	available_apps = list(filter(lambda x: x not in installed_apps, bench_apps.keys()))
	installed_apps = frappe.get_all(
		"Frappe App",
		fields=["name", "repo_owner as owner", "scrubbed as repo", "url", "branch", "frappe"],
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
		"owner": site.owner,
		"last_updated": site.modified,
		"update_available": (site.bench in benches_with_available_update())
		and should_try_update(site),
	}


@frappe.whitelist()
@protected("Site")
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

	usage_data = get_data("Site Request Log", "counter")
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
	plan = frappe.db.get_value("Site", name, "plan")
	plan_limit = get_plan_config(plan)["rate_limit"]["limit"]
	return {
		"usage_counter": [{"value": r.counter, "timestamp": r.timestamp} for r in usage_data],
		"request_count": [
			{"value": r.request_count, "timestamp": r.timestamp} for r in request_data
		],
		"request_cpu_time": [
			{"value": r.request_duration, "timestamp": r.timestamp} for r in request_data
		],
		"job_count": [
			{"value": r.job_count * 1000, "timestamp": r.timestamp} for r in job_data
		],
		"job_cpu_time": [
			{"value": r.job_duration * 1000, "timestamp": r.timestamp} for r in job_data
		],
		"uptime": (uptime_data + [{}] * 60)[:60],
		"plan_limit": plan_limit,
	}


@frappe.whitelist()
@protected("Site")
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
	result = frappe.get_all(
		"Site Request Log",
		fields=["reset", "counter"],
		filters={"site": name},
		order_by="creation desc",
		limit=1,
	)
	if result:
		result = result[0]
		# cpu usage in microseconds
		total_cpu_usage = cint(result.counter)
		# convert into hours
		total_cpu_usage_hours = flt(total_cpu_usage / (3.6 * (10 ** 9)), 5)
	else:
		total_cpu_usage_hours = 0

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
@protected("Site")
def change_plan(name, plan):
	frappe.get_doc("Site", name).change_plan(plan)


@frappe.whitelist()
@protected("Site")
def deactivate(name):
	frappe.get_doc("Site", name).deactivate()


@frappe.whitelist()
@protected("Site")
def activate(name):
	frappe.get_doc("Site", name).activate()


@frappe.whitelist()
@protected("Site")
def login(name):
	return frappe.get_doc("Site", name).login()


@frappe.whitelist()
@protected("Site")
def update(name):
	return frappe.get_doc("Site", name).schedule_update()


@frappe.whitelist()
@protected("Site")
def backup(name, with_files=False):
	frappe.get_doc("Site", name).backup(with_files)


@frappe.whitelist()
@protected("Site")
def archive(name):
	frappe.get_doc("Site", name).archive()


@frappe.whitelist()
@protected("Site")
def reinstall(name):
	frappe.get_doc("Site", name).reinstall()


@frappe.whitelist()
@protected("Site")
def migrate(name):
	frappe.get_doc("Site", name).migrate()


@frappe.whitelist()
@protected("Site")
def restore(name, files):
	site = frappe.get_doc("Site", name)
	site.remote_database_file = files["database"]
	site.remote_public_file = files["public"]
	site.remote_private_file = files["private"]
	site.save()
	site.restore_site()


@frappe.whitelist()
def exists(subdomain):
	return bool(
		frappe.db.exists("Site", {"subdomain": subdomain, "status": ("!=", "Archived")})
	)


@frappe.whitelist()
@protected("Site")
def setup_wizard_complete(name):
	return frappe.get_doc("Site", name).is_setup_wizard_complete()


def check_dns_cname_a(name, domain):
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
@protected("Site")
def check_dns(name, domain):
	return check_dns_cname_a(name, domain)


@frappe.whitelist()
def domain_exists(domain):
	return frappe.db.get_value("Site Domain", domain.lower(), "site")


@frappe.whitelist()
@protected("Site")
def add_domain(name, domain):
	frappe.get_doc("Site", name).add_domain(domain)


@frappe.whitelist()
@protected("Site")
def remove_domain(name, domain):
	frappe.get_doc("Site", name).remove_domain(domain)


@frappe.whitelist()
@protected("Site")
def retry_add_domain(name, domain):
	frappe.get_doc("Site", name).retry_add_domain(domain)


@frappe.whitelist()
@protected("Site")
def set_host_name(name, domain):
	frappe.get_doc("Site", name).set_host_name(domain)


@frappe.whitelist()
@protected("Site")
def install_app(name, app):
	frappe.get_doc("Site", name).install_app(app)


@frappe.whitelist()
@protected("Site")
def uninstall_app(name, app):
	frappe.get_doc("Site", name).uninstall_app(app)


@frappe.whitelist()
@protected("Site")
def logs(name):
	return frappe.get_doc("Site", name).server_logs


@frappe.whitelist()
@protected("Site")
def log(name, log):
	return frappe.get_doc("Site", name).get_server_log(log)


@frappe.whitelist()
@protected("Site")
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


@frappe.whitelist()
def get_upload_link(file, parts=1):
	bucket_name = frappe.db.get_single_value("Press Settings", "remote_uploads_bucket")
	expiration = frappe.db.get_single_value("Press Settings", "remote_link_expiry") or 3600
	object_name = get_remote_key(file)
	parts = int(parts)

	s3_client = client(
		"s3",
		aws_access_key_id=frappe.db.get_single_value(
			"Press Settings", "remote_access_key_id"
		),
		aws_secret_access_key=get_decrypted_password(
			"Press Settings", "Press Settings", "remote_secret_access_key"
		),
		region_name="ap-south-1",
	)
	try:
		# The response contains the presigned URL and required fields
		if parts > 1:
			signed_urls = []
			response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=object_name)

			for count in range(parts):
				signed_url = s3_client.generate_presigned_url(
					ClientMethod="upload_part",
					Params={
						"Bucket": bucket_name,
						"Key": object_name,
						"UploadId": response.get("UploadId"),
						"PartNumber": count + 1,
					},
				)
				signed_urls.append(signed_url)

			payload = response
			payload["signed_urls"] = signed_urls
			return payload

		return s3_client.generate_presigned_post(
			bucket_name, object_name, ExpiresIn=expiration
		)

	except ClientError as e:
		log_error("Failed to Generate Presigned URL", content=e)


@frappe.whitelist()
def multipart_exit(file, id, action, parts=None):
	s3_client = client(
		"s3",
		aws_access_key_id=frappe.db.get_single_value(
			"Press Settings", "remote_access_key_id"
		),
		aws_secret_access_key=get_decrypted_password(
			"Press Settings", "Press Settings", "remote_secret_access_key"
		),
		region_name="ap-south-1",
	)
	if action == "abort":
		response = s3_client.abort_multipart_upload(
			Bucket="uploads.frappe.cloud", Key=file, UploadId=id,
		)
	elif action == "complete":
		parts = json.loads(parts)
		# After completing for all parts, you will use complete_multipart_upload api which requires that parts list
		response = s3_client.complete_multipart_upload(
			Bucket="uploads.frappe.cloud",
			Key=file,
			UploadId=id,
			MultipartUpload={"Parts": parts},
		)
	return response


@frappe.whitelist()
def uploaded_backup_info(file=None, path=None, type=None, size=None, url=None):
	doc = frappe.get_doc(
		{
			"doctype": "Remote File",
			"file_name": file,
			"file_type": type,
			"file_size": size,
			"file_path": path,
			"url": url,
			"bucket": frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"),
		}
	).insert()
	add_tag("Site Upload", doc.doctype, doc.name)
	return doc.name


@frappe.whitelist()
def verify(site):
	return verify_frappe_site(site)


@frappe.whitelist()
def get_backup_links(site, auth):
	return get_frappe_backups(site, auth)
