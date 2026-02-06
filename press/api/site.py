# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import frappe
import requests
import wrapt
from boto3 import client
from botocore.exceptions import ClientError
from frappe.core.utils import find
from frappe.desk.doctype.tag.tag import add_tag
from frappe.query_builder import Case
from frappe.rate_limiter import rate_limit
from frappe.utils import flt, sbool, time_diff_in_hours
from frappe.utils.password import get_decrypted_password
from frappe.utils.typing_validations import validate_argument_types
from frappe.utils.user import is_system_user

from press.access.support_access import has_support_access
from press.guards import role_guard
from press.press.doctype.agent_job.agent_job import job_detail
from press.press.doctype.marketplace_app.marketplace_app import (
	get_plans_for_app,
	get_total_installs_by_app,
)
from press.press.doctype.remote_file.remote_file import get_remote_key
from press.press.doctype.server.server import is_dedicated_server
from press.press.doctype.site.site import Site, get_updates_between_current_and_next_apps
from press.press.doctype.site_plan.plan import Plan
from press.press.doctype.site_update.site_update import benches_with_available_update
from press.utils import (
	get_client_blacklisted_keys,
	get_current_team,
	get_frappe_backups,
	get_last_doc,
	log_error,
	unique,
)
from press.utils.dns import check_dns_cname_a

if TYPE_CHECKING:
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.press.doctype.server.server import Server
	from press.press.doctype.team.team import Team


def protected(doctypes):
	"""
	This decorator is stupid. It works in magical ways. It checks whether the
	owner of the Doctype (one of `doctypes`) is the same as the current team.

	The stupid magical part of this decorator is how it gets the name of the
	Doctype (see: `get_protected_doctype_name`); in order of precedence:
	1. kwargs value with key `name`
	2. first value in kwargs value with key `filters` i.e. ≈ `kwargs['filters'].values()[0]`
	3. first value in the args tuple
	4. kwargs value with key `snake_case(doctypes[0])`
	"""

	if not isinstance(doctypes, list):
		doctypes = [doctypes]

	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		user_type = frappe.session.data.user_type or frappe.get_cached_value(
			"User", frappe.session.user, "user_type"
		)

		# System users have access to all endpoints.
		if user_type == "System User":
			return wrapped(*args, **kwargs)

		# Get the name of the document being accessed.
		if not (docname := get_protected_doctype_name(args, kwargs, doctypes)):
			frappe.throw("Name not found, API access not permitted", frappe.PermissionError)

		current_team = get_current_team()
		for doctype in doctypes:
			document_team = frappe.db.get_value(doctype, docname, "team")
			if document_team == current_team or has_support_access(doctype, docname):
				return wrapped(*args, **kwargs)

		frappe.throw("Not Permitted", frappe.PermissionError)
		return None

	return wrapper


def get_protected_doctype_name(args: list, kwargs: dict, doctypes: list[str]):
	# 1. Name from kwargs["name"] or kwargs["doc_name"]
	if name := (kwargs.get("name") or kwargs.get("doc_name")):
		return name

	# 2. Name from first value in filters
	filters = kwargs.get("filters", {})
	if name := get_name_from_filters(filters):
		return name

	#  3. Name from first value in args
	if len(args) >= 1 and args[0]:
		return args[0]

	if len(doctypes) == 0:
		return None

	# 4. Name from snakecased first `doctypes` name
	doctype = doctypes[0]
	key = doctype.lower().replace(" ", "_")
	return kwargs.get(key)


def get_name_from_filters(filters: dict):
	values = [v for v in filters.values()]
	if len(values) == 0:
		return None

	value = values[0]
	if isinstance(value, (int, str)):
		return value

	return None


