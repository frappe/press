# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import json
import frappe

from typing import Dict, List
from frappe.core.utils import find
from press.api.bench import options
from press.api.site import protected
from press.marketplace.doctype.marketplace_app_plan.marketplace_app_plan import (
	MarketplaceAppPlan,
)
from press.press.doctype.plan.plan import Plan
from press.press.doctype.app.app import new_app as new_app_doc
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.app_release.app_release import AppRelease
from press.utils import get_current_team, get_last_doc, unique, get_app_tag
from press.press.doctype.marketplace_app.marketplace_app import MarketplaceApp
from press.press.doctype.app_release_approval_request.app_release_approval_request import (
	AppReleaseApprovalRequest,
)
from press.press.doctype.marketplace_app.marketplace_app import get_plans_for_app


@frappe.whitelist()
def options_for_quick_install(marketplace_app: str):
	app_name, title = frappe.db.get_value(
		"Marketplace App", marketplace_app, ["app", "title"]
	)
	candidate_groups = get_candidate_release_groups(marketplace_app, app_name)
	candidate_sites = get_candidate_sites(app_name)
	plans = get_plans_for_app(marketplace_app)

	return {
		"release_groups": candidate_groups,
		"sites": candidate_sites,
		"app_name": app_name,
		"title": title,
		"has_plans_available": len(plans) > 0,
	}


def get_candidate_release_groups(marketplace_app: str, app_name: str) -> List[Dict]:
	"""
	List of release groups where the given marketplace app is NOT installed but CAN BE installed.

	returns list of dicts of the form:
	{
	'name': 'bench-1096',
	'title': 'My Private Bench',
	'version': 'Version 13',
	'source': 'SRC-posawesome-001'
	}
	"""
	team = get_current_team()
	group = frappe.qb.DocType("Release Group")
	group_app = frappe.qb.DocType("Release Group App")
	marketplace_app_version = frappe.qb.DocType("Marketplace App Version")

	query = (
		frappe.qb.from_(group)
		.left_join(marketplace_app_version)
		.on(marketplace_app_version.version == group.version)
		.left_join(group_app)
		.on((group.name == group_app.parent) & (group_app.app == app_name))
		.select(group.name, group.title, group.version, marketplace_app_version.source)
		.where(
			(group.enabled == 1)
			& (group.team == team)
			& (marketplace_app_version.parent == marketplace_app)
			& group_app.app.isnull()  # not present in group
		)
	)

	return query.run(as_dict=True)


def get_candidate_sites(app_name: str) -> List[str]:
	"""
	List of Active sites on which the given app is NOT installed but CAN BE installed.
	"""
	team = get_current_team()
	site = frappe.qb.DocType("Site")
	site_app = frappe.qb.DocType("Site App")
	bench = frappe.qb.DocType("Bench")
	bench_app = frappe.qb.DocType("Bench App")

	sites = (
		frappe.qb.from_(site)
		.left_join(site_app)
		.on((site_app.parent == site.name) & (site_app.app == app_name))
		.left_join(bench)
		.on(bench.name == site.bench)
		.right_join(bench_app)  # must be installed on bench (corresponding bench app exists)
		.on((bench.name == bench_app.parent) & (bench_app.app == app_name))
		.select(site.name)
		.where(
			(site.status == "Active") & (site.team == team) & site_app.app.isnull()
		)  # not installed on site
	)

	return sites.run(pluck="name")


@frappe.whitelist()
def become_publisher():
	"""Turn on marketplace developer mode for current team"""
	current_team = get_current_team(get_doc=True)
	current_team.is_developer = True
	current_team.save()


@frappe.whitelist()
def developer_toggle_allowed():
	"""Feature flag to allow display of developer account toggle"""
	# Already a developer
	current_team = get_current_team(get_doc=True)
	if current_team.is_developer:
		return False

	return frappe.db.get_value("Press Settings", None, "allow_developer_account") == "1"


@frappe.whitelist()
def frappe_versions():
	"""Return a list of Frappe Version names"""
	return frappe.get_all("Frappe Version", pluck="name", order_by="name desc")


@frappe.whitelist()
def get_apps() -> List[Dict]:
	"""Return list of apps developed by the current team"""
	team = get_current_team()
	apps = frappe.get_all(
		"Marketplace App",
		fields=["name", "title", "image", "app", "status", "description"],
		filters={"team": team},
		order_by="title",
	)

	return apps


