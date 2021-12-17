# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

import json
import wrapt
import frappe
import dns.resolver

from typing import Dict
from boto3 import client
from frappe.core.utils import find
from botocore.exceptions import ClientError
from frappe.desk.doctype.tag.tag import add_tag
from frappe.utils import flt, time_diff_in_hours
from frappe.utils.password import get_decrypted_password
from press.press.doctype.agent_job.agent_job import job_detail
from press.press.doctype.remote_file.remote_file import get_remote_key
from press.press.doctype.site_update.site_update import (
	benches_with_available_update,
	should_try_update,
)
from press.utils import (
	get_current_team,
	log_error,
	get_frappe_backups,
	get_client_blacklisted_keys,
	group_children_in_result,
	unique,
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
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new site because your account is disabled")

	files = site.get("files", {})
	share_details_consent = site.get("share_details_consent")

	domain = frappe.db.get_single_value("Press Settings", "domain")
	cluster = site.get("cluster") or frappe.db.get_single_value(
		"Press Settings", "cluster"
	)
	proxy_servers = frappe.get_all(
		"Proxy Server",
		[["status", "=", "Active"], ["Proxy Server Domain", "domain", "=", domain]],
		pluck="name",
	)

	bench = frappe.db.sql(
		"""
	SELECT
		bench.name, bench.cluster = %s as in_primary_cluster
	FROM
		tabBench bench
	LEFT JOIN
		tabServer server
	ON
		bench.server = server.name
	WHERE
		server.proxy_server in %s AND bench.status = "Active" AND bench.group = %s
	ORDER BY
		in_primary_cluster DESC, server.use_for_new_sites DESC, bench.creation DESC
	LIMIT 1
	""",
		(cluster, proxy_servers, site["group"]),
		as_dict=True,
	)[0].name
	plan = site["plan"]
	site = frappe.get_doc(
		{
			"doctype": "Site",
			"subdomain": site["name"],
			"bench": bench,
			"apps": [{"app": app} for app in site["apps"]],
			"team": team.name,
			"free": team.free_account,
			"subscription_plan": plan,
			"remote_config_file": files.get("config"),
			"remote_database_file": files.get("database"),
			"remote_public_file": files.get("public"),
			"remote_private_file": files.get("private"),
			"skip_failing_patches": site.get("skip_failing_patches", False),
		},
	).insert(ignore_permissions=True)
	site.create_subscription(plan)

	if share_details_consent:
		frappe.get_doc(doctype="Partner Lead", team=team.name, site=site.name).insert(
			ignore_permissions=True
		)

	return {
		"site": site.name,
		"job": frappe.db.get_value(
			"Agent Job",
			filters={
				"site": site.name,
				"job_type": ("in", ["New Site", "New Site from Backup"]),
			},
		),
	}


@frappe.whitelist()
@protected("Site")
def jobs(name, start=0):
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters={"site": name},
		start=start,
		limit=10,
	)
	return jobs


@frappe.whitelist()
def job(job):
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
		"remote_database_file",
		"remote_public_file",
		"remote_private_file",
	]
	latest_backups = frappe.get_all(
		"Site Backup",
		fields=fields,
		filters={"site": name, "files_availability": "Available", "offsite": 0},
		order_by="creation desc",
		limit=10,
	)
	offsite_backups = frappe.get_all(
		"Site Backup",
		fields=fields,
		filters={"site": name, "files_availability": "Available", "offsite": 1},
		order_by="creation desc",
		limit_page_length=available_offsite_backups,
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
		fields=["name", "domain", "status", "retry_count", "redirect_to_primary"],
		filters={"site": name},
	)
	host_name = frappe.db.get_value("Site", name, "host_name")
	primary = find(domains, lambda x: x.domain == host_name)
	if primary:
		primary.primary = True
	return domains


@frappe.whitelist()
def activities(name, start=0, limit=20):
	# get all site activity except Backup by Administrator
	activities = frappe.db.sql(
		"""
		SELECT action, reason, creation, owner
		FROM `tabSite Activity`
		WHERE site = %(site)s
		AND (action != 'Backup' or owner != 'Administrator')
		ORDER BY creation desc
		LIMIT %(limit)s
		OFFSET %(start)s
	""",
		values={"site": name, "limit": limit, "start": start},
		as_dict=1,
	)

	for activity in activities:
		if activity.action == "Create":
			activity.action = "Site created"

	return activities