def _new(site, server: str | None = None, ignore_plan_validation: bool = False):
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new site because your account is disabled")

	files = site.get("files", {})

	apps = [{"app": app} for app in site["apps"]]

	group = get_group_for_new_site_and_set_localisation_app(site, apps)
	domain = site.get("domain")
	if not (domain and frappe.db.exists("Root Domain", {"name": domain})):
		frappe.throw("No root domain for site")

	cluster = site.get("cluster") or frappe.db.get_single_value("Press Settings", "cluster")

	Bench = frappe.qb.DocType("Bench")
	Server = frappe.qb.DocType("Server")
	ProxyServer = frappe.qb.DocType("Proxy Server")
	ProxyServerDomain = frappe.qb.DocType("Proxy Server Domain")

	proxy_servers = (
		frappe.qb.from_(ProxyServer)
		.join(ProxyServerDomain)
		.on(ProxyServer.name == ProxyServerDomain.parent)
		.select(ProxyServer.name)
		.where(ProxyServerDomain.domain == domain)
		.where(ProxyServer.status == "Active")
	).run(as_dict=True)
	proxy_servers = [d.name for d in proxy_servers]

	bench_query = (
		frappe.qb.from_(Bench)
		.join(Server)
		.on(Bench.server == Server.name)
		.select(Bench.name, Bench.server)
		.where(Server.proxy_server.isin(proxy_servers))
		.where(Bench.status == "Active")
		.where(Bench.group == site["group"])
		.orderby(Case().when(Bench.cluster == cluster, 1).else_(0), order=frappe.qb.desc)
		.orderby(Server.use_for_new_sites, order=frappe.qb.desc)
		.orderby(Bench.creation, order=frappe.qb.desc)
		.limit(1)
	)

	if server:
		bench_query = bench_query.where(Server.name == server)

	bench = bench_query.run(as_dict=True).pop()

	plan = site["plan"]
	app_plans = site.get("selected_app_plans")
	if not ignore_plan_validation:
		validate_plan(bench.server, plan)

	site = frappe.get_doc(
		{
			"doctype": "Site",
			"subdomain": site["name"],
			"domain": domain,
			"group": group,
			"server": server,
			"cluster": cluster,
			"apps": apps,
			"app_plans": app_plans,
			"team": team.name,
			"free": team.free_account,
			"subscription_plan": plan,
			"version": site.get("version"),
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
		secret_keys = {f"sk_{s.document_name}": s.secret_key for s in subscription_docs}
		site._update_configuration(secret_keys, save=False)

	site.insert(ignore_permissions=True)

	if app_plans and len(app_plans) > 0:
		# Set site in subscription docs
		for doc in subscription_docs:
			doc.site = site.name
			doc.save(ignore_permissions=True)

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


def get_group_for_new_site_and_set_localisation_app(site, apps):
	if not (localisation_country := site.get("localisation_country")):
		return site.get("group")

	# if localisation country is selected, move site to a public bench with the same localisation app
	localisation_app = frappe.db.get_value(
		"Marketplace Localisation App", {"country": localisation_country}, "marketplace_app"
	)
	restricted_release_group_names = frappe.db.get_all(
		"Site Plan Release Group",
		pluck="release_group",
		filters={"parenttype": "Site Plan", "parentfield": "release_groups"},
	)
	ReleaseGroup = frappe.qb.DocType("Release Group")
	ReleaseGroupApp = frappe.qb.DocType("Release Group App")
	groups = (
		frappe.qb.from_(ReleaseGroup)
		.select(ReleaseGroup.name)
		.join(ReleaseGroupApp)
		.on(ReleaseGroup.name == ReleaseGroupApp.parent)
		.where(ReleaseGroupApp.app == localisation_app)
		.where(ReleaseGroup.public == 1)
		.where(ReleaseGroup.enabled == 1)
		.where(ReleaseGroup.name.notin(restricted_release_group_names or [""]))
		.where(ReleaseGroup.version == site.get("version"))
		.run(pluck="name")
	)
	if not groups:
		frappe.throw(
			f"Localisation app for {frappe.bold(localisation_country)} is not available for version {frappe.bold(site.get('version'))}"
		)

	apps.append({"app": localisation_app})
	return groups[0]


@validate_argument_types
def validate_plan(server: str, plan: str) -> None:
	if not frappe.db.exists("Site Plan", plan):
		frappe.throw(f"Plan {plan} does not exist", frappe.DoesNotExistError)
	if (
		frappe.db.get_value("Site Plan", plan, "price_usd") > 0
		or frappe.db.get_value("Site Plan", plan, "dedicated_server_plan") == 1
	):
		return
	if (
		frappe.session.data.user_type == "System User"
		or frappe.db.get_value("Server", server, "team") == get_current_team()
	):
		return
	frappe.throw("You are not allowed to use this plan")


@frappe.whitelist()
def new(site):
	if not hasattr(site, "domain") and not site.get("domain"):
		site["domain"] = frappe.db.get_single_value("Press Settings", "domain")

	plan = site.get("plan")
	if frappe.db.get_value("Site Plan", plan, "private_bench_support"):
		return create_site_on_private_bench(
			subdomain=site.get("name"),
			plan=plan,
			cluster=site.get("cluster"),
			apps=site.get("apps", ["frappe"]),
			version=site.get("version"),
			provider=site.get("provider"),
			localisation_country=site.get("localisation_country"),
		)

	return _new(site)


def create_site_on_private_bench(
	subdomain: str,
	plan: str,
	cluster: str,
	apps: list[str],
	version: str,
	provider: str,
	localisation_country: str | None = None,
) -> dict:
	team = get_current_team()

	if localisation_country:
		localisation_app = frappe.db.get_value(
			"Marketplace Localisation App", {"country": localisation_country}, "marketplace_app"
		)
		if localisation_app:
			apps.append(localisation_app)

	app_names = [app for app in apps if app != "frappe"]

	AppSource = frappe.qb.DocType("App Source")
	AppSourceVersion = frappe.qb.DocType("App Source Version")
	frappe_app_source = (
		frappe.qb.from_(AppSource)
		.left_join(AppSourceVersion)
		.on(AppSource.name == AppSourceVersion.parent)
		.select(AppSource.name.as_("source"), AppSource.app, AppSourceVersion.version)
		.where(AppSource.app == "frappe")
		.where(AppSource.public == 1)
		.where(AppSourceVersion.version == version)
		.run(as_dict=True)
	)

	if app_names:
		MarketplaceApp = frappe.qb.DocType("Marketplace App")
		MarketplaceAppVersion = frappe.qb.DocType("Marketplace App Version")
		app_sources = (
			frappe.qb.from_(MarketplaceApp)
			.left_join(MarketplaceAppVersion)
			.on(MarketplaceApp.name == MarketplaceAppVersion.parent)
			.select(
				MarketplaceApp.name.as_("app"),
				MarketplaceAppVersion.source,
			)
			.where(MarketplaceApp.name.isin(app_names))
			.where(MarketplaceAppVersion.version == version)
			.orderby(MarketplaceAppVersion.version, order=frappe.qb.desc)
			.run(as_dict=True)
		)
	else:
		app_sources = []

	apps_with_sources = []
	sources = {x.app: x.source for x in frappe_app_source + app_sources}
	for app in apps:
		if app not in sources:
			frappe.throw(f"Source not found for app {app}")

		apps_with_sources.append({"app": app, "source": sources[app]})

	# Create Site Group Deploy with auto_provision_bench flag
	site_group_deploy = frappe.get_doc(
		{
			"doctype": "Site Group Deploy",
			"auto_provision_bench": 1,
			"site_plan": plan,
			"subdomain": subdomain,
			"apps": apps_with_sources,
			"cluster": cluster,
			"version": version,
			"team": team,
			"provider": provider,
		}
	).insert(ignore_permissions=True)

	return {
		"site_group_deploy": site_group_deploy.name,
	}


def get_app_subscriptions(app_plans, team_name: str):
	subscriptions = []
	team: Team | None = None

	for app_name, plan_name in app_plans.items():
		is_free = frappe.db.get_value("Marketplace App Plan", plan_name, "is_free")
		if not is_free:
			if not team:
				team = frappe.get_doc("Team", team_name)
			if not team.can_install_paid_apps():
				frappe.throw(
					"You cannot install a Paid app on Free Credits. Please buy credits before trying to install again."
				)

		new_subscription = frappe.get_doc(
			{
				"doctype": "Subscription",
				"document_type": "Marketplace App",
				"document_name": app_name,
				"plan_type": "Marketplace App Plan",
				"plan": plan_name,
				"enabled": 1,
				"team": team_name,
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

	for job in jobs:
		job["status"] = "Pending" if job["status"] == "Undelivered" else job["status"]

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

	if job.status == "Undelivered":
		job.status = "Pending"

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
	jobs = frappe.get_all("Agent Job", filters={"status": ("in", ("Pending", "Running")), "site": name})
	return [job_detail(job.name) for job in jobs]


@frappe.whitelist()
@protected("Site")
def backups(name):
	available_offsite_backups = frappe.db.get_single_value("Press Settings", "offsite_backups_count") or 30
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
	return sorted(latest_backups + offsite_backups, key=lambda x: x["creation"], reverse=True)


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
		.select(SiteActivity.action, SiteActivity.reason, SiteActivity.creation, SiteActivity.owner)
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
def app_details_for_new_public_site():
	fields = [
		"name",
		"title",
		"image",
		"description",
		"app",
		"route",
		"subscription_type",
		{"sources": ["source", "version"]},
		{"localisation_apps": ["marketplace_app", "country"]},
	]

	marketplace_apps = frappe.qb.get_query(
		"Marketplace App",
		fields=fields,
		filters={"status": "Published", "show_for_site_creation": 1},
	).run(as_dict=True)

	marketplace_app_sources = [app["sources"][0]["source"] for app in marketplace_apps if app["sources"]]

	if not marketplace_app_sources:
		return []

	AppSource = frappe.qb.DocType("App Source")
	MarketplaceApp = frappe.qb.DocType("Marketplace App")
	app_source_details = (
		frappe.qb.from_(AppSource)
		.select(
			AppSource.name,
			AppSource.app,
			AppSource.repository_url,
			AppSource.repository,
			AppSource.repository_owner,
			AppSource.branch,
			AppSource.team,
			AppSource.public,
			MarketplaceApp.title.as_("app_title"),
			AppSource.frappe,
		)
		.join(MarketplaceApp)
		.on(AppSource.app == MarketplaceApp.app)
		.where(AppSource.name.isin(marketplace_app_sources))
		.run(as_dict=True)
	)

	total_installs_by_app = get_total_installs_by_app()
	for app in marketplace_apps:
		app["plans"] = get_plans_for_app(app.app)
		app["total_installs"] = total_installs_by_app.get(app.app, 0)
		source_detail = find(app_source_details, lambda x: x.app == app.app)
		if source_detail:
			app.update({**source_detail})

	return marketplace_apps


def get_dedicated_server_info(release_group_name: str) -> dict:
	"""
	check servers linked to a release group and determine dedicated server deployment options.

	Returns dict with:
	- case: str - one of:
		- "dedicated_only_single" - exactly one dedicated server
		- "dedicated_only_multiple" - multiple dedicated servers
		- "user_choice_single" - one dedicated server and other public server(s)
		"user_choice_multiple" - multiple dedicated servers and public server(s)
		- "no_dedicated_server"
	- dedicated_servers: list - Available dedicated servers for user selection
	"""
	current_team = get_current_team()

	linked_servers = frappe.db.get_all(
		"Release Group Server",
		filters={"parent": release_group_name, "parenttype": "Release Group"},
		pluck="server",
	)

	if not linked_servers:
		return {
			"case": "no_dedicated_server",
			"dedicated_servers": [],
		}

	servers = frappe.db.get_all(
		"Server",
		filters={"name": ("in", linked_servers), "status": "Active"},
		fields=["name", "title", "public", "team", "cluster", "provider"],
	)
	public_servers = [s for s in servers if s.public]
	team_private_servers = [s for s in servers if not s.public and s.team == current_team]

	num_private = len(team_private_servers)
	has_public_server = bool(public_servers)

	if has_public_server:
		if num_private == 1:
			return {
				"case": "user_choice_single",
				"dedicated_servers": team_private_servers,
			}
		if num_private > 1:
			return {
				"case": "user_choice_multiple",
				"dedicated_servers": team_private_servers,
			}
	else:
		if num_private == 1:
			return {
				"case": "dedicated_only_single",
				"dedicated_servers": team_private_servers,
			}
		if num_private > 1:
			return {
				"case": "dedicated_only_multiple",
				"dedicated_servers": team_private_servers,
			}

	return {
		"case": "no_dedicated_server",
		"dedicated_servers": [],
	}


@frappe.whitelist()
def options_for_new(for_bench: str | None = None):  # noqa: C901
	from press.press.doctype.cloud_provider.cloud_provider import get_cloud_providers
	from press.utils import get_nearest_cluster

	available_versions = get_available_versions(for_bench)

	unique_app_sources = []
	for version in available_versions:
		for app_source in version.group.bench_app_sources:
			if app_source not in unique_app_sources:
				unique_app_sources.append(app_source)

	if for_bench:
		app_source_details = frappe.db.get_all(
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
			filters={"name": ("in", unique_app_sources)},
		)

		unique_apps = []
		app_source_details_grouped = {}
		for app_source in app_source_details:
			if app_source.app not in unique_apps:
				unique_apps.append(app_source.app)
			app_source_details_grouped[app_source.name] = app_source

		marketplace_apps = frappe.db.get_all(
			"Marketplace App",
			fields=["title", "image", "description", "app", "route", "subscription_type"],
			filters={"app": ("in", unique_apps)},
		)
		total_installs_by_app = get_total_installs_by_app()
		marketplace_details = {}

		for app in unique_apps:
			details = find(marketplace_apps, lambda x: x.app == app)
			if details:
				details["plans"] = get_plans_for_app(app)
				details["total_installs"] = total_installs_by_app.get(app, 0)
				marketplace_details[app] = details

		set_default_apps(app_source_details_grouped)
	else:
		app_source_details_grouped = app_details_for_new_public_site()
		# app source details are all fetched from marketplace apps for public sites
		marketplace_details = None

	default_domain = frappe.db.get_single_value("Press Settings", "domain")
	cluster_specific_root_domains = frappe.db.get_all(
		"Root Domain",
		{"name": ("like", f"%.{default_domain}")},
		["name", "default_cluster as cluster"],
	)

	# providers list from all clusters across versions
	unique_providers = {}
	cloud_providers = get_cloud_providers()
	existing_clusters = set()

	for version in available_versions:
		for cluster in version.group.clusters or []:
			existing_clusters.add(cluster.get("name"))
			provider_name = cluster.get("cloud_provider")
			if provider_name and provider_name in cloud_providers and provider_name not in unique_providers:
				provider_info = cloud_providers.get(provider_name, {})
				unique_providers[provider_name] = {
					"name": provider_name,
					"title": provider_info.get("title", provider_name),
					"image": provider_info.get("image"),
				}

	# Get additional clusters with active servers for deploying sites on private benches
	private_bench_clusters = []
	if not for_bench:
		private_bench_clusters = get_additional_clusters_for_private_benches(
			existing_clusters, cloud_providers, unique_providers
		)

	return {
		"versions": available_versions,
		"domain": default_domain,
		"closest_cluster": get_nearest_cluster(),
		"cluster_specific_root_domains": cluster_specific_root_domains,
		"marketplace_details": marketplace_details,
		"app_source_details": app_source_details_grouped,
		"providers": list(unique_providers.values()),
		"additional_clusters": private_bench_clusters,
	}


def set_default_apps(app_source_details_grouped):
	press_settings = frappe.get_single("Press Settings")
	default_apps = press_settings.get_default_apps()

	for app_source in app_source_details_grouped.values():
		if app_source["app"] in default_apps:
			app_source["preinstalled"] = True


def get_available_versions(for_bench: str | None = None):
	available_versions = []
	restricted_release_group_names = get_restricted_release_group_names()
	filters: dict[str, int | bool | tuple] = {}
	release_group_filters: dict[str, int | str | bool | tuple] = {}

	if for_bench:
		version = frappe.db.get_value("Release Group", for_bench, "version")
		filters = {"name": version}

		release_group_filters = {"name": for_bench}
	else:
		filters = {"public": True, "status": ("!=", "End of Life")}
		release_group_filters = {
			"public": 1,
			"enabled": 1,
			"saas_bench": 0,
			"name": (
				"not in",
				restricted_release_group_names,
			),  # filter out restricted release groups
		}

	versions = frappe.db.get_all(
		"Frappe Version",
		["name", "default", "status", "number"],
		filters,
		order_by="number desc",
	)

	for version in versions:
		release_group_filters["version"] = version.name
		release_group = frappe.db.get_value(
			"Release Group",
			fieldname=["name", "`default`", "title", "public"],
			filters=release_group_filters,
			order_by="creation desc",
			as_dict=1,
		)

		if release_group:
			version.group = release_group
			if for_bench:
				version.group.dedicated_server_config = get_dedicated_server_info(release_group.name) or {}

			set_bench_and_clusters(version, for_bench)

			if version.group and version.group.bench and version.group.clusters:
				available_versions.append(version)

	return available_versions


def get_restricted_release_group_names():
	return frappe.db.get_all(
		"Site Plan Release Group",
		pluck="release_group",
		filters={"parenttype": "Site Plan", "parentfield": "release_groups"},
	)


def set_bench_and_clusters(version, for_bench):
	# here we get the last created bench for the release group
	# assuming the last created bench is the latest one
	bench = frappe.db.get_value(
		"Bench",
		filters={"status": "Active", "group": version.group.name},
		order_by="creation desc",
	)
	if bench:
		version.group.bench = bench
		version.group.bench_app_sources = frappe.db.get_all(
			"Bench App", {"parent": bench, "app": ("!=", "frappe")}, pluck="source"
		)
		cluster_names = unique(
			frappe.db.get_all(
				"Bench",
				filters={"candidate": frappe.db.get_value("Bench", bench, "candidate")},
				pluck="cluster",
			)
		)

		allowed_cluster_names: list[str] = []
		if for_bench:
			current_team = get_current_team()
			release_group_servers = frappe.db.get_all(
				"Release Group Server",
				filters={"parent": version.group.name, "parenttype": "Release Group"},
				pluck="server",
			)

			if release_group_servers:
				server_clusters = frappe.db.get_all(
					"Server",
					filters={
						"status": "Active",
						"name": ("in", release_group_servers),
						"cluster": ("in", cluster_names),
					},
					or_filters={
						"public": 1,
						"team": current_team,
					},
					pluck="cluster",
				)
				allowed_cluster_names = list(set(server_clusters))
		else:
			public_servers_clusters = frappe.db.get_all(
				"Server",
				filters={
					"status": "Active",
					"public": 1,
					"cluster": ("in", cluster_names),
				},
				pluck="cluster",
			)
			allowed_cluster_names = list(set(public_servers_clusters))

		clusters = frappe.db.get_all(
			"Cluster",
			filters={"name": ("in", allowed_cluster_names)},
			fields=["name", "title", "image", "beta", "cloud_provider"],
		)
		if not for_bench:
			proxy_servers = frappe.db.get_all(
				"Proxy Server",
				{
					"cluster": ("in", allowed_cluster_names),
					"is_primary": 1,
				},
				["name", "cluster"],
			)

			for cluster in clusters:
				cluster.proxy_server = find(proxy_servers, lambda x: x.cluster == cluster.name)

		version.group.clusters = clusters


def get_additional_clusters_for_private_benches(existing_clusters, cloud_providers, unique_providers):
	"""
	Fetch clusters from active public servers that are not already in existing_clusters(from benches linked to public release groups) and have a provider that's enabled in at least Site Plan with Private Bench enabled
	"""
	private_bench_site_plans_providers = frappe.db.get_all(
		"Site Plan",
		filters={"private_bench_support": 1, "enabled": 1, "dedicated_server_plan": 0},
		pluck="name",
	)

	if not private_bench_site_plans_providers:
		return []

	allowed_providers = frappe.db.get_all(
		"Cloud Providers",
		filters={"parent": ("in", private_bench_site_plans_providers)},
		pluck="cloud_provider",
	)

	if not allowed_providers:
		return []

	servers_from_allowed_providers = frappe.db.get_all(
		"Server",
		filters={
			"status": "Active",
			"public": 1,
			"provider": ("in", allowed_providers),
		},
		fields=["cluster", "provider"],
	)

	additional_clusters = []
	seen_clusters = set()
	for server in servers_from_allowed_providers:
		cluster_name = server.get("cluster")
		if cluster_name in existing_clusters or cluster_name in seen_clusters:
			continue

		provider_name = server.get("provider")

		cluster_info = frappe.db.get_value(
			"Cluster",
			cluster_name,
			["name", "title", "image", "beta", "cloud_provider"],
			as_dict=True,
		)

		if cluster_info:
			additional_clusters.append(cluster_info)
			seen_clusters.add(cluster_name)

			if provider_name and provider_name in cloud_providers and provider_name not in unique_providers:
				provider_info = cloud_providers.get(provider_name, {})
				unique_providers[provider_name] = {
					"name": provider_name,
					"title": provider_info.get("title", provider_name),
					"image": provider_info.get("image"),
				}

	return additional_clusters


@frappe.whitelist()
def get_domain():
	return frappe.db.get_value("Press Settings", "Press Settings", ["domain"])


@frappe.whitelist()
def get_new_site_options(group: str | None = None):
	team = get_current_team()
	apps = set()
	filters: dict[str, bool | str] = {"enabled": True}
	versions_filters: dict[str, tuple | str | bool] = {"public": True}

	if group:  # private bench
		filters.update({"name": group, "team": team})
	else:
		filters.update({"public": True})
		versions_filters.update({"status": ("!=", "End of Life")})

	versions = frappe.get_all(
		"Frappe Version",
		["name", "number", "default", "status"],
		filters=versions_filters,
		order_by="`default` desc, number desc",
	)

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
			fields=["name", "title", "image", "beta"],
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
def get_site_plans():
	plans = Plan.get_plans(
		doctype="Site Plan",
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
			"offsite_backups",
			"private_benches",
			"monitor_access",
			"dedicated_server_plan",
			"is_trial_plan",
			"allow_downgrading_from_other_plan",
			"private_bench_support",
		],
		# TODO: Remove later, temporary change because site plan has all document_type plans
		filters={"document_type": "Site"},
	)

	# Fetch cloud_providers for each plan
	for plan in plans:
		plan.cloud_providers = frappe.get_all(
			"Cloud Providers",
			filters={"parent": plan.name},
			fields=["cloud_provider"],
			pluck="cloud_provider",
		)

	plan_names = [x.name for x in plans]
	if len(plan_names) == 0:
		return []

	filtered_plans = []

	SitePlan = frappe.qb.DocType("Site Plan")
	Bench = frappe.qb.DocType("Bench")
	ReleaseGroup = frappe.qb.DocType("Release Group")
	SitePlanReleaseGroup = frappe.qb.DocType("Site Plan Release Group")
	SitePlanAllowedApp = frappe.qb.DocType("Site Plan Allowed App")

	plan_details_query = (
		frappe.qb.from_(SitePlan)
		.select(SitePlan.name, SitePlanReleaseGroup.release_group, SitePlanAllowedApp.app)
		.left_join(SitePlanReleaseGroup)
		.on(SitePlanReleaseGroup.parent == SitePlan.name)
		.left_join(SitePlanAllowedApp)
		.on(SitePlanAllowedApp.parent == SitePlan.name)
		.where(SitePlan.name.isin(plan_names))
	)

	plan_details_with_bench_query = (
		frappe.qb.from_(plan_details_query)
		.select(
			plan_details_query.name,
			plan_details_query.release_group,
			plan_details_query.app,
			Bench.cluster,
			ReleaseGroup.version,
		)
		.left_join(Bench)
		.on(Bench.group == plan_details_query.release_group)
		.left_join(ReleaseGroup)
		.on(ReleaseGroup.name == plan_details_query.release_group)
		.where(Bench.status == "Active")
	)

	plan_details = plan_details_with_bench_query.run(as_dict=True)
	plan_details_dict = get_plan_details_dict(plan_details)

	for plan in plans:
		if plan.name in plan_details_dict:
			plan.clusters = plan_details_dict[plan.name]["clusters"]
			plan.allowed_apps = plan_details_dict[plan.name]["allowed_apps"]
			plan.bench_versions = plan_details_dict[plan.name]["bench_versions"]
			plan.restricted_plan = True
		else:
			plan.clusters = []
			plan.allowed_apps = []
			plan.bench_versions = []
			plan.restricted_plan = False
		filtered_plans.append(plan)

	return filtered_plans


def get_plan_details_dict(plan_details):
	plan_details_dict = {}

	for plan in plan_details:
		if plan["name"] not in plan_details_dict:
			plan_details_dict[plan["name"]] = {
				"allowed_apps": [],
				"release_groups": [],
				"clusters": [],
				"bench_versions": [],
			}
		if (
			plan["release_group"]
			and plan["release_group"] not in plan_details_dict[plan["name"]]["release_groups"]
		):
			plan_details_dict[plan["name"]]["release_groups"].append(plan["release_group"])
		if plan["app"] and plan["app"] not in plan_details_dict[plan["name"]]["allowed_apps"]:
			plan_details_dict[plan["name"]]["allowed_apps"].append(plan["app"])
		if plan["cluster"] and plan["cluster"] not in plan_details_dict[plan["name"]]["clusters"]:
			plan_details_dict[plan["name"]]["clusters"].append(plan["cluster"])
		if plan["version"] and plan["version"] not in plan_details_dict[plan["name"]]["bench_versions"]:
			plan_details_dict[plan["name"]]["bench_versions"].append(plan["version"])
	return plan_details_dict


@frappe.whitelist()
def get_plans(name=None, rg=None):
	site_name = name
	plans = Plan.get_plans(
		doctype="Site Plan",
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
			"offsite_backups",
			"private_benches",
			"monitor_access",
			"dedicated_server_plan",
			"allow_downgrading_from_other_plan",
		],
		# TODO: Remove later, temporary change because site plan has all document_type plans
		filters={"document_type": "Site"},
	)

	if site_name or rg:
		team = get_current_team()
		release_group_name = rg if rg else frappe.db.get_value("Site", site_name, "group")
		release_group = frappe.get_doc("Release Group", release_group_name)
		is_private_bench = release_group.team == team and not release_group.public
		is_system_user = frappe.db.get_value("User", frappe.session.user, "user_type") == "System User"
		# poor man's bench paywall
		# this will not allow creation of $10 sites on private benches
		# wanted to avoid adding a new field, so doing this with a date check :)
		# TODO: find a better way to do paywalls
		paywall_date = frappe.utils.get_datetime("2021-09-21 00:00:00")
		is_paywalled_bench = is_private_bench and release_group.creation > paywall_date and not is_system_user

		site_server = frappe.db.get_value("Site", site_name, "server") if site_name else None
		on_dedicated_server = is_dedicated_server(site_server) if site_server else None

	else:
		on_dedicated_server = None
		is_paywalled_bench = False

	out = []
	for plan in plans:
		if is_paywalled_bench and plan.price_usd == 10:
			continue
		if not plan.allow_downgrading_from_other_plan and plan.price_usd == 5:
			continue
		if not on_dedicated_server and plan.dedicated_server_plan:
			continue
		if on_dedicated_server and not plan.dedicated_server_plan:
			continue
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
	if site_filter is None:
		site_filter = {"status": "", "tag": ""}

	benches_with_updates = tuple(benches_with_available_update())

	sites = get_sites_query(site_filter, benches_with_updates).run(as_dict=True)

	for site in sites:
		site.server_region_info = get_server_region_info(site)
		site_plan_name = frappe.get_value("Site", site.name, "plan")
		site.plan = frappe.get_doc("Site Plan", site_plan_name) if site_plan_name else None
		site.tags = frappe.get_all(
			"Resource Tag",
			{"parent": site.name},
			pluck="tag_name",
		)
		if site.bench in benches_with_updates:
			site.update_available = True

	return sites


def get_sites_query(site_filter, benches_with_updates):
	Site = frappe.qb.DocType("Site")
	ReleaseGroup = frappe.qb.DocType("Release Group")

	from press.press.doctype.team.team import get_child_team_members

	team = get_current_team()
	child_teams = [x.name for x in get_child_team_members(team)]

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
		sites_query = sites_query.where(Site.team.isin([team, *child_teams]))
	else:
		sites_query = sites_query.where(Site.team == team)

	if site_filter["status"] == "Active":
		sites_query = sites_query.where(Site.status == "Active")
	elif site_filter["status"] == "Broken":
		sites_query = sites_query.where(Site.status == "Broken")
	elif site_filter["status"] == "Inactive":
		sites_query = sites_query.where(Site.status == "Inactive")
	elif site_filter["status"] == "Trial":
		sites_query = sites_query.where((Site.trial_end_date != "") & (Site.status != "Archived"))
	elif site_filter["status"] == "Update Available":
		sites_query = sites_query.where(Site.bench.isin(benches_with_updates) & (Site.status != "Archived"))
	else:
		sites_query = sites_query.where(Site.status != "Archived")

	if site_filter["tag"]:
		Tag = frappe.qb.DocType("Resource Tag")
		sites_with_tag = frappe.qb.from_(Tag).select(Tag.parent).where(Tag.tag_name == site_filter["tag"])
		sites_query = sites_query.where(Site.name.isin(sites_with_tag))
	return sites_query


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
		site: "Site" = frappe.get_doc("Site", name)
	except frappe.DoesNotExistError:
		# If name is a custom domain then redirect to the site name
		site_name = frappe.db.get_value("Site Domain", name, "site")
		if site_name:
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = f"/api/method/press.api.site.get?name={site_name}"
			return None
		raise
	rg_info = frappe.db.get_value("Release Group", site.group, ["team", "version", "public"], as_dict=True)
	group_team = rg_info.team
	frappe_version = rg_info.version
	group_name = site.group if group_team == team or is_system_user(frappe.session.user) else None

	server = frappe.db.get_value(
		"Server",
		site.server,
		["name", "ip", "is_standalone", "proxy_server", "team"],
		as_dict=True,
	)
	if server.is_standalone:
		ip = server.ip
	else:
		ip = frappe.db.get_value("Proxy Server", server.proxy_server, "ip")

	site_migration = get_last_doc("Site Migration", {"site": site.name})
	if (
		site_migration
		and site_migration.status not in ["Failure", "Success"]
		and -1 <= time_diff(site_migration.scheduled_time, frappe.utils.now_datetime()).days <= 1
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
		and -1 <= time_diff(version_upgrade.scheduled_time, frappe.utils.now_datetime()).days <= 1
	):
		version_upgrade = {
			"status": version_upgrade.status,
			"scheduled_time": version_upgrade.scheduled_time,
			"job_id": frappe.get_value("Site Update", version_upgrade.site_update, "update_job"),
		}
	else:
		version_upgrade = None

	on_dedicated_server = is_dedicated_server(server.name)

	return {
		"name": site.name,
		"host_name": site.host_name,
		"status": site.status,
		"archive_failed": bool(site.archive_failed),
		"trial_end_date": site.trial_end_date,
		"setup_wizard_complete": site.setup_wizard_complete,
		"group": group_name,
		"team": site.team,
		"group_public": rg_info.public,
		"latest_frappe_version": frappe.db.get_value(
			"Frappe Version", {"status": "Stable", "public": True}, order_by="name desc"
		),
		"frappe_version": frappe_version,
		"server": site.server,
		"server_region_info": get_server_region_info(site),
		"can_change_plan": server.team != team or (on_dedicated_server and server.team == team),
		"hide_config": site.hide_config,
		"communication_infos": [
			{"channel": c.channel, "type": c.type, "value": c.value} for c in site.communication_infos
		],
		"ip": ip,
		"site_tags": [{"name": x.tag, "tag": x.tag_name} for x in site.tags],
		"tags": frappe.get_all("Press Tag", {"team": team, "doctype_name": "Site"}, ["name", "tag"]),
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
	out.update_available = site.bench in benches_with_available_update(site=name)
	if not out.update_available:
		return out

	bench: "Bench" = frappe.get_doc("Bench", site.bench)
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

	destination_candidate: "DeployCandidate" = frappe.get_doc("Deploy Candidate", destination)

	out.installed_apps = site.apps

	current_apps = bench.apps
	next_apps = destination_candidate.apps
	out.apps = get_updates_between_current_and_next_apps(
		current_apps,
		next_apps,
	)
	out.update_available = any([app["update_available"] for app in out.apps])
	return out


@frappe.whitelist()
@protected("Site")
def installed_apps(name):
	site = frappe.get_cached_doc("Site", name)
	return get_installed_apps(site)


def get_installed_apps(site, query_filters: dict | None = None):
	if query_filters is None:
		query_filters = {}

	installed_apps = [app.app for app in site.apps]
	bench = frappe.get_doc("Bench", site.bench)
	installed_bench_apps = [app for app in bench.apps if app.app in installed_apps]

	AppSource = frappe.qb.DocType("App Source")
	MarketplaceApp = frappe.qb.DocType("Marketplace App")

	query = (
		frappe.qb.from_(AppSource)
		.left_join(MarketplaceApp)
		.on(AppSource.app == MarketplaceApp.app)
		.select(
			AppSource.name,
			AppSource.app,
			AppSource.repository,
			AppSource.repository_url,
			AppSource.repository_owner,
			AppSource.branch,
			AppSource.team,
			AppSource.public,
			AppSource.app_title,
			MarketplaceApp.title,
			MarketplaceApp.collect_feedback,
		)
		.where(AppSource.name.isin([d.source for d in installed_bench_apps]))
	)

	if owner := query_filters.get("repository_owner"):
		query = query.where(AppSource.repository_owner == owner)

	if branch := query_filters.get("branch"):
		query = query.where(AppSource.branch == branch)

	sources = query.run(as_dict=True)

	installed_apps = []
	for app in installed_bench_apps:
		app_source = find(sources, lambda x: x.name == app.source)
		if not app_source:
			continue
		app_source.hash = app.hash
		app_source.commit_message = frappe.db.get_value("App Release", {"hash": app_source.hash}, "message")
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
			frappe.db.exists("Marketplace App Plan", {"price_usd": (">", 0), "app": app.app, "enabled": 1})
		)
		app_source.billing_type = is_prepaid_marketplace_app(app.app)
		if frappe.db.exists(
			"Subscription",
			{
				"site": site.name,
				"document_type": "Marketplace App",
				"document_name": app.app,
				"enabled": 1,
			},
		):
			subscription = frappe.get_value(
				"Subscription",
				{
					"site": site.name,
					"document_type": "Marketplace App",
					"document_name": app.app,
					"enabled": 1,
				},
				["document_name as app", "plan", "name"],
				as_dict=True,
			)
			app_source.subscription = subscription

			app_source.plan_info = frappe.db.get_value(
				"Marketplace App Plan",
				subscription.plan,
				["price_usd", "price_inr", "name", "plan"],
				as_dict=True,
			)

			app_source.plans = get_plans_for_app(app.app)

			app_source.is_free = app_source.plan_info.price_usd <= 0
		else:
			app_source.subscription = {}

		installed_apps.append(app_source)

	return installed_apps


def get_server_region_info(site) -> dict:
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

	AppSource = frappe.qb.DocType("App Source")
	MarketplaceApp = frappe.qb.DocType("Marketplace App")

	sources = (
		frappe.qb.from_(AppSource)
		.left_join(MarketplaceApp)
		.on(AppSource.app == MarketplaceApp.app)
		.select(
			AppSource.name,
			AppSource.app,
			AppSource.repository_url,
			AppSource.repository_owner,
			AppSource.branch,
			AppSource.team,
			AppSource.public,
			AppSource.app_title,
			MarketplaceApp.title,
		)
		.where(AppSource.name.isin(bench_sources))
		.run(as_dict=True)
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
	plan = frappe.get_doc("Site Plan", site.plan) if site.plan else None

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
		"monitor_access": (is_system_user(frappe.session.user) or (plan.monitor_access if plan else None)),
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
	if not files.get("database") and not files.get("public") and not files.get("private"):
		frappe.throw("At least one file must be provided for restoration.")

	frappe.db.set_value(
		"Site",
		name,
		{
			"remote_database_file": files.get("database", ""),
			"remote_public_file": files.get("public", ""),
			"remote_private_file": files.get("private", ""),
			"remote_config_file": files.get("config", ""),
		},
	)
	site: Site = frappe.get_doc("Site", name)
	return site.restore_site(skip_failing_patches=skip_failing_patches)


@frappe.whitelist()
@protected("Site")
def validate_restoration_space_requirements(
	name: str, db_file_size: int, public_file_size: int, private_file_size: int
):
	site: Site = frappe.get_cached_doc("Site", name)
	server: Server = frappe.get_cached_doc("Server", site.server)
	database_server: DatabaseServer = frappe.get_cached_doc("Database Server", server.database_server)

	required_space_on_app_server = site.get_restore_space_required_on_app(
		db_file_size=db_file_size, public_file_size=public_file_size, private_file_size=private_file_size
	)
	required_space_on_db_server = site.get_restore_space_required_on_db(db_file_size=db_file_size)

	free_space_on_app_server = server.free_space(server.guess_data_disk_mountpoint())
	free_space_on_db_server = database_server.free_space(database_server.guess_data_disk_mountpoint())

	allowed_to_upload = False

	if server.public:
		"""
		If it's a public server, Frappe Cloud will auto extend the disk space
		to accommodate the restoration.
		"""
		allowed_to_upload = True
	else:
		if (
			free_space_on_app_server >= required_space_on_app_server
			and free_space_on_db_server >= required_space_on_db_server
		):
			allowed_to_upload = True

	return {
		"allowed_to_upload": allowed_to_upload,
		"free_space_on_app_server": free_space_on_app_server
		if not server.public
		else -1,  # -1 indicates unlimited space, no need to expose public server space
		"free_space_on_db_server": free_space_on_db_server if not database_server.public else -1,
		"is_insufficient_space_on_app_server": free_space_on_app_server < required_space_on_app_server,
		"is_insufficient_space_on_db_server": free_space_on_db_server < required_space_on_db_server,
		"required_space_on_app_server": required_space_on_app_server,
		"required_space_on_db_server": required_space_on_db_server,
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60)
def exists(subdomain, domain):
	from press.press.doctype.site.site import Site

	return Site.exists(subdomain, domain)


@frappe.whitelist()
@protected("Site")
def setup_wizard_complete(name):
	return frappe.get_doc("Site", name).is_setup_wizard_complete()


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
	config = list(filter(lambda x: not x.internal, site.configuration))

	secret_keys = frappe.get_all("Site Config Key", filters={"type": "Password"}, pluck="key")
	for c in config:
		if c.key in secret_keys:
			c.type = "Password"
			c.value = "*******"

	return config


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
			c.value = bool(sbool(c.value))
		elif c.type == "JSON":
			c.value = frappe.parse_json(c.value)
		elif c.type == "Password" and c.value == "*******":
			c.value = frappe.get_value("Site Config", {"key": c.key, "parent": name}, "value")
		sanitized_config.append(c)

	site = frappe.get_doc("Site", name)
	site.update_site_config(sanitized_config)
	return list(filter(lambda x: not x.internal, site.configuration))


@frappe.whitelist()
def get_trial_plan():
	return frappe.db.get_value("Press Settings", None, "press_trial_plan")


@frappe.whitelist()
def get_upload_link(file, parts=1):
	bucket_name = frappe.db.get_single_value("Press Settings", "remote_uploads_bucket")
	expiration = frappe.db.get_single_value("Press Settings", "remote_link_expiry") or 3600
	object_name = get_remote_key(file)
	parts = int(parts)

	s3_client = client(
		"s3",
		aws_access_key_id=frappe.db.get_single_value("Press Settings", "remote_access_key_id"),
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

		return s3_client.generate_presigned_post(bucket_name, object_name, ExpiresIn=expiration)

	except ClientError as e:
		log_error("Failed to Generate Presigned URL", content=e)


@frappe.whitelist()
def multipart_exit(file, id, action, parts=None):
	bucket_name = frappe.db.get_single_value("Press Settings", "remote_uploads_bucket")
	s3_client = client(
		"s3",
		aws_access_key_id=frappe.db.get_single_value("Press Settings", "remote_access_key_id"),
		aws_secret_access_key=get_decrypted_password(
			"Press Settings",
			"Press Settings",
			"remote_secret_access_key",
			raise_exception=False,
		),
		region_name="ap-south-1",
	)
	if action == "abort":
		response = s3_client.abort_multipart_upload(Bucket=bucket_name, Key=file, UploadId=id)
	elif action == "complete":
		parts = json.loads(parts)
		# After completing for all parts, you will use complete_multipart_upload api which requires that parts list
		response = s3_client.complete_multipart_upload(
			Bucket=bucket_name,
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
	try:
		files = get_frappe_backups(url, email, password)
	except requests.RequestException as e:
		frappe.throw(f"Could not fetch backups from {url}. Error: {e}")
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
def get_job_status(job_name):
	return {"status": frappe.db.get_value("Agent Job", job_name, "status")}


@frappe.whitelist()
@protected("Site")
def send_change_team_request(name, team_mail_id, reason):
	frappe.get_doc("Site", name).send_change_team_request(team_mail_id, reason)


@frappe.whitelist(allow_guest=True)
def confirm_site_transfer(key: str):
	from frappe import _

	if frappe.session.user == "Guest":
		return frappe.respond_as_web_page(
			_("Not Permitted"),
			_("You need to be logged in to confirm the site transfer."),
			http_status_code=403,
			indicator_color="red",
			primary_action="/dashboard/login",
			primary_label=_("Login"),
		)

	if not isinstance(key, str):
		return frappe.respond_as_web_page(
			_("Not Permitted"),
			_("The link you are using is invalid."),
			http_status_code=403,
			indicator_color="red",
		)

	if team_change := frappe.db.get_value("Team Change", {"key": key}):
		team_change = frappe.get_doc("Team Change", team_change)
		to_team = team_change.to_team
		if not frappe.db.get_value(
			"Team Member", {"user": frappe.session.user, "parent": to_team, "parenttype": "Team"}
		):
			return frappe.respond_as_web_page(
				_("Not Permitted"),
				_("You are not a member of the team to which the site is being transferred."),
				http_status_code=403,
				indicator_color="red",
			)

		team_change.transfer_completed = True
		team_change.save()
		frappe.db.commit()

		frappe.response.type = "redirect"
		frappe.response.location = f"/dashboard/sites/{team_change.document_name}"
		return None

	return frappe.respond_as_web_page(
		_("Not Permitted"),
		_("The link you are using is invalid or expired."),
		http_status_code=403,
		indicator_color="red",
	)


@frappe.whitelist()
@protected("Site")
def add_server_to_release_group(name, group_name, server=None):
	if not server:
		server = frappe.db.get_value("Site", name, "server")

	rg: ReleaseGroup = frappe.get_doc("Release Group", group_name)

	if not frappe.db.exists("Deploy Candidate Build", {"status": "Success", "group": group_name}):
		frappe.throw(
			f"There should be atleast one deploy in the bench {frappe.bold(rg.title)} to do a site migration or a site version upgrade."
		)
	try:
		deploy = rg.add_server(server, deploy=True)
	except PermissionError as e:
		if f"does not have access to this document: Release Group - {group_name}" in str(e):
			frappe.throw(
				f"Bench group is owned by a team you (<strong>{frappe.session.user}</strong>) are not a member of. Please contact the team owner or transfer the bench group to your team.",
			)
		else:
			frappe.throw(str(e), type(e))

	if isinstance(deploy, str):
		return None

	bench = find(deploy.benches, lambda bench: bench.server == server).bench
	return frappe.get_value("Agent Job", {"bench": bench, "job_type": "New Bench"}, "name")


@frappe.whitelist()
def validate_group_for_upgrade(name, group_name):
	server = frappe.db.get_value("Site", name, "server")
	rg = frappe.get_doc("Release Group", group_name)
	if server not in [server.server for server in rg.servers]:
		return False
	return True


@frappe.whitelist()
@protected("Site")
@role_guard.document(
	document_type=lambda _: "Release Group",
	inject_values=True,
	should_throw=False,
)
def change_group_options(name, release_groups=None):
	team = get_current_team()
	group, server, plan = frappe.db.get_value("Site", name, ["group", "server", "plan"])

	if plan and not frappe.db.get_value("Site Plan", plan, "private_benches"):
		frappe.throw(
			"The current plan doesn't allow the site to be in a private bench. Please upgrade to a higher plan to move your site."
		)

	version = frappe.db.get_value("Release Group", group, "version")

	Bench = frappe.qb.DocType("Bench")
	ReleaseGroup = frappe.qb.DocType("Release Group")
	query = (
		frappe.qb.from_(Bench)
		.select(Bench.group.as_("name"), ReleaseGroup.title)
		.inner_join(ReleaseGroup)
		.on(ReleaseGroup.name == Bench.group)
		.where(Bench.status == "Active")
		.where(ReleaseGroup.name != group)
		.where(ReleaseGroup.version == version)
		.where(ReleaseGroup.team == team)
		.where(Bench.server == server)
		.groupby(Bench.group)
	)

	if release_groups and isinstance(release_groups, list):
		query = query.where(ReleaseGroup.name.isin(release_groups))

	return query.run(as_dict=True)


@frappe.whitelist()
@protected("Site")
def clone_group(name: str, new_group_title: str, server: str | None = None):
	site = frappe.get_doc("Site", name)
	group = frappe.get_doc("Release Group", site.group)
	cloned_group = frappe.new_doc("Release Group")

	cloned_group.update(
		{
			"title": new_group_title,
			"team": get_current_team(),
			"public": 0,
			"enabled": 1,
			"version": group.version,
			"dependencies": group.dependencies,
			"is_redisearch_enabled": group.is_redisearch_enabled,
			"servers": [{"server": server if server else site.server, "default": False}],
		}
	)

	# add apps to rg if they are installed in site
	apps_installed_in_site = [app.app for app in site.apps]
	cloned_group.apps = [app for app in group.apps if app.app in apps_installed_in_site]

	cloned_group.insert()

	candidate = cloned_group.create_deploy_candidate()
	candidate.schedule_build_and_deploy()

	return {
		"bench_name": cloned_group.name,
		"candidate_name": candidate.name,
	}


@frappe.whitelist()
@protected("Site")
def change_group(name, group, skip_failing_patches=False):
	team = frappe.db.get_value("Release Group", group, "team")
	if team != get_current_team():
		frappe.throw(f"Bench {group} does not belong to your team")

	site = frappe.get_doc("Site", name)
	site.move_to_group(group, skip_failing_patches=skip_failing_patches)


@frappe.whitelist()
@protected("Site")
def change_region_options(name):
	group, cluster = frappe.db.get_value("Site", name, ["group", "cluster"])

	group = frappe.get_doc("Release Group", group)
	cluster_names = group.get_clusters()
	group_regions = frappe.get_all(
		"Cluster", filters={"name": ("in", cluster_names)}, fields=["name", "title", "image"]
	)

	return {
		"regions": [region for region in group_regions if region.name != cluster],
		"current_region": cluster,
	}


@frappe.whitelist()
@protected("Site")
def change_region(name, cluster, scheduled_datetime=None, skip_failing_patches=False):
	group = frappe.db.get_value("Site", name, "group")
	bench_vals = frappe.db.get_value(
		"Bench", {"group": group, "cluster": cluster, "status": "Active"}, ["name", "server"]
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
			"skip_failing_patches": skip_failing_patches,
		}
	).insert()

	if not scheduled_datetime:
		site_migration.start()


@frappe.whitelist()
@protected("Site")
@role_guard.document(
	document_type=lambda _: "Release Group",
	inject_values=True,
	should_throw=False,
)
def get_private_groups_for_upgrade(name, version, release_groups=None):
	team = get_current_team()
	version_number = frappe.db.get_value("Frappe Version", version, "number")
	next_version = frappe.db.get_value(
		"Frappe Version",
		{
			"number": version_number + 1,
			"status": ("in", ("Stable", "End of Life")),
			"public": True,
		},
		"name",
	)

	ReleaseGroup = frappe.qb.DocType("Release Group")
	ReleaseGroupServer = frappe.qb.DocType("Release Group Server")

	query = (
		frappe.qb.from_(ReleaseGroup)
		.select(ReleaseGroup.name, ReleaseGroup.title)
		.join(ReleaseGroupServer)
		.on(ReleaseGroupServer.parent == ReleaseGroup.name)
		.where(ReleaseGroup.enabled == 1)
		.where(ReleaseGroup.team == team)
		.where(ReleaseGroup.public == 0)
		.where(ReleaseGroup.version == next_version)
		.distinct()
	)

	if release_groups and isinstance(release_groups, list):
		query = query.where(ReleaseGroup.name.isin(release_groups))

	return query.run(as_dict=True)


@frappe.whitelist()
@protected("Site")
def version_upgrade(
	name, destination_group, scheduled_datetime=None, skip_failing_patches=False, skip_backups=False
):
	site = frappe.get_doc("Site", name)
	current_version, shared_site, central_site = frappe.db.get_value(
		"Release Group", site.group, ["version", "public", "central_bench"]
	)
	next_version = f"Version {int(current_version.split(' ')[1]) + 1}"

	if shared_site or central_site:
		ReleaseGroup = frappe.qb.DocType("Release Group")
		ReleaseGroupServer = frappe.qb.DocType("Release Group Server")

		destination_group = (
			frappe.qb.from_(ReleaseGroup)
			.select(ReleaseGroup.name)
			.join(ReleaseGroupServer)
			.on(ReleaseGroupServer.parent == ReleaseGroup.name)
			.where(ReleaseGroup.version == next_version)
			.where(ReleaseGroup.public == shared_site)
			.where(ReleaseGroup.central_bench == central_site)
			.where(ReleaseGroup.enabled == 1)
			.where(ReleaseGroupServer.server == site.server)
			.run(as_dict=True, pluck="name")
		)

		if destination_group:
			destination_group = destination_group[0]
		else:
			frappe.throw(f"There are no public benches with the version {frappe.bold(next_version)}.")

	version_upgrade = frappe.get_doc(
		{
			"doctype": "Version Upgrade",
			"site": name,
			"destination_group": destination_group,
			"scheduled_time": scheduled_datetime,
			"skip_failing_patches": skip_failing_patches,
			"skip_backups": skip_backups,
		}
	).insert()

	if not scheduled_datetime:
		version_upgrade.start()


@frappe.whitelist()
@protected("Site")
def check_existing_upgrade_bench(name, version):
	"""
	Check if an existing next-version bench exists on the same server
	with compatible app list (all or more apps than current site's release group).

	Returns: {
		"exists": bool,
		"bench_name": str or None,
		"release_group": str or None,
	}
	"""
	site_server, site_group = frappe.db.get_value("Site", name, ["server", "group"])
	current_team = get_current_team()

	current_apps = frappe.db.get_all("Release Group App", filters={"parent": site_group}, pluck="app")

	version_number = frappe.db.get_value("Frappe Version", version, "number")
	next_version = frappe.db.get_value(
		"Frappe Version",
		{
			"number": version_number + 1,
			"status": ("in", ("Stable", "End of Life")),
			"public": True,
		},
		"name",
	)

	if not next_version:
		return {"exists": False, "bench_name": None, "release_group": None}

	# Find private benches on same server with next version - optimized query
	Bench = frappe.qb.DocType("Bench")
	ReleaseGroup = frappe.qb.DocType("Release Group")

	benches = (
		frappe.qb.from_(Bench)
		.join(ReleaseGroup)
		.on(Bench.group == ReleaseGroup.name)
		.select(Bench.name, Bench.group, ReleaseGroup.title)
		.where(Bench.status == "Active")
		.where(Bench.server == site_server)
		.where(Bench.team == current_team)
		.where(ReleaseGroup.version == next_version)
		.where(ReleaseGroup.public == 0)
	).run(as_dict=True)

	for bench in benches:
		bench_apps = frappe.db.get_all("Release Group App", filters={"parent": bench.group}, pluck="app")
		if set(current_apps).issubset(set(bench_apps)):
			return {
				"exists": True,
				"bench_name": bench.name,
				"release_group": bench.group,
				"release_group_title": bench.release_group_title,
			}

	return {"exists": False, "bench_name": None, "release_group": None, "release_group_title": None}


@frappe.whitelist()
@protected("Site")
def check_app_compatibility_for_upgrade(name, version):
	"""
	Check which apps in the current site's release group are compatible
	with the next Frappe version.
	"""
	next_version = get_next_version(version)
	site_group = frappe.db.get_value("Site", name, "group")
	current_apps = frappe.db.get_all(
		"Release Group App",
		filters={"parent": site_group},
		fields=["app", "source"],
	)
	if not current_apps:
		return {
			"incompatible": [],
			"custom_apps": [],
			"can_upgrade": True,
		}
	source_names = list({a.source for a in current_apps})
	app_sources = frappe.db.get_all(
		"App Source",
		filters={"name": ("in", source_names)},
		fields=[
			"name",
			"app_title",
			"app",
			"public",
			"enabled",
			"repository_url",
			"github_installation_id",
			"branch",
		],
	)
	source_map = {s.name: s for s in app_sources}
	public_apps = []
	public_source_map = {}
	for row in current_apps:
		source = source_map.get(row.source)
		if not source or not source.enabled:
			continue

		if source.public:
			public_apps.append(row.app)
			public_source_map[row.app] = source

	incompatible_apps = _check_public_apps_compatibility(
		public_apps,
		public_source_map,
		next_version,
	)
	if incompatible_apps:
		return {
			"incompatible": incompatible_apps,
			"custom_apps": [],
			"can_upgrade": False,
		}

	# Fetch custom app branches only if public apps are compatible
	custom_apps = []
	for row in current_apps:
		source = source_map.get(row.source)
		if not source or source.public or not source.enabled:
			continue

		branches = _get_custom_app_branches(
			source.repository_url,
			row.app,
			source.github_installation_id,
		)
		custom_apps.append(
			{
				"app": row.app,
				"title": source.app_title or row.app,
				"repository_url": source.repository_url,
				"branch": source.branch,
				"branches": branches,
			}
		)

	return {
		"incompatible": [],
		"custom_apps": custom_apps,
		"can_upgrade": True,
	}


@frappe.whitelist()
@protected("Site")
def create_private_bench_for_upgrade(
	name,
	version,
	release_group_title,
	custom_app_sources=None,
	scheduled_time=None,
	skip_failing_patches=False,
	skip_backups=False,
):
	"""
	Deploy private release group and schedule version upgrade.
	"""
	from press.press.doctype.release_group.release_group import new_release_group

	next_version = get_next_version(version)
	site_group, site_server = frappe.db.get_value("Site", name, ["group", "server"])
	team = get_current_team()

	custom_app_sources = custom_app_sources or []
	custom_source_map = {c.get("app"): c for c in custom_app_sources}

	current_apps = frappe.db.get_all(
		"Release Group App",
		filters={"parent": site_group},
		fields=["app", "source"],
	)
	if not current_apps:
		frappe.throw("No apps found in current release group")

	app_names = [a.app for a in current_apps]
	source_names = [a.source for a in current_apps]

	app_sources = frappe.db.get_all(
		"App Source",
		filters={"name": ("in", source_names)},
		fields=[
			"name",
			"app",
			"public",
			"enabled",
			"repository_url",
			"github_installation_id",
		],
	)

	source_map = {s.name: s for s in app_sources}
	_, compatible_apps_map = get_compatible_public_apps_and_sources(
		app_names,
		next_version,
	)

	apps_for_new_group = _get_apps_for_version_upgrade(
		current_apps,
		source_map,
		compatible_apps_map,
		custom_source_map,
		next_version,
		team,
	)
	apps_payload = [{"app": app, "source": source} for app, source in apps_for_new_group]

	try:
		release_group_doc = new_release_group(
			title=release_group_title,
			version=next_version,
			apps=apps_payload,
			team=team,
			server=site_server,
		)
		version_upgrade = frappe.get_doc(
			{
				"doctype": "Version Upgrade",
				"site": name,
				"deploy_private_bench": 1,
				"destination_group": release_group_doc.name,
				"scheduled_time": scheduled_time,
				"skip_failing_patches": skip_failing_patches,
				"skip_backups": skip_backups,
				"status": "Pending",
			}
		)
		version_upgrade.insert()
		return release_group_doc.name
	except Exception as e:
		frappe.throw(f"Failed to create and deploy bench: {e!s}")


@frappe.whitelist()
@protected("Site")
def change_server_options(name):
	site = Site("Site", name)
	return {
		"servers": frappe.db.get_all(
			"Server",
			{"team": get_current_team(), "status": "Active", "name": ("!=", site.server)},
			["name", "title"],
		),
		"estimated_duration": site.get_estimated_duration_for_server_change(),
	}


@frappe.whitelist()
@protected("Site")
def is_server_added_in_group(name, server):
	site_group = frappe.get_value("Site", name, "group")
	rg = frappe.get_doc("Release Group", site_group)
	if server not in [s.server for s in rg.servers]:
		return False
	return True


@frappe.whitelist()
@protected("Site")
def change_server(name, server, scheduled_datetime=None, skip_failing_patches=False):
	group = frappe.db.get_value("Site", name, "group")
	bench = frappe.db.get_value("Bench", {"group": group, "status": "Active", "server": server}, "name")

	if not bench:
		if frappe.db.exists(
			"Agent Job",
			{
				"job_type": "New Bench",
				"status": ("in", ("Pending", "Running")),
				"server": server,
			},
		):
			frappe.throw(
				f"Please wait for the new deploy to be created in the server {frappe.bold(server)} if you have just added a new server to the bench."
			)
		else:
			frappe.throw(
				f"A deploy does not exist in the server {frappe.bold(server)}. Please schedule a new deploy on your bench and try again."
			)

	site_migration = frappe.get_doc(
		{
			"doctype": "Site Migration",
			"site": name,
			"destination_bench": bench,
			"scheduled_time": scheduled_datetime,
			"skip_failing_patches": skip_failing_patches,
		}
	).insert()

	if not scheduled_datetime:
		site_migration.start()


@frappe.whitelist()
def get_site_config_standard_keys():
	return frappe.get_all(
		"Site Config Key",
		{"internal": 0},
		["name", "key", "title", "description", "type"],
		order_by="title asc",
	)


@frappe.whitelist()
def fetch_sites_data_for_export():
	from press.api.client import get_list

	sites = get_list(
		"Site",
		[
			"name",
			"host_name",
			"plan.plan_title as plan_title",
			"cluster.title as cluster_title",
			"group.title as group_title",
			"group.version as version",
			"creation",
		],
		start=0,
		limit=99999,
	)

	tags = frappe.db.get_all(
		"Resource Tag",
		filters={"parenttype": "Site", "parent": ["in", [site.name for site in sites]]},
		fields=["name", "tag_name", "parent"],
	)

	for site in sites:
		site.tags = [tag.tag_name for tag in tags if tag.parent == site.name]

	return sites


def get_next_version(version):
	version_number = frappe.db.get_value("Frappe Version", version, "number")
	if not version_number:
		frappe.throw(f"Invalid Frappe version: {version}")

	next_version = frappe.db.get_value(
		"Frappe Version",
		{
			"number": version_number + 1,
			"status": ("in", ("Stable", "End of Life")),
			"public": True,
		},
		"name",
	)
	if not next_version:
		frappe.throw(f"Next version not found for {version}")

	return next_version


def _check_public_apps_compatibility(public_apps, source_map, next_version):
	compatible_set, _ = get_compatible_public_apps_and_sources(
		public_apps,
		next_version,
	)
	incompatible = []

	for app in public_apps:
		if app in compatible_set:
			continue

		source = source_map.get(app)
		incompatible.append(source.app_title if source else app)

	return incompatible


def _get_custom_app_branches(repository_url, app_name, installation_id):
	if not repository_url:
		return []

	try:
		match = re.search(r"github\.com/([^/]+)/([^/\.]+)", repository_url)
		if not match:
			return []

		owner, repo = match.groups()

		from press.api.github import branches as gh_branches

		api_branches = gh_branches(
			owner=owner,
			name=repo,
			installation=installation_id or None,
		)
		if api_branches:
			return [b.get("name") for b in api_branches]
	except Exception as e:
		frappe.log_error(
			f"Failed to fetch branches for {app_name}: {e!s}",
			"check_app_compatibility_for_upgrade",
		)
	return []


def _get_apps_for_version_upgrade(
	current_apps,
	source_map,
	compatible_map,
	custom_source_map,
	next_version,
	team,
):
	apps = []
	for row in current_apps:
		app_name = row.app
		source_name = row.source
		source = source_map.get(source_name)
		if not source or not source.enabled:
			frappe.throw(f"Invalid source for {app_name}")

		if source.public:
			compatible_source = compatible_map.get(app_name)
			if not compatible_source:
				frappe.throw(f"No compatible source for app {app_name} for {next_version}")
			apps.append((app_name, compatible_source))
			continue

		custom_payload = custom_source_map.get(app_name)
		if not custom_payload:
			frappe.throw(f"Custom app source not provided for {app_name}")

		branch = custom_payload.get("branch")
		repository_url = source.repository_url
		github_installation_id = source.github_installation_id

		if not branch:
			frappe.throw(f"Branch not provided for {app_name}")
		if not repository_url:
			frappe.throw(f"Repository URL not provided for {app_name}")

		app_doc = frappe.get_cached_doc("App", app_name)
		custom_source = app_doc.add_source(
			repository_url=repository_url,
			branch=branch,
			frappe_version=next_version,
			team=team,
			github_installation_id=github_installation_id,
		)
		apps.append((app_name, custom_source.name))
	return apps


def get_compatible_public_apps_and_sources(app_names, next_version):
	"""
	Return:
	- set(app)
	- dict(app -> source)
	"""
	if not app_names:
		return set(), {}

	AppSource = frappe.qb.DocType("App Source")
	AppSourceVersion = frappe.qb.DocType("App Source Version")
	rows = (
		frappe.qb.from_(AppSourceVersion)
		.join(AppSource)
		.on(AppSourceVersion.parent == AppSource.name)
		.select(
			AppSource.app,
			AppSource.name.as_("source"),
		)
		.where(AppSourceVersion.version == next_version)
		.where(AppSource.app.isin(app_names))
		.where(AppSource.public == 1)
		.where(AppSource.enabled == 1)
	).run(as_dict=True)

	compatible_apps = set()
	compatible_sources = {}
	for r in rows:
		compatible_apps.add(r.app)
		compatible_sources[r.app] = r.source

	return compatible_apps, compatible_sources