@frappe.whitelist()
@protected("Marketplace App")
def get_app(name: str) -> Dict:
	"""Return the `Marketplace App` document with name"""
	app = frappe.get_doc("Marketplace App", name).as_dict()
	deploy_info = deploy_information(name)

	# Attach sources information to marketplace sources
	for source in app.sources:
		source_information = frappe.get_doc("App Source", source.source).as_dict()
		source_information.status = deploy_info.get(source.version)
		source.source_information = source_information

	return app


@frappe.whitelist()
@protected("Marketplace App")
def deploy_information(name: str):
	"""Return the deploy information for marketplace app `app`"""
	marketplace_app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	return marketplace_app.get_deploy_information()


@frappe.whitelist()
@protected("Marketplace App")
def published_versions(name: str) -> List[Dict]:
	"""Return a list of published versions of the app `name`"""
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)

	versions = []
	for source in app.sources:
		app_source = frappe.get_doc("App Source", source.source)
		version = {
			"version": source.version,
			"repository_url": app_source.repository_url,
			"repository": app_source.repository,
			"branch": app_source.branch,
			"repository_owner": app_source.repository_owner,
			"source": source.source,
		}
		versions.append(version)

	return versions


@frappe.whitelist()
def profile_image_url(app: str) -> str:
	return frappe.db.get_value("Marketplace App", app, "image")


@frappe.whitelist()
def update_app_image() -> str:
	"""Handles App Image Upload"""
	app_name = frappe.form_dict.docname
	_file = frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": "Marketplace App",
			"attached_to_name": app_name,
			"attached_to_field": "image",
			"folder": "Home/Attachments",
			"file_name": frappe.local.uploaded_filename,
			"is_private": 0,
			"content": frappe.local.uploaded_file,
		}
	)
	_file.save(ignore_permissions=True)
	file_url = _file.file_url
	frappe.db.set_value("Marketplace App", app_name, "image", file_url)

	return file_url


@frappe.whitelist()
def update_app_profile(name: str, title: str, category: str) -> MarketplaceApp:
	"""Update `title` and `category`"""
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	app.title = title
	app.category = category
	app.save(ignore_permissions=True)

	return app


@frappe.whitelist()
def update_app_links(name: str, links: Dict) -> None:
	"""Update links related to app"""
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	app.update(links)
	app.save(ignore_permissions=True)


@frappe.whitelist()
def categories() -> List[str]:
	"""Return a list of Marketplace App Categories"""
	categories = frappe.get_all("Marketplace App Category", pluck="name")
	return categories


@frappe.whitelist()
def update_app_summary(name: str, summary: str) -> None:
	"""Update the `description` of Marketplace App `name`"""
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	app.description = summary
	app.save(ignore_permissions=True)


@frappe.whitelist()
def update_app_description(name: str, description: str) -> None:
	"""Update the `long_description` of Marketplace App `name`"""
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	app.long_description = description
	app.save(ignore_permissions=True)


@frappe.whitelist()
def releases(app: str, source: str, start: int = 0) -> List[Dict]:
	"""Return list of App Releases for this `app` and `source` in order of creation time"""

	app_releases = frappe.get_all(
		"App Release",
		filters={"app": app, "source": source},
		fields="*",
		order_by="creation desc",
		start=start,
		limit=15,
	)

	for release in app_releases:
		# Attach rejection feedback (if any)
		try:
			feedback = reason_for_rejection(release.name)
		except frappe.ValidationError:
			feedback = ""
		release.reason_for_rejection = feedback

		# Attach release tag
		app_source = frappe.get_doc("App Source", release.source)
		release.tag = get_app_tag(
			app_source.repository, app_source.repository_owner, release.hash
		)

	return app_releases


@frappe.whitelist()
def get_app_source(name: str) -> AppSource:
	"""Return `App Source` document having `name`"""
	return frappe.get_doc("App Source", name)


@frappe.whitelist()
def latest_approved_release(source: str) -> AppRelease:
	"""Return the latest app release with `approved` status"""
	return get_last_doc("App Release", {"source": source, "status": "Approved"})


@frappe.whitelist()
def create_approval_request(marketplace_app: str, app_release: str):
	"""Create a new Approval Request for given `app_release`"""
	AppReleaseApprovalRequest.create(marketplace_app, app_release)


@frappe.whitelist()
def cancel_approval_request(app_release: str):
	"""Cancel Approval Request for given `app_release`"""
	get_latest_approval_request(app_release).cancel()