@frappe.whitelist()
def options_for_new():
	team = get_current_team()
	versions = frappe.get_all(
		"Frappe Version",
		["name", "number", "default", "status"],
		{"public": True},
		order_by="`default` desc, number desc",
	)
	deployed_versions = []
	apps = set()
	for version in versions:
		groups = frappe.get_all(
			"Release Group",
			fields=["name", "`default`", "title"],
			filters={"enabled": True, "version": version.name},
			or_filters={"public": True, "team": team},
			order_by="public desc",
		)
		for group in groups:
			# Find most recently created bench
			# Assume that this bench has all the latest updates
			benches = frappe.get_all(
				"Bench",
				filters={"status": "Active", "group": group.name},
				order_by="creation desc",
				limit=1,
			)
			if not benches:
				continue

			bench = frappe.get_doc("Bench", benches[0].name)
			bench_apps = [app.source for app in bench.apps]
			app_sources = frappe.get_all(
				"App Source",
				[
					"name",
					"app",
					"repository_url",
					"repository",
					"repository_owner",
					"branch",
					"team",
					"public",
					"app_title",
					"frappe",
				],
				filters={"name": ("in", bench_apps)},
				or_filters={"public": True, "team": team},
			)
			group["apps"] = sorted(app_sources, key=lambda x: bench_apps.index(x.name))

			cluster_names = unique(
				frappe.db.get_all("Bench", filters={"candidate": bench.candidate}, pluck="cluster")
			)
			group["clusters"] = frappe.db.get_all(
				"Cluster",
				filters={"name": ("in", cluster_names), "public": True},
				fields=["name", "title", "image"],
			)
			version.setdefault("groups", []).append(group)
			apps.update([source.app for source in app_sources])
		if version.get("groups"):
			deployed_versions.append(version)

	marketplace_apps = frappe.db.get_all(
		"Marketplace App",
		fields=["title", "category", "image", "description", "app", "route"],
		filters={"app": ("in", list(apps))},
	)

	domain = frappe.db.get_value("Press Settings", "Press Settings", ["domain"])
	return {
		"domain": domain,
		"plans": get_plans(),
		"marketplace_apps": {row.app: row for row in marketplace_apps},
		"versions": deployed_versions,
	}


@frappe.whitelist()
def get_plans(name=None):
	filters = {"enabled": True, "document_type": "Site"}

	plans = frappe.db.get_all(
		"Plan",
		fields=[
			"name",
			"plan_title",
			"price_usd",
			"price_inr",
			"cpu_time_per_day",
			"max_storage_usage",
			"max_database_usage",
			"`tabHas Role`.role",
		],
		filters=filters,
		order_by="price_usd asc",
	)
	plans = group_children_in_result(plans, {"role": "roles"})

	if name:
		team = get_current_team()
		release_group_name = frappe.db.get_value("Site", name, "group")
		release_group = frappe.get_doc("Release Group", release_group_name)
		is_private_bench = release_group.team == team and not release_group.public
		# poor man's bench paywall
		# this will not allow creation of $10 sites on private benches
		# wanted to avoid adding a new field, so doing this with a date check :)
		# TODO: find a better way to do paywalls
		paywall_date = frappe.utils.get_datetime("2021-09-21 00:00:00")
		is_paywalled_bench = is_private_bench and release_group.creation > paywall_date
	else:
		is_paywalled_bench = False

	out = []
	for plan in plans:
		if is_paywalled_bench and plan.price_usd == 10:
			continue
		if frappe.utils.has_common(plan["roles"], frappe.get_roles()):
			plan.pop("roles", "")
			out.append(plan)
	return out


