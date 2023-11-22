# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

import json
from frappe.utils.user import is_system_user
from press.press.doctype.marketplace_app.marketplace_app import get_plans_for_app
import wrapt
import frappe
from dns.resolver import Resolver
import dns.exception

from typing import Dict
from boto3 import client
from frappe.core.utils import find
from botocore.exceptions import ClientError
from frappe.desk.doctype.tag.tag import add_tag
from frappe.utils import flt, time_diff_in_hours
from frappe.utils.password import get_decrypted_password
from press.press.doctype.agent_job.agent_job import job_detail
from press.press.doctype.press_user_permission.press_user_permission import (
	has_user_permission,
)
from press.press.doctype.remote_file.remote_file import get_remote_key
from press.press.doctype.site_update.site_update import benches_with_available_update
from press.utils import (
	get_current_team,
	log_error,
	get_last_doc,
	get_frappe_backups,
	get_client_blacklisted_keys,
	group_children_in_result,
	unique,
)

NAMESERVERS = ["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"]


def protected(doctypes):
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		request_path = (
			frappe.local.request.path.rsplit("/", 1)[-1]
			if hasattr(frappe.local, "request")
			else ""
		)
		user_type = frappe.session.data.user_type or frappe.get_cached_value(
			"User", frappe.session.user, "user_type"
		)
		if user_type == "System User":
			return wrapped(*args, **kwargs)

		# name is either name or 1st value from filters dict from kwargs or 1st value from args
		name = (
			kwargs.get("name") or next(iter(kwargs.get("filters", {}).values()), None) or args[0]
		)
		team = get_current_team()

		nonlocal doctypes
		if not isinstance(doctypes, list):
			doctypes = [doctypes]

		for doctype in doctypes:
			owner = frappe.db.get_value(doctype, name, "team")
			if owner == team:
				if frappe.get_value("Team", team, "user") != frappe.session.user and hasattr(
					frappe.local, "request"
				):
					# Logged in user is a team member
					# Check if the user has permission to access the document
					groups = frappe.get_all(
						"Press Permission Group User",
						{
							"user": frappe.session.user,
						},
						pluck="parent",
					)
					name = frappe.db.get_value(doctype, name, "group") if doctype == "Bench" else name
					doctype = "Release Group" if doctype == "Bench" else doctype
					if (
						frappe.db.exists("Press User Permission", {"user": frappe.session.user}) or groups
					) and frappe.db.exists(
						"Press Method Permission", {"method": request_path}
					):
						# has restricted access
						if has_user_permission(doctype, name, request_path, groups):
							return wrapped(*args, **kwargs)
					else:
						# has access to everything
						return wrapped(*args, **kwargs)
				else:
					# Logged in user is the team owner
					return wrapped(*args, **kwargs)

		raise frappe.PermissionError

	return wrapper