@frappe.whitelist()
def reason_for_rejection(app_release: str) -> str:
	"""Return feedback given on a `Rejected` approval request"""
	approval_request = get_latest_approval_request(app_release)
	app_release = frappe.get_doc("App Release", app_release)

	if app_release.status != "Rejected":
		frappe.throw("The request for the given app release was not rejected!")

	return approval_request.reason_for_rejection


def get_latest_approval_request(app_release: str):
	"""Return Approval request for the given `app_release`, throws if not found"""
	approval_requests = frappe.get_all(
		"App Release Approval Request",
		filters={"app_release": app_release},
		pluck="name",
		order_by="creation desc",
	)

	if len(approval_requests) == 0:
		frappe.throw("No approval request exists for the given app release")

	approval_request: AppReleaseApprovalRequest = frappe.get_doc(
		"App Release Approval Request", approval_requests[0]
	)

	return approval_request


@frappe.whitelist()
def options_for_marketplace_app() -> Dict[str, Dict]:
	""""""
	# Get versions (along with apps and associated sources)
	# which belong to the current team
	versions = options(only_by_current_team=True)["versions"]

	filtered_apps = []

	for version in versions:
		# Remove Frappe Framework
		version["apps"] = [app for app in version["apps"] if app["name"] != "frappe"]

		for app in version["apps"]:
			if not is_on_marketplace(app["name"]):
				for source in app["sources"]:
					source["version"] = version["name"]
				filtered_apps.append(app)

			else:
				marketplace_app = frappe.get_doc("Marketplace App", app["name"])
				marketplace_versions = [v.version for v in marketplace_app.sources]

				if version["name"] not in marketplace_versions:
					for source in app["sources"]:
						source["version"] = version["name"]
					filtered_apps.append(app)

	aggregated_sources = {}

	for app in filtered_apps:
		aggregated_sources.setdefault(app["name"], []).extend(app["sources"])
		# Remove duplicate sources
		aggregated_sources[app["name"]] = unique(
			aggregated_sources[app["name"]], lambda x: x["name"]
		)

	marketplace_options = []
	for app_name, sources in aggregated_sources.items():
		app = find(filtered_apps, lambda x: x["name"] == app_name)
		marketplace_options.append(
			{
				"name": app_name,
				"sources": sources,
				"source": app["source"],
				"title": app["title"],
			}
		)

	return marketplace_options


def is_on_marketplace(app: str) -> bool:
	"""Returns `True` if this `app` is on marketplace else `False`"""
	return frappe.db.exists("Marketplace App", app)


@frappe.whitelist()
def new_app(app: Dict):
	name = app["name"]
	team = get_current_team()

	if frappe.db.exists("App", name):
		app_doc = frappe.get_doc("App", name)
	else:
		app_doc = new_app_doc(name, app["title"])

	source = app_doc.add_source(
		app["version"],
		app["repository_url"],
		app["branch"],
		team,
		app["github_installation_id"],
	)

	return add_app(source.name, app_doc.name)


@frappe.whitelist()
def add_app(source: str, app: str):
	if not is_on_marketplace(app):
		supported_versions = frappe.get_all(
			"App Source Version", filters={"parent": source}, pluck="version"
		)
		marketplace_app = frappe.get_doc(
			doctype="Marketplace App",
			app=app,
			team=get_current_team(),
			description="Please add a short description about your app here...",
			sources=[{"version": v, "source": source} for v in supported_versions],
		).insert()

	else:
		marketplace_app = frappe.get_doc("Marketplace App", app)

		if marketplace_app.team != get_current_team():
			frappe.throw(
				f"The app {marketplace_app.name} already exists and is owned by some other team."
			)

		# Versions on marketplace
		versions = [v.version for v in marketplace_app.sources]

		app_source = frappe.get_doc("App Source", source)
		# Versions on this app `source`
		app_source_versions = [v.version for v in app_source.versions]

		version_difference = set(app_source_versions) - set(versions)
		if version_difference:
			# App source contains version not yet in marketplace
			for version in version_difference:
				marketplace_app.append("sources", {"source": source, "version": version})
				marketplace_app.save()
		else:
			frappe.throw("A marketplace app already exists with the given versions!")

	return marketplace_app.name


@frappe.whitelist()
@protected("Marketplace App")
def analytics(name: str):
	marketplace_app_doc: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	return marketplace_app_doc.get_analytics()