@frappe.whitelist()
def all():
	team = get_current_team()
	sites = frappe.get_list(
		"Site",
		fields=[
			"name",
			"status",
			"creation",
			"bench",
			"current_cpu_usage",
			"current_database_usage",
			"current_disk_usage",
			"trial_end_date",
		],
		filters={"team": team, "status": ("!=", "Archived")},
		order_by="creation desc",
		ignore_ifnull=True,
	)
	benches_with_updates = set(benches_with_available_update())
	for site in sites:
		if site.bench in benches_with_updates and should_try_update(site):
			site.update_available = True

	benches = frappe.db.get_all(
		"Bench",
		fields=["name", "status", "group"],
		filters={"name": ("in", set([site.bench for site in sites]))},
	)

	# includes public groups
	groups_with_sites = frappe.db.get_all(
		"Release Group",
		fields=["name", "title", "creation", "version", "team", "public"],
		filters={"enabled": True, "name": ("in", set([bench.group for bench in benches]))},
		order_by="creation desc",
	)

	empty_private_groups = frappe.db.get_all(
		"Release Group",
		fields=["name", "title", "creation", "version", "team", "public"],
		filters={
			"enabled": True,
			"team": team,
			"public": False,
			"name": ("not in", set([bench.group for bench in benches])),
		},
		order_by="creation desc",
	)

	groups = groups_with_sites + empty_private_groups
	shared_bench = frappe._dict(name="shared", shared=True, status="Active", sites=[])
	private_benches = []
	for group in groups:
		group.benches = [bench for bench in benches if bench.group == group.name]
		group.owned_by_team = team == group.team

		group.sites = []
		for bench in group.benches:
			group.sites += [site for site in sites if site.bench == bench.name]

		if group.public and not group.owned_by_team:
			shared_bench.sites += group.sites
		else:
			private_benches.append(group)

	private_benches = sorted(private_benches, key=lambda x: x.title)
	return [shared_bench] + private_benches


@frappe.whitelist()
@protected("Site")
def get(name):
	team = get_current_team()
	site = frappe.get_doc("Site", name)
	group_team = frappe.db.get_value("Release Group", site.group, "team")
	group_name = site.group if group_team == team else None

	return {
		"name": site.name,
		"status": site.status,
		"trial_end_date": site.trial_end_date,
		"setup_wizard_complete": site.setup_wizard_complete,
		"group": group_name,
		"team": site.team,
		"server_region_info": get_server_region_info(site),
	}


@frappe.whitelist()
@protected("Site")
def check_for_updates(name):
	site = frappe.get_doc("Site", name)
	out = frappe._dict()
	out.update_available = site.bench in benches_with_available_update()
	if not out.update_available:
		return out

	bench = frappe.get_doc("Bench", site.bench)
	source = bench.candidate
	destinations = frappe.get_all(
		"Deploy Candidate Difference",
		filters={"source": source},
		limit=1,
		pluck="destination",
	)
	if not destinations:
		out.update_available = False
		return out

	destination = destinations[0]
	site_update_log = frappe.db.exists(
		"Site Update",
		{
			"site": site.name,
			"source_candidate": source,
			"destination_candidate": destination,
			"cause_of_failure_is_resolved": False,
		},
	)
	if site_update_log:
		# update already attempted but it failed for some reason
		out.update_available = False
		return out

	destination_candidate = frappe.get_doc("Deploy Candidate", destination)

	out.apps = get_updates_between_current_and_next_apps(
		bench.apps, destination_candidate.apps
	)
	out.update_available = any([app["update_available"] for app in out.apps])
	return out


def get_updates_between_current_and_next_apps(current_apps, next_apps):
	from press.utils import get_app_tag

	apps = []
	for app in next_apps:
		bench_app = find(current_apps, lambda x: x.app == app.app)
		current_hash = bench_app.hash if bench_app else None
		source = frappe.get_doc("App Source", app.source)

		will_branch_change = False
		current_branch = source.branch
		if bench_app:
			current_source = frappe.get_doc("App Source", bench_app.source)
			will_branch_change = current_source.branch != source.branch
			current_branch = current_source.branch

		current_tag = (
			get_app_tag(source.repository, source.repository_owner, current_hash)
			if current_hash
			else None
		)
		next_hash = app.hash
		apps.append(
			{
				"title": app.title,
				"app": app.app,
				"repository": source.repository,
				"repository_owner": source.repository_owner,
				"repository_url": source.repository_url,
				"branch": source.branch,
				"current_hash": current_hash,
				"current_tag": current_tag,
				"next_hash": next_hash,
				"next_tag": get_app_tag(source.repository, source.repository_owner, next_hash),
				"will_branch_change": will_branch_change,
				"current_branch": current_branch,
				"update_available": not current_hash or current_hash != next_hash,
			}
		)
	return apps