def _new(site, server: str = None, ignore_plan_validation: bool = False):
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new site because your account is disabled")

	files = site.get("files", {})
	share_details_consent = site.get("share_details_consent")

	domain = site.get("domain")
	if not (domain and frappe.db.exists("Root Domain", {"name": domain})):
		frappe.throw("No root domain for site")

	cluster = site.get("cluster") or frappe.db.get_single_value(
		"Press Settings", "cluster"
	)

	proxy_servers = frappe.get_all(
		"Proxy Server Domain", {"domain": domain}, pluck="parent"
	)
	proxy_servers = frappe.get_all(
		"Proxy Server",
		{"status": "Active", "name": ("in", proxy_servers)},
		pluck="name",
	)
	proxy_servers = (
		tuple(proxy_servers) if len(proxy_servers) > 1 else f"('{proxy_servers[0]}')"
	)

	query_sub_str = ""
	if server:
		query_sub_str = f"AND server.name = '{server}'"

	bench = frappe.db.sql(
		f"""
	SELECT
		bench.name, bench.server, bench.cluster = '{cluster}' as in_primary_cluster
	FROM
		tabBench bench
	LEFT JOIN
		tabServer server
	ON
		bench.server = server.name
	WHERE
		server.proxy_server in {proxy_servers} AND
		bench.status = "Active" AND
		bench.group = '{site["group"]}'
		{query_sub_str}
	ORDER BY
		in_primary_cluster DESC, server.use_for_new_sites DESC, bench.creation DESC
	LIMIT 1
	""",
		as_dict=True,
	)[0]
	plan = site["plan"]
	app_plans = site.get("selected_app_plans")
	if not ignore_plan_validation:
		validate_plan(bench.server, plan)

	site = frappe.get_doc(
		{
			"doctype": "Site",
			"subdomain": site["name"],
			"domain": domain,
			"group": site["group"],
			"server": server,
			"cluster": cluster,
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
	)

	if app_plans and len(app_plans) > 0:
		subscription_docs = get_app_subscriptions(app_plans, team.name)

		# Set the secret keys for subscription in config
		secret_keys = {f"sk_{s.app}": s.secret_key for s in subscription_docs}
		site._update_configuration(secret_keys, save=False)

	site.insert(ignore_permissions=True)

	if app_plans and len(app_plans) > 0:
		# Set site in subscription docs
		for doc in subscription_docs:
			doc.site = site.name
			doc.save(ignore_permissions=True)

	# Telemetry: Send event if first site
	if len(frappe.db.get_all("Site", {"team": team.name})) <= 1:
		from press.utils.telemetry import capture

		capture("created_first_site", "fc_signup", team.account_request)

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


def validate_plan(server, plan):
	if frappe.db.get_value("Plan", plan, "price_usd") > 0:
		return
	if (
		frappe.session.data.user_type == "System User"
		or frappe.db.get_value("Server", server, "team") == get_current_team()
	):
		return
	frappe.throw("You are not allowed to use this plan")


@frappe.whitelist()
def new(site):
	site["domain"] = frappe.db.get_single_value("Press Settings", "domain")

	return _new(site)


def get_app_subscriptions(app_plans, team: str):
	subscriptions = []

	for app_name, plan_name in app_plans.items():
		is_free = frappe.db.get_value("Marketplace App Plan", plan_name, "is_free")
		if not is_free:
			team = get_current_team(get_doc=True)
			if not team.can_install_paid_apps():
				frappe.throw(
					"You cannot install a Paid app on Free Credits. Please buy credits before trying to install again."
				)

		new_subscription = frappe.get_doc(
			{
				"doctype": "Marketplace App Subscription",
				"marketplace_app_plan": plan_name,
				"app": app_name,
				"team": team,
				"while_site_creation": True,
			}
		).insert(ignore_permissions=True)

		subscriptions.append(new_subscription)

	return subscriptions


@frappe.whitelist()
@protected("Site")
def jobs(filters=None, order_by=None, limit_start=None, limit_page_length=None):
	jobs = frappe.get_all(
		"Agent Job",
		fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
		filters=filters,
		start=limit_start,
		limit=limit_page_length,
		order_by=order_by or "creation desc",
	)
	return jobs


@frappe.whitelist()
def job(job):
	job = frappe.get_doc("Agent Job", job)
	job = job.as_dict()
	whitelisted_fields = [
		"name",
		"job_type",
		"creation",
		"status",
		"start",
		"end",
		"duration",
	]
	for key in list(job.keys()):
		if key not in whitelisted_fields:
			job.pop(key, None)

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
		"config_file_size",
		"config_file_url",
		"config_file",
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
		"remote_config_file",
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
	domains.sort(key=lambda domain: not domain.primary)
	return domains


@frappe.whitelist()
def activities(filters=None, order_by=None, limit_start=None, limit_page_length=None):
	# get all site activity except Backup by Administrator
	SiteActivity = frappe.qb.DocType("Site Activity")
	activities = (
		frappe.qb.from_(SiteActivity)
		.select(
			SiteActivity.action, SiteActivity.reason, SiteActivity.creation, SiteActivity.owner
		)
		.where(SiteActivity.site == filters["site"])
		.where((SiteActivity.action != "Backup") | (SiteActivity.owner != "Administrator"))
		.orderby(SiteActivity.creation, order=frappe.qb.desc)
		.offset(limit_start)
		.limit(limit_page_length)
		.run(as_dict=True)
	)

	for activity in activities:
		if activity.action == "Create":
			activity.action = "Site Created"

	return activities


@frappe.whitelist()
def options_for_new():
	versions = frappe.db.get_all(
		"Frappe Version",
		["name", "default", "status", "number"],
		{"public": True},
		order_by="number desc",
	)
	available_versions = []
	for version in versions:
		release_group = frappe.db.get_value(
			"Release Group",
			fieldname=["name", "`default`", "title"],
			filters={
				"enabled": 1,
				"public": 1,
				"version": version.name,
			},
			order_by="creation desc",
			as_dict=1,
		)
		version.group = release_group
		if version.group:
			bench = frappe.db.get_value(
				"Bench",
				filters={"status": "Active", "group": version.group.name},
				order_by="creation desc",
			)
			if bench:
				version.group.bench = bench
				bench_app_sources = frappe.db.get_all("Bench App", {"parent": bench}, pluck="source")
				app_sources = frappe.db.get_all(
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
					filters={"name": ("in", bench_app_sources), "frappe": 0, "public": True},
				)
				version.group.apps = app_sources
				if version.group.apps:
					marketplace_apps = frappe.db.get_all(
						"Marketplace App",
						fields=["title", "image", "description", "app", "route"],
						filters={"app": ("in", [app.app for app in version.group.apps])},
					)
					for app in version.group.apps:
						marketplace_details = find(marketplace_apps, lambda x: x.app == app.app)
						if marketplace_details:
							app.update(marketplace_details)
							app.plans = get_plans_for_app(app.app, version.name)

				cluster_names = unique(
					frappe.db.get_all(
						"Bench",
						filters={"candidate": frappe.db.get_value("Bench", bench, "candidate")},
						pluck="cluster",
					)
				)
				clusters = frappe.db.get_all(
					"Cluster",
					filters={"name": ("in", cluster_names), "public": True},
					fields=["name", "title", "image"],
				)
				version.group.clusters = clusters

				if version.group and version.group.bench and version.group.clusters:
					available_versions.append(version)

	return {
		"versions": available_versions,
		"domain": frappe.db.get_single_value("Press Settings", "domain"),
	}


@frappe.whitelist()
def get_domain():
	return frappe.db.get_value("Press Settings", "Press Settings", ["domain"])


@frappe.whitelist()
def get_new_site_options(group: str = None):
	team = get_current_team()
	versions = frappe.get_all(
		"Frappe Version",
		["name", "number", "default", "status"],
		{"public": True},
		order_by="`default` desc, number desc",
	)
	apps = set()
	filters = {"enabled": True}
	if group:  # private bench
		filters.update({"name": group, "team": team})
	else:
		filters.update({"public": True})

	for version in versions:
		filters.update({"version": version.name})
		rg = frappe.get_all(
			"Release Group",
			fields=["name", "`default`", "title"],
			filters=filters,
			limit=1,
		)
		if not rg:
			continue
		else:
			rg = rg[0]

		benches = frappe.get_all(
			"Bench",
			filters={"status": "Active", "group": rg.name},
			order_by="creation desc",
			limit=1,
		)
		if not benches:
			continue

		bench_name = benches[0].name
		bench_apps = frappe.get_all("Bench App", {"parent": bench_name}, pluck="source")
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
		rg["apps"] = sorted(app_sources, key=lambda x: bench_apps.index(x.name))

		# Regions with latest update
		cluster_names = unique(
			frappe.db.get_all(
				"Bench",
				filters={"candidate": frappe.db.get_value("Bench", bench_name, "candidate")},
				pluck="cluster",
			)
		)
		rg["clusters"] = frappe.db.get_all(
			"Cluster",
			filters={"name": ("in", cluster_names), "public": True},
			fields=["name", "title", "image"],
		)
		version["group"] = rg
		apps.update([source.app for source in app_sources])

	marketplace_apps = frappe.db.get_all(
		"Marketplace App",
		fields=["title", "image", "description", "app", "route"],
		filters={"app": ("in", list(apps))},
	)
	return {
		"versions": versions,
		"marketplace_apps": {row.app: row for row in marketplace_apps},
	}


@frappe.whitelist()
def get_plans(name=None, rg=None):
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
			"database_access",
			"support_included",
			"`tabHas Role`.role",
		],
		filters=filters,
		order_by="price_usd asc",
	)
	plans = group_children_in_result(plans, {"role": "roles"})

	if name or rg:
		team = get_current_team()
		release_group_name = rg if rg else frappe.db.get_value("Site", name, "group")
		release_group = frappe.get_doc("Release Group", release_group_name)
		is_private_bench = release_group.team == team and not release_group.public
		is_system_user = (
			frappe.db.get_value("User", frappe.session.user, "user_type") == "System User"
		)
		# poor man's bench paywall
		# this will not allow creation of $10 sites on private benches
		# wanted to avoid adding a new field, so doing this with a date check :)
		# TODO: find a better way to do paywalls
		paywall_date = frappe.utils.get_datetime("2021-09-21 00:00:00")
		is_paywalled_bench = (
			is_private_bench and release_group.creation > paywall_date and not is_system_user
		)
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