@frappe.whitelist()
def get_promotional_banners() -> List:
	promotionalBanner = frappe.qb.DocType("Marketplace Promotional Banner")
	marketplaceApp = frappe.qb.DocType("Marketplace App")

	promotions = (
		frappe.qb.from_(promotionalBanner)
		.left_join(marketplaceApp)
		.on(promotionalBanner.marketplace_app == marketplaceApp.name)
		.select(
			promotionalBanner.alert_message,
			promotionalBanner.alert_title,
			promotionalBanner.marketplace_app.as_("app"),
			promotionalBanner.name,
			marketplaceApp.image,
			marketplaceApp.title,
			marketplaceApp.description,
		)
		.where(promotionalBanner.is_active == True)  # noqa
		.run(as_dict=True)
	)

	return promotions


# PAID APPS APIs
# (might refactor later to a separate file
#  like 'api/marketplace/billing.py')


@frappe.whitelist()
def get_marketplace_subscriptions_for_site(site: str):
	subscriptions = frappe.db.get_all(
		"Marketplace App Subscription",
		filters={"site": site, "status": ("!=", "Disabled")},
		fields=["name", "app", "status", "marketplace_app_plan", "plan"],
	)

	for subscription in subscriptions:
		marketplace_app_info = frappe.db.get_value(
			"Marketplace App", subscription.app, ["title", "image"], as_dict=True
		)

		subscription.app_title = marketplace_app_info.title
		subscription.app_image = marketplace_app_info.image

		subscription.plan_info = frappe.db.get_value(
			"Plan", subscription.plan, ["price_usd", "price_inr"], as_dict=True
		)

		subscription.is_free = frappe.db.get_value(
			"Marketplace App Plan", subscription.marketplace_app_plan, "is_free"
		)

	return subscriptions


@frappe.whitelist()
def get_app_plans(app: str, release_group: str = None, frappe_version: str = None):
	marketplace_app: MarketplaceApp = frappe.get_doc("Marketplace App", app)

	if (not frappe_version) and release_group:
		frappe_version = frappe.db.get_value("Release Group", release_group, "version")

	return marketplace_app.get_plans(frappe_version)


@frappe.whitelist()
def get_app_info(app: str):
	return frappe.db.get_value(
		"Marketplace App", app, ["name", "title", "image"], as_dict=True
	)


@frappe.whitelist()
def get_apps_with_plans(apps, release_group: str = None):

	if isinstance(apps, str):
		apps = json.loads(apps)

	apps_with_plans = []

	# Make sure it is a marketplace app
	m_apps = frappe.db.get_all(
		"Marketplace App", filters={"app": ("in", apps)}, fields=["name", "title", "image"]
	)

	frappe_version = frappe.db.get_value("Release Group", release_group, "version")
	for app in m_apps:
		plans = get_plans_for_app(app.name, frappe_version)
		if len(plans) > 0:
			apps_with_plans.append(app)

	return apps_with_plans


@frappe.whitelist()
def change_app_plan(subscription, new_plan):
	is_free = frappe.db.get_value("Marketplace App Plan", new_plan, "is_free")
	if not is_free:
		team = get_current_team(get_doc=True)
		if not team.can_install_paid_apps():
			frappe.throw(
				"You cannot upgrade to paid plan on Free Credits. Please buy credits before trying to upgrade plan."
			)

	subscription = frappe.get_doc("Marketplace App Subscription", subscription)
	subscription.marketplace_app_plan = new_plan
	subscription.save(ignore_permissions=True)


@frappe.whitelist()
def get_publisher_profile_info():
	publisher_profile_info = {}

	team = get_current_team()

	publisher_profile_name = frappe.db.exists(
		"Marketplace Publisher Profile", {"team": team}
	)

	if publisher_profile_name:
		publisher_profile_info["profile_created"] = True
		publisher_profile_info["profile_info"] = frappe.get_doc(
			"Marketplace Publisher Profile", publisher_profile_name
		)

	return publisher_profile_info


@frappe.whitelist()
def update_publisher_profile(profile_data=dict()):
	"""Update if exists, otherwise create"""
	team = get_current_team()

	publisher_profile_name = frappe.db.exists(
		"Marketplace Publisher Profile", {"team": team}
	)

	if publisher_profile_name:
		profile_doc = frappe.get_doc(
			"Marketplace Publisher Profile", publisher_profile_name, for_update=True
		)
		profile_doc.update(profile_data)
		profile_doc.save()
	else:
		profile_doc = frappe.get_doc({"doctype": "Marketplace Publisher Profile"})
		profile_doc.team = team
		profile_doc.update(profile_data)
		profile_doc.insert(ignore_permissions=True)