@frappe.whitelist()
@protected("Site")
def overview(name):
	site = frappe.get_cached_doc("Site", name)

	return {
		"recent_activity": activities(name, limit=3),
		"plan": current_plan(name),
		"info": {
			"owner": frappe.db.get_value(
				"User", site.team, ["first_name", "last_name", "user_image"], as_dict=True
			),
			"created_on": site.creation,
			"last_deployed": (
				frappe.db.get_all(
					"Site Activity",
					filters={"site": name, "action": "Update"},
					order_by="creation desc",
					limit=1,
					pluck="creation",
				)
				or [None]
			)[0],
		},
		"installed_apps": get_installed_apps(site),
		"domains": domains(name),
	}


def get_installed_apps(site):
	installed_apps = [app.app for app in site.apps]
	bench = frappe.get_doc("Bench", site.bench)
	installed_bench_apps = [app for app in bench.apps if app.app in installed_apps]

	sources = frappe.get_all(
		"App Source",
		fields=[
			"name",
			"app",
			"repository",
			"repository_url",
			"repository_owner",
			"branch",
			"team",
			"public",
			"app_title as title",
		],
		filters={"name": ("in", [d.source for d in installed_bench_apps])},
	)

	installed_apps = []
	for app in installed_bench_apps:
		app_source = find(sources, lambda x: x.name == app.source)
		app_source.hash = app.hash
		app_source.tag = frappe.db.get_value(
			"App Tag",
			{
				"repository": app_source.repository,
				"repository_owner": app_source.repository_owner,
				"hash": app_source.hash,
			},
			"tag",
		)
		installed_apps.append(app_source)

	return installed_apps


def get_server_region_info(site) -> Dict:
	"""Return a Dict with `title` and `image`"""
	return frappe.db.get_value("Cluster", site.cluster, ["title", "image"], as_dict=True)


@frappe.whitelist()
@protected("Site")
def available_apps(name):
	team = get_current_team()
	site = frappe.get_doc("Site", name)
	installed_apps = [app.app for app in site.apps]

	bench = frappe.get_doc("Bench", site.bench)
	bench_sources = [app.source for app in bench.apps]

	available_sources = []
	sources = frappe.get_all(
		"App Source",
		fields=[
			"name",
			"app",
			"repository_url",
			"repository_owner",
			"branch",
			"team",
			"public",
			"app_title as title",
		],
		filters={"name": ("in", bench_sources)},
	)
	for source in sources:
		if (source.app not in installed_apps) and (source.public or source.team == team):
			available_sources.append(source)

	return sorted(available_sources, key=lambda x: bench_sources.index(x.name))