def sites_with_recent_activity(sites, limit=3):
	site_activity = frappe.qb.DocType("Site Activity")

	query = (
		frappe.qb.from_(site_activity)
		.select(site_activity.site)
		.where(site_activity.site.isin(sites))
		.where(site_activity.action != "Backup")
		.orderby(site_activity.creation, order=frappe.qb.desc)
		.limit(limit)
		.distinct()
	)

	return query.run(pluck="site")


@frappe.whitelist()
def all(site_filter=None):
	from press.press.doctype.team.team import get_child_team_members

	if site_filter is None:
		site_filter = {"status": "", "tag": ""}

	team = get_current_team()
	child_teams = [x.name for x in get_child_team_members(team)]
	benches_with_updates = tuple(benches_with_available_update())

	Site = frappe.qb.DocType("Site")
	ReleaseGroup = frappe.qb.DocType("Release Group")
	sites_query = (
		frappe.qb.from_(Site)
		.select(
			Site.name,
			Site.host_name,
			Site.status,
			Site.creation,
			Site.bench,
			Site.current_cpu_usage,
			Site.current_database_usage,
			Site.current_disk_usage,
			Site.trial_end_date,
			Site.team,
			Site.cluster,
			Site.group,
			ReleaseGroup.title,
			ReleaseGroup.version,
			ReleaseGroup.public,
		)
		.left_join(ReleaseGroup)
		.on(Site.group == ReleaseGroup.name)
		.orderby(Site.creation, order=frappe.qb.desc)
	)
	if child_teams:
		sites_query = sites_query.where(Site.team.isin([team] + child_teams))
	else:
		sites_query = sites_query.where(Site.team == team)

	if site_filter["status"] == "Active":
		sites_query = sites_query.where(Site.status == "Active")
	elif site_filter["status"] == "Broken":
		sites_query = sites_query.where(Site.status == "Broken")
	elif site_filter["status"] == "Inactive":
		sites_query = sites_query.where(Site.status == "Inactive")
	elif site_filter["status"] == "Trial":
		sites_query = sites_query.where(
			(Site.trial_end_date != "") & (Site.status != "Archived")
		)
	elif site_filter["status"] == "Update Available":
		sites_query = sites_query.where(
			Site.bench.isin(benches_with_updates) & (Site.status != "Archived")
		)
	else:
		sites_query = sites_query.where(Site.status != "Archived")

	if site_filter["tag"]:
		Tag = frappe.qb.DocType("Resource Tag")
		sites_with_tag = (
			frappe.qb.from_(Tag).select(Tag.parent).where(Tag.tag_name == site_filter["tag"])
		)
		sites_query = sites_query.where(Site.name.isin(sites_with_tag))

	sites = sites_query.run(as_dict=True)

	for site in sites:
		site.server_region_info = get_server_region_info(site)
		site_plan_name = frappe.get_value("Site", site.name, "plan")
		site.plan = frappe.get_doc("Plan", site_plan_name) if site_plan_name else None
		site.tags = frappe.get_all(
			"Resource Tag",
			{"parent": site.name},
			pluck="tag_name",
		)
		if site.bench in benches_with_updates:
			site.update_available = True

	return sites