@frappe.whitelist()
def submit_user_review(title, rating, app, review):
	return frappe.get_doc(
		{
			"doctype": "App User Review",
			"title": title,
			"rating": rating / 5,
			"app": app,
			"review": review,
			"reviewer": frappe.session.user,
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def get_subscriptions_list(marketplace_app: str) -> List:
	app_sub = frappe.qb.DocType("Marketplace App Subscription")
	app_plan = frappe.qb.DocType("Marketplace App Plan")
	plan = frappe.qb.DocType("Plan")
	site = frappe.qb.DocType("Site")
	usage_record = frappe.qb.DocType("Usage Record")

	conditions = app_plan.is_free == False  # noqa: E712
	conditions = conditions & (app_sub.app == marketplace_app)

	query = (
		frappe.qb.from_(app_sub)
		.join(app_plan)
		.on(app_sub.marketplace_app_plan == app_plan.name)
		.join(plan)
		.on(app_plan.plan == plan.name)
		.join(site)
		.on(site.name == app_sub.site)
		.join(usage_record)
		.on(usage_record.subscription == app_sub.name)
		.where(conditions)
		.groupby(usage_record.subscription)
		.select(
			frappe.query_builder.functions.Count("*").as_("active_days"),
			app_sub.site,
			site.team.as_("user_contact"),
			app_sub.plan.as_("app_plan"),
			plan.price_usd.as_("price_usd"),
			plan.price_inr.as_("price_inr"),
			app_sub.status,
		)
		.orderby(app_sub.status)
		.orderby(app_sub.creation, order=frappe.qb.desc)
	)

	result = query.run(as_dict=True)

	return result


@frappe.whitelist()
def create_app_plan(marketplace_app: str, plan_data: Dict):
	plan = create_new_plan(marketplace_app, plan_data)
	app_plan_doc = frappe.get_doc(
		{"doctype": "Marketplace App Plan", "app": marketplace_app, "plan": plan.name}
	)

	feature_list = plan_data.get("features")
	reset_features_for_plan(app_plan_doc, feature_list)
	app_plan_doc.insert(ignore_permissions=True)


@frappe.whitelist()
def update_app_plan(app_plan_name: str, updated_plan_data: Dict):
	if not updated_plan_data.get("plan_title"):
		frappe.throw("Plan title is required")

	app_plan_doc = frappe.get_doc("Marketplace App Plan", app_plan_name)
	plan_name = app_plan_doc.plan

	no_of_active_subscriptions = frappe.db.count(
		"Marketplace App Subscription",
		{"app": app_plan_doc.app, "plan": plan_name, "status": "Active"},
	)

	if no_of_active_subscriptions > 0:
		# Someone is on this plan, don't change price for the plan,
		# instead create and link a new plan
		# TODO: Later we have to figure out a way for plan changes
		new_plan = create_new_plan(app_plan_doc.app, updated_plan_data)
		app_plan_doc.plan = new_plan.name
	else:
		plan_doc = frappe.get_doc("Plan", plan_name, for_update=True)
		# Update the price in the plan itself
		plan_doc.update(
			{
				"price_inr": updated_plan_data.get("price_inr"),
				"price_usd": updated_plan_data.get("price_usd"),
				"plan_title": updated_plan_data.get("plan_title", plan_doc.plan_title),
			}
		)
		plan_doc.save(ignore_permissions=True)

	feature_list = updated_plan_data.get("features", [])
	reset_features_for_plan(app_plan_doc, feature_list, save=False)
	app_plan_doc.save(ignore_permissions=True)


def reset_features_for_plan(
	app_plan_doc: MarketplaceAppPlan, feature_list: List[str], save=False
):
	# Clear the already existing features
	app_plan_doc.features = []
	for feature in feature_list:
		if not feature:
			frappe.throw("Feature cannot be empty string")
		app_plan_doc.append("features", {"description": feature})

	if save:
		app_plan_doc.save(ignore_permissions=True)


def create_new_plan(app: str, data: Dict) -> Plan:
	return frappe.get_doc(
		{
			"doctype": "Plan",
			"price_inr": data.get("price_inr"),
			"price_usd": data.get("price_usd"),
			"plan_title": data.get("plan_title"),
			"document_type": "Marketplace App",
			"name": app + f"-plan-{frappe.utils.random_string(6)}",
		}
	).insert(ignore_permissions=True)