@frappe.whitelist()
@protected("Site")
def current_plan(name):
	from press.api.analytics import get_current_cpu_usage

	site = frappe.get_doc("Site", name)
	plan = frappe.get_doc("Plan", site.plan) if site.plan else None

	result = get_current_cpu_usage(name)
	total_cpu_usage_hours = flt(result / (3.6 * (10 ** 9)), 5)

	usage = frappe.get_all(
		"Site Usage",
		fields=["database", "public", "private"],
		filters={"site": name},
		order_by="creation desc",
		limit=1,
	)
	if usage:
		usage = usage[0]
		total_database_usage = usage.database
		total_storage_usage = usage.public + usage.private
	else:
		total_database_usage = 0
		total_storage_usage = 0

	# number of hours until cpu usage resets
	now = frappe.utils.now_datetime()
	today_end = now.replace(hour=23, minute=59, second=59)
	hours_left_today = flt(time_diff_in_hours(today_end, now), 2)

	return {
		"current_plan": plan,
		"total_cpu_usage_hours": total_cpu_usage_hours,
		"hours_until_reset": hours_left_today,
		"max_database_usage": plan.max_database_usage if plan else None,
		"max_storage_usage": plan.max_storage_usage if plan else None,
		"total_database_usage": total_database_usage,
		"total_storage_usage": total_storage_usage,
		"usage_in_percent": {
			"cpu": site.current_cpu_usage,
			"disk": site.current_disk_usage,
			"database": site.current_database_usage,
		},
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
def login(name, reason=None):
	return frappe.get_doc("Site", name).login(reason)


@frappe.whitelist()
@protected("Site")
def update(name, skip_failing_patches=False):
	return frappe.get_doc("Site", name).schedule_update(
		skip_failing_patches=skip_failing_patches
	)


@frappe.whitelist()
@protected("Site")
def last_migrate_failed(name):
	return frappe.get_doc("Site", name).last_migrate_failed()


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
def migrate(name, skip_failing_patches=False):
	frappe.get_doc("Site", name).migrate(skip_failing_patches=skip_failing_patches)


@frappe.whitelist()
@protected("Site")
def clear_cache(name):
	frappe.get_doc("Site", name).clear_site_cache()


@frappe.whitelist()
@protected("Site")
def restore(name, files, skip_failing_patches=False):
	site = frappe.get_doc("Site", name)
	site.remote_database_file = files["database"]
	site.remote_public_file = files["public"]
	site.remote_private_file = files["private"]
	site.save()
	site.reload()
	site.restore_site(skip_failing_patches=skip_failing_patches)


@frappe.whitelist()
def exists(subdomain):
	from press.press.doctype.site.site import Site

	return Site.exists(subdomain)


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
def set_redirect(name, domain):
	frappe.get_doc("Site", name).set_redirect(domain)


@frappe.whitelist()
@protected("Site")
def unset_redirect(name, domain):
	frappe.get_doc("Site", name).unset_redirect(domain)


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
def site_config(name):
	site = frappe.get_doc("Site", name)
	return list(filter(lambda x: not x.internal, site.configuration))


@frappe.whitelist()
@protected("Site")
def update_config(name, config):
	config = frappe.parse_json(config)
	config = [frappe._dict(c) for c in config]
	blacklisted_keys = get_client_blacklisted_keys()

	sanitized_config = []
	for c in config:
		if c.key in blacklisted_keys:
			continue
		if c.type == "Number":
			c.value = flt(c.value)
		elif c.type in ("JSON", "Boolean"):
			c.value = frappe.parse_json(c.value)
		sanitized_config.append(c)

	site = frappe.get_doc("Site", name)
	site.update_site_config(sanitized_config)
	return list(filter(lambda x: not x.internal, site.configuration))


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
			"Press Settings", "Press Settings", "remote_secret_access_key", raise_exception=False
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
def get_backup_links(url, email, password):
	files = get_frappe_backups(url, email, password)
	remote_files = []
	for file_type, file_url in files.items():
		file_name = file_url.split("backups/")[1].split("?sid=")[0]
		remote_files.append(
			{
				"type": file_type,
				"remote_file": uploaded_backup_info(file=file_name, url=file_url, type=file_type),
				"file_name": file_name,
				"url": file_url,
			}
		)

	return remote_files


@frappe.whitelist()
def search_list():
	team = get_current_team()
	sites = frappe.get_list("Site", filters={"status": ("!=", "Archived"), "team": team})

	return sites


@frappe.whitelist()
@protected("Site")
def enable_auto_update(name):
	site_doc = frappe.get_doc("Site", name)
	if not site_doc.auto_updates_scheduled:
		site_doc.auto_updates_scheduled = True
		site_doc.save()


@frappe.whitelist()
@protected("Site")
def disable_auto_update(name):
	site_doc = frappe.get_doc("Site", name)
	if site_doc.auto_updates_scheduled:
		site_doc.auto_updates_scheduled = False
		site_doc.save()


@frappe.whitelist()
@protected("Site")
def get_auto_update_info(name):
	site_doc = frappe.get_doc("Site", name)

	auto_update_info = {
		"auto_updates_scheduled": site_doc.auto_updates_scheduled,
		"auto_update_last_triggered_on": site_doc.auto_update_last_triggered_on,
		"update_trigger_frequency": site_doc.update_trigger_frequency,
		"update_trigger_time": site_doc.update_trigger_time,
		"update_on_weekday": site_doc.update_on_weekday,
		"update_end_of_month": site_doc.update_end_of_month,
		"update_on_day_of_month": site_doc.update_on_day_of_month,
	}

	return auto_update_info


@frappe.whitelist()
@protected("Site")
def update_auto_update_info(name, info=dict()):
	site_doc = frappe.get_doc("Site", name, for_update=True)
	site_doc.update(info)
	site_doc.save()