@frappe.whitelist()
def site_tags():
	team = get_current_team()
	return frappe.get_all("Press Tag", {"team": team, "doctype_name": "Site"}, pluck="tag")


@frappe.whitelist()
@protected("Site")
def get(name):
	from frappe.utils.data import time_diff

	team = get_current_team()
	try:
		site = frappe.get_doc("Site", name)
	except frappe.DoesNotExistError:
		# If name is a custom domain then redirect to the site name
		site_name = frappe.db.get_value("Site Domain", name, "site")
		if site_name:
			frappe.local.response["type"] = "redirect"
			frappe.local.response[
				"location"
			] = f"/api/method/press.api.site.get?name={site_name}"
			return
		else:
			raise
	rg_info = frappe.db.get_value(
		"Release Group", site.group, ["team", "version", "public"], as_dict=True
	)
	group_team = rg_info.team
	frappe_version = rg_info.version
	group_name = (
		site.group if group_team == team or is_system_user(frappe.session.user) else None
	)

	server = frappe.db.get_value(
		"Server", site.server, ["ip", "is_standalone", "proxy_server", "team"], as_dict=True
	)
	if server.is_standalone:
		ip = server.ip
	else:
		ip = frappe.db.get_value("Proxy Server", server.proxy_server, "ip")

	site_migration = get_last_doc("Site Migration", {"site": site.name})
	if (
		site_migration
		and site_migration.status not in ["Failure", "Success"]
		and -1
		<= time_diff(site_migration.scheduled_time, frappe.utils.now_datetime()).days
		<= 1
	):
		job = find(site_migration.steps, lambda x: x.status == "Running")
		site_migration = {
			"status": site_migration.status,
			"scheduled_time": site_migration.scheduled_time,
			"job_id": job.step_job if job else None,
		}
	else:
		site_migration = None

	version_upgrade = get_last_doc("Version Upgrade", {"site": site.name})
	if (
		version_upgrade
		and version_upgrade.status not in ["Failure", "Success"]
		and -1
		<= time_diff(version_upgrade.scheduled_time, frappe.utils.now_datetime()).days
		<= 1
	):
		version_upgrade = {
			"status": version_upgrade.status,
			"scheduled_time": version_upgrade.scheduled_time,
			"job_id": frappe.get_value("Site Update", version_upgrade.site_update, "update_job"),
		}
	else:
		version_upgrade = None

	return {
		"name": site.name,
		"host_name": site.host_name,
		"status": site.status,
		"archive_failed": bool(site.archive_failed),
		"trial_end_date": site.trial_end_date,
		"setup_wizard_complete": site.setup_wizard_complete,
		"group": group_name,
		"team": site.team,
		"is_public": rg_info.public,
		"latest_frappe_version": frappe.db.get_value("Frappe Version", {"status": "Stable"}),
		"frappe_version": frappe_version,
		"server": site.server,
		"server_region_info": get_server_region_info(site),
		"can_change_plan": server.team != team,
		"hide_config": site.hide_config,
		"notify_email": site.notify_email,
		"ip": ip,
		"site_tags": [{"name": x.tag, "tag": x.tag_name} for x in site.tags],
		"tags": frappe.get_all(
			"Press Tag", {"team": team, "doctype_name": "Site"}, ["name", "tag"]
		),
		"info": {
			"owner": frappe.db.get_value(
				"User",
				frappe.get_cached_doc("Team", site.team).user,
				["first_name", "last_name", "user_image"],
				as_dict=True,
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
			"auto_updates_enabled": not site.skip_auto_updates,
		},
		"pending_for_long": site.pending_for_long,
		"site_migration": site_migration,
		"version_upgrade": version_upgrade,
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

	destination_candidate = frappe.get_doc("Deploy Candidate", destination)

	out.installed_apps = site.apps
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
def installed_apps(name):
	site = frappe.get_cached_doc("Site", name)
	return get_installed_apps(site)


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
		app_source.commit_message = frappe.db.get_value(
			"App Release", {"hash": app_source.hash}, "message"
		)
		app_tags = frappe.db.get_value(
			"App Tag",
			{
				"repository": app_source.repository,
				"repository_owner": app_source.repository_owner,
				"hash": app_source.hash,
			},
			["tag", "timestamp"],
			as_dict=True,
		)
		app_source.update(app_tags if app_tags else {})
		app_source.subscription_available = bool(
			frappe.db.exists(
				"Marketplace App Plan", {"is_free": 0, "app": app.app, "enabled": 1}
			)
		)
		app_source.billing_type = is_prepaid_marketplace_app(app.app)
		if frappe.db.exists(
			"Marketplace App Subscription",
			{"site": site.name, "app": app.app, "status": "Active"},
		):
			subscription = frappe.get_doc(
				"Marketplace App Subscription",
				{"site": site.name, "app": app.app, "status": "Active"},
			)
			app_source.subscription = subscription
			marketplace_app_info = frappe.db.get_value(
				"Marketplace App", subscription.app, ["title", "image"], as_dict=True
			)

			app_source.app_title = marketplace_app_info.title
			app_source.app_image = marketplace_app_info.image

			app_source.plan_info = frappe.db.get_value(
				"Plan", subscription.plan, ["price_usd", "price_inr"], as_dict=True
			)

			app_source.is_free = frappe.db.get_value(
				"Marketplace App Plan", subscription.marketplace_app_plan, "is_free"
			)
		else:
			app_source.subscription = {}

		installed_apps.append(app_source)

	return installed_apps


def get_server_region_info(site) -> Dict:
	"""Return a Dict with `title` and `image`"""
	return frappe.db.get_value("Cluster", site.cluster, ["title", "image"], as_dict=True)


@frappe.whitelist()
@protected("Site")
def available_apps(name):
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
		frappe_version = frappe.db.get_value("Release Group", bench.group, "version")

		if is_marketplace_app_source(source.name):
			app_plans = get_plans_for_app(source.app, frappe_version)
			source.billing_type = is_prepaid_marketplace_app(source.app)
		else:
			app_plans = []

		if len(app_plans) > 0:
			source.has_plans_available = True
			source.plans = app_plans

		if source.app not in installed_apps:
			available_sources.append(source)

	return sorted(available_sources, key=lambda x: bench_sources.index(x.name))


def is_marketplace_app_source(app_source_name):
	return frappe.db.exists("Marketplace App Version", {"source": app_source_name})


def is_prepaid_marketplace_app(app):
	return (
		frappe.db.get_value("Saas Settings", app, "billing_type")
		if frappe.db.exists("Saas Settings", app)
		else "postpaid"
	)


@frappe.whitelist()
@protected("Site")
def current_plan(name):
	from press.api.analytics import get_current_cpu_usage

	site = frappe.get_doc("Site", name)
	plan = frappe.get_doc("Plan", site.plan) if site.plan else None

	result = get_current_cpu_usage(name)
	total_cpu_usage_hours = flt(result / (3.6 * (10**9)), 5)

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
		"database_access": plan.database_access if plan else None,
		"monitor_access": (
			is_system_user(frappe.session.user) or (plan.monitor_access if plan else None)
		),
		"usage_in_percent": {
			"cpu": site.current_cpu_usage,
			"disk": site.current_disk_usage,
			"database": site.current_database_usage,
		},
	}


@frappe.whitelist()
@protected("Site")
def change_plan(name, plan):
	frappe.get_doc("Site", name).set_plan(plan)


@frappe.whitelist()
@protected("Site")
def change_auto_update(name, auto_update_enabled):
	# Not so good, it should have been "enable_auto_updates"
	# TODO: Make just one checkbox to track auto updates
	return frappe.db.set_value("Site", name, "skip_auto_updates", not auto_update_enabled)


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
	return {"sid": frappe.get_doc("Site", name).login(reason), "site": name}


@frappe.whitelist()
@protected("Site")
def update(name, skip_failing_patches=False, skip_backups=False):
	return frappe.get_doc("Site", name).schedule_update(
		skip_failing_patches=skip_failing_patches, skip_backups=skip_backups
	)


@frappe.whitelist()
@protected("Site")
def last_migrate_failed(name):
	return frappe.get_doc("Site", name).last_migrate_failed()


@frappe.whitelist()
@protected("Site")
def backup(name, with_files=False):
	site_doc = frappe.get_doc("Site", name)
	if site_doc.status == "Suspended":
		activity = frappe.db.get_all(
			"Site Activity",
			filters={"site": name, "action": "Suspend Site"},
			order_by="creation desc",
			limit=1,
		)
		suspension_time = frappe.get_doc("Site Activity", activity[0]).creation

		if (
			frappe.db.count(
				"Site Backup",
				filters=dict(site=name, status="Success", creation=(">=", suspension_time)),
			)
			> 3
		):
			frappe.throw("You cannot take more than 3 backups after site suspension")

	frappe.get_doc("Site", name).backup(with_files)


@frappe.whitelist()
@protected("Site")
def archive(name, force):
	frappe.get_doc("Site", name).archive(force=force)


@frappe.whitelist()
@protected("Site")
def reinstall(name):
	return frappe.get_doc("Site", name).reinstall()


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
	return site.restore_site(skip_failing_patches=skip_failing_patches)


@frappe.whitelist()
def exists(subdomain, domain):
	from press.press.doctype.site.site import Site

	return Site.exists(subdomain, domain)


@frappe.whitelist()
@protected("Site")
def setup_wizard_complete(name):
	return frappe.get_doc("Site", name).is_setup_wizard_complete()


def check_dns_cname_a(name, domain):
	def check_dns_cname(name, domain):
		result = {"type": "CNAME", "matched": False, "answer": ""}
		try:
			resolver = Resolver(configure=False)
			resolver.nameservers = NAMESERVERS
			answer = resolver.query(domain, "CNAME")
			mapped_domain = answer[0].to_text().rsplit(".", 1)[0]
			result["answer"] = answer.rrset.to_text()
			if mapped_domain == name:
				result["matched"] = True
		except dns.exception.DNSException as e:
			result["answer"] = str(e)
		except Exception as e:
			result["answer"] = str(e)
			log_error("DNS Query Exception - CNAME", site=name, domain=domain, exception=e)
		finally:
			return result

	def check_dns_a(name, domain):
		result = {"type": "A", "matched": False, "answer": ""}
		try:
			resolver = Resolver(configure=False)
			resolver.nameservers = NAMESERVERS
			answer = resolver.query(domain, "A")
			domain_ip = answer[0].to_text()
			site_ip = resolver.query(name, "A")[0].to_text()
			result["answer"] = answer.rrset.to_text()
			if domain_ip == site_ip:
				result["matched"] = True
		except dns.exception.DNSException as e:
			result["answer"] = str(e)
		except Exception as e:
			result["answer"] = str(e)
			log_error("DNS Query Exception - A", site=name, domain=domain, exception=e)
		finally:
			return result

	cname = check_dns_cname(name, domain)
	result = {"CNAME": cname}
	result.update(cname)

	if result["matched"]:
		return result

	a = check_dns_a(name, domain)
	result.update({"A": a})
	result.update(a)

	return result


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
def install_app(name, app, plan=None):
	frappe.get_doc("Site", name).install_app(app, plan)


@frappe.whitelist()
@protected("Site")
def uninstall_app(name, app):
	frappe.get_doc("Site", name).uninstall_app(app)
	disable_marketplace_plan_if_exists(name, app)


def disable_marketplace_plan_if_exists(site_name, app_name):
	marketplace_app_name = frappe.db.get_value("Marketplace App", {"app": app_name})
	app_subscription = frappe.db.exists(
		"Marketplace App Subscription", {"site": site_name, "app": marketplace_app_name}
	)
	if marketplace_app_name and app_subscription:
		app_subscription = frappe.get_doc(
			"Marketplace App Subscription",
			app_subscription,
			for_update=True,
		)
		app_subscription.status = "Disabled"
		app_subscription.save(ignore_permissions=True)


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

	sanitized_config = []
	for c in config:
		if c.key in get_client_blacklisted_keys():
			continue
		if frappe.db.exists("Site Config Key", c.key):
			c.type = frappe.db.get_value("Site Config Key", c.key, "type")
		if c.type == "Number":
			c.value = flt(c.value)
		elif c.type == "Boolean":
			c.value = bool(c.value)
		elif c.type == "JSON":
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
			"Press Settings",
			"Press Settings",
			"remote_secret_access_key",
			raise_exception=False,
		),
		region_name="ap-south-1",
	)
	if action == "abort":
		response = s3_client.abort_multipart_upload(
			Bucket="uploads.frappe.cloud", Key=file, UploadId=id
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
	return frappe.get_doc("Site", name).get_auto_update_info()


@frappe.whitelist()
@protected("Site")
def update_auto_update_info(name, info=None):
	site_doc = frappe.get_doc("Site", name, for_update=True)
	site_doc.update(info or {})
	site_doc.save()


@frappe.whitelist()
@protected("Site")
def get_database_access_info(name):
	return frappe.get_doc("Site", name).get_database_access_info()


@frappe.whitelist()
@protected("Site")
def enable_database_access(name, mode="read_only"):
	site_doc = frappe.get_doc("Site", name)
	enable_access_job = site_doc.enable_database_access(mode)
	return enable_access_job.name


@frappe.whitelist()
@protected("Site")
def disable_database_access(name):
	site_doc = frappe.get_doc("Site", name)
	disable_access_job = site_doc.disable_database_access()
	return disable_access_job.name


@frappe.whitelist()
def get_job_status(job_name):
	return {"status": frappe.db.get_value("Agent Job", job_name, "status")}


@frappe.whitelist()
@protected("Site")
def change_notify_email(name, email):
	site_doc = frappe.get_doc("Site", name)
	site_doc.notify_email = email
	site_doc.save(ignore_permissions=True)


@frappe.whitelist()
@protected("Site")
def change_team(team, name):

	if not (
		frappe.db.exists("Team", {"team_title": team})
		and frappe.db.get_value("Team", {"team_title": team}, "enabled", 1)
	):
		frappe.throw("No Active Team record found.")

	from press.press.doctype.team.team import get_child_team_members

	current_team = get_current_team(True)
	child_teams = [team.team_title for team in get_child_team_members(current_team.name)]
	teams = [current_team.team_title] + child_teams

	if team not in teams:
		frappe.throw(f"{team} is not part of your organization.")

	child_team = frappe.get_doc("Team", {"team_title": team})
	site_doc = frappe.get_doc("Site", name)
	site_doc.team = child_team.name
	site_doc.save(ignore_permissions=True)


@frappe.whitelist()
@protected("Site")
def change_group_options(name):
	team = get_current_team()
	group, server = frappe.db.get_value("Site", name, ["group", "server"])

	version = frappe.db.get_value("Release Group", group, "version")
	benches = frappe.qb.DocType("Bench")
	groups = frappe.qb.DocType("Release Group")
	benches = (
		frappe.qb.from_(benches)
		.select(benches.group.as_("name"), groups.title)
		.inner_join(groups)
		.on(groups.name == benches.group)
		.where(benches.status == "Active")
		.where(groups.name != group)
		.where(groups.version == version)
		.where(groups.team == team)
		.where(benches.server == server)
		.groupby(benches.group)
	).run(as_dict=True)

	return benches


@frappe.whitelist()
@protected("Site")
def change_group(name, group):
	team = frappe.db.get_value("Release Group", group, "team")
	if team != get_current_team():
		frappe.throw(f"Bench {group} does not belong to your team")

	frappe.get_doc(
		{
			"doctype": "Site Update",
			"site": name,
			"destination_group": group,
		}
	).insert()


@frappe.whitelist()
@protected("Site")
def change_region_options(name):
	group, cluster = frappe.db.get_value("Site", name, ["group", "cluster"])

	ReleaseGroupServer = frappe.qb.DocType("Release Group Server")
	Server = frappe.qb.DocType("Server")
	Cluster = frappe.qb.DocType("Cluster")
	query = (
		frappe.qb.from_(ReleaseGroupServer)
		.join(Server)
		.on(Server.name == ReleaseGroupServer.server)
		.join(Cluster)
		.on(Cluster.name == Server.cluster)
		.select(Cluster.name, Cluster.title, Cluster.image)
		.distinct()
		.where(ReleaseGroupServer.parent == group)
		.where(ReleaseGroupServer.parenttype == "Release Group")
	)

	return {"regions": query.run(as_dict=True), "current_region": cluster}


@frappe.whitelist()
@protected("Site")
def change_region(name, cluster, scheduled_datetime=None):
	group = frappe.db.get_value("Site", name, "group")
	bench_vals = frappe.db.get_value(
		"Bench", {"group": group, "cluster": cluster}, ["name", "server"]
	)

	if bench_vals is None:
		frappe.throw(f"Bench {group} does not have an existing deploy in {cluster}")

	bench, server = bench_vals

	site_migration = frappe.get_doc(
		{
			"doctype": "Site Migration",
			"site": name,
			"destination_group": group,
			"destination_bench": bench,
			"destination_server": server,
			"destination_cluster": cluster,
			"scheduled_time": scheduled_datetime,
		}
	).insert()

	if not scheduled_datetime:
		site_migration.start()


@frappe.whitelist()
@protected("Site")
def get_private_groups_for_upgrade(name, version):
	team = get_current_team()
	server = frappe.db.get_value("Site", name, "server")

	ReleaseGroup = frappe.qb.DocType("Release Group")
	ReleaseGroupServer = frappe.qb.DocType("Release Group Server")

	private_groups = (
		frappe.qb.from_(ReleaseGroup)
		.select(ReleaseGroup.name, ReleaseGroup.title)
		.join(ReleaseGroupServer)
		.on(ReleaseGroupServer.parent == ReleaseGroup.name)
		.where(ReleaseGroup.enabled == 1)
		.where(ReleaseGroupServer.server == server)
		.where(ReleaseGroup.team == team)
		.where(ReleaseGroup.public == 0)
		.where(ReleaseGroup.version > version)
	).run(as_dict=True)

	return private_groups


@frappe.whitelist()
@protected("Site")
def version_upgrade(name, destination_group, scheduled_datetime=None):
	site = frappe.get_doc("Site", name)
	current_version, shared_site = frappe.db.get_value(
		"Release Group", site.group, ["version", "public"]
	)
	next_version = f"Version {int(current_version.split(' ')[1]) + 1}"

	if shared_site:
		destination_group = frappe.db.get_value(
			"Release Group", {"version": next_version, "public": 1}, "name"
		)

	if not destination_group:
		frappe.throw(f"There are no benches with {next_version}.")

	version_upgrade = frappe.get_doc(
		{
			"doctype": "Version Upgrade",
			"site": name,
			"destination_group": destination_group,
			"scheduled_time": scheduled_datetime,
		}
	).insert()

	if not scheduled_datetime:
		version_upgrade.start()


@frappe.whitelist()
@protected("Site")
def change_server_options(name):
	site_server = frappe.db.get_value("Site", name, "server")
	return frappe.db.get_all(
		"Server",
		{"team": get_current_team(), "status": "Active", "name": ("!=", site_server)},
		["name", "title"],
	)


@frappe.whitelist()
@protected("Site")
def change_server_bench_options(name, server):
	site_group, site_bench = frappe.db.get_value("Site", name, ["group", "bench"])
	site_candidate = frappe.db.get_value("Bench", site_bench, "candidate")
	site_version = frappe.db.get_value("Release Group", site_group, "version")
	team = get_current_team()

	Bench = frappe.qb.DocType("Bench")
	ReleaseGroup = frappe.qb.DocType("Release Group")
	rg = (
		frappe.qb.from_(Bench)
		.select(ReleaseGroup.name, ReleaseGroup.title)
		.join(ReleaseGroup)
		.on(ReleaseGroup.name == Bench.group)
		.where(Bench.server == server)
		.where(Bench.status == "Active")
		.where(ReleaseGroup.team == team)
		.where(Bench.candidate >= site_candidate)
		.where(ReleaseGroup.version == site_version)
		.distinct()
	).run(as_dict=True)

	if not rg:
		frappe.throw(
			f"There are no benches with <b>{site_version}</b> in server <b>{server}</b>."
		)

	return rg


@frappe.whitelist()
@protected("Site")
def change_server(name, group, scheduled_datetime=None):
	bench = frappe.db.get_value("Bench", {"group": group, "status": "Active"}, "name")

	site_migration = frappe.get_doc(
		{
			"doctype": "Site Migration",
			"site": name,
			"destination_bench": bench,
			"scheduled_time": scheduled_datetime,
		}
	).insert()

	if not scheduled_datetime:
		site_migration.start()
