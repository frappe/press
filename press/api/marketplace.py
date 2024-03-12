# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import json
import frappe

from typing import Dict, List
from frappe.core.utils import find
from press.api.bench import options
from press.api.billing import create_payment_intent_for_prepaid_app
from press.api.site import (
	is_marketplace_app_source,
	is_prepaid_marketplace_app,
	protected,
)
from press.marketplace.doctype.marketplace_app_plan.marketplace_app_plan import (
	MarketplaceAppPlan,
)
from press.press.doctype.app.app import new_app as new_app_doc
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.app_release.app_release import AppRelease
from press.utils import get_current_team, get_last_doc, unique, get_app_tag
from press.press.doctype.marketplace_app.marketplace_app import MarketplaceApp
from press.press.doctype.marketplace_app.marketplace_app import get_plans_for_app
from press.utils.billing import get_frappe_io_connection


@frappe.whitelist()
def options_for_quick_install(marketplace_app: str):
	app_name, title, frappe_approved = frappe.db.get_value(
		"Marketplace App", marketplace_app, ["app", "title", "frappe_approved"]
	)
	candidate_groups = get_candidate_release_groups(marketplace_app, app_name)
	candidate_sites = get_candidate_sites(app_name)
	plans = get_plans_for_app(marketplace_app)

	return {
		"release_groups": candidate_groups,
		"sites": candidate_sites,
		"app_name": app_name,
		"title": title,
		"approved": bool(frappe_approved),
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

	# Attach sources information to marketplace sources
	for source in app.sources:
		source.source_information = frappe.get_doc("App Source", source.source).as_dict()

	return app


@frappe.whitelist()
@protected("Marketplace App")
def deploy_information(name: str):
	"""Return the deploy information for marketplace app `app`"""
	marketplace_app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	return marketplace_app.get_deploy_information()


@frappe.whitelist()
def profile_image_url(app: str) -> str:
	return frappe.db.get_value("Marketplace App", app, "image")


@frappe.whitelist()
def update_app_image() -> str:
	"""Handles App Image Upload"""
	file_content = frappe.local.uploaded_file

	validate_app_image_dimensions(file_content)

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
			"content": file_content,
		}
	)
	_file.save(ignore_permissions=True)
	file_url = _file.file_url
	frappe.db.set_value("Marketplace App", app_name, "image", file_url)

	return file_url


@frappe.whitelist()
def add_app_screenshot() -> str:
	"""Handles App Image Upload"""
	file_content = frappe.local.uploaded_file
	app_name = frappe.form_dict.docname
	app_doc = frappe.get_doc("Marketplace App", app_name)

	_file = frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_field": "image",
			"folder": "Home/Attachments",
			"file_name": frappe.local.uploaded_filename,
			"is_private": 0,
			"content": file_content,
		}
	)
	_file.save(ignore_permissions=True)
	file_url = _file.file_url

	app_doc.append(
		"screenshots",
		{
			"image": file_url,
		},
	)
	app_doc.save(ignore_permissions=True)

	return file_url


@protected("Marketplace App")
@frappe.whitelist()
def remove_app_screenshot(name, file):
	app_doc = frappe.get_doc("Marketplace App", name)

	for i, sc in enumerate(app_doc.screenshots):
		if sc.image == file:
			frappe.delete_doc("File", file)
			app_doc.screenshots.pop(i)
	app_doc.save(ignore_permissions=True)


def validate_app_image_dimensions(file_content):
	"""Throws if image is not a square image, atleast 300x300px in size"""
	from PIL import Image
	from io import BytesIO

	im = Image.open(BytesIO(file_content))
	im_width, im_height = im.size
	if im_width != im_height or im_height < 300:
		frappe.throw("Logo must be a square image atleast 300x300px in size")


@frappe.whitelist()
def update_app_title(name: str, title: str) -> MarketplaceApp:
	"""Update `title` and `category`"""
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	app.title = title
	app.save(ignore_permissions=True)

	return app


@frappe.whitelist()
def update_app_links(name: str, links: Dict) -> None:
	"""Update links related to app"""
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	app.update(links)
	app.save(ignore_permissions=True)


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
def releases(
	filters=None, order_by=None, limit_start=None, limit_page_length=None
) -> List[Dict]:
	"""Return list of App Releases for this `app` and `source` in order of creation time"""

	app_releases = frappe.get_all(
		"App Release",
		filters=filters,
		fields="*",
		order_by=order_by or "creation desc",
		start=limit_start,
		limit=limit_page_length,
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
def latest_approved_release(source: None | str) -> AppRelease:
	"""Return the latest app release with `approved` status"""
	return get_last_doc("App Release", {"source": source, "status": "Approved"})


@frappe.whitelist()
@protected("Marketplace App")
def create_approval_request(name, app_release: str):
	"""Create a new Approval Request for given `app_release`"""
	frappe.get_doc("Marketplace App", name).create_approval_request(app_release)


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

	approval_request = frappe.get_doc("App Release Approval Request", approval_requests[0])

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
				marketplace_app.save(ignore_permissions=True)
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
		"Subscription",
		filters={"site": site, "enabled": 1, "document_type": "Marketplace App"},
		fields=["name", "document_name as app", "enabled", "plan"],
	)

	for subscription in subscriptions:
		marketplace_app_info = frappe.db.get_value(
			"Marketplace App", subscription.app, ["title", "image"], as_dict=True
		)

		subscription.app_title = marketplace_app_info.title
		subscription.app_image = marketplace_app_info.image
		subscription.plan_info = frappe.db.get_value(
			"Marketplace App Plan", subscription.plan, ["price_usd", "price_inr"], as_dict=True
		)
		subscription.is_free = frappe.db.get_value(
			"Marketplace App Plan", subscription.marketplace_app_plan, "is_free"
		)
		subscription.billing_type = is_prepaid_marketplace_app(subscription.app)

	return subscriptions


@frappe.whitelist()
def get_app_plans(app: str, include_disabled=True):
	return get_plans_for_app(app, include_disabled=include_disabled)


@frappe.whitelist()
def get_app_info(app: str):
	return frappe.db.get_value(
		"Marketplace App", app, ["name", "title", "image", "team"], as_dict=True
	)


@frappe.whitelist()
def get_apps_with_plans(apps, release_group: str):

	if isinstance(apps, str):
		apps = json.loads(apps)

	apps_with_plans = []

	# Make sure it is a marketplace app
	m_apps = frappe.db.get_all(
		"Marketplace App", filters={"app": ("in", apps)}, fields=["name", "title", "image"]
	)

	frappe_version = frappe.db.get_value("Release Group", release_group, "version")
	for app in m_apps:
		app_source = frappe.db.get_value(
			"Release Group App", {"parent": release_group, "app": app.name}, "source"
		)
		if is_marketplace_app_source(app_source):
			plans = get_plans_for_app(app.name, frappe_version)
		else:
			plans = []

		if len(plans) > 0:
			apps_with_plans.append(app)

	return apps_with_plans


@frappe.whitelist()
def change_app_plan(subscription, new_plan):
	is_free = frappe.db.get_value("Marketplace App Plan", new_plan, "price_usd") <= 0
	if not is_free:
		team = get_current_team(get_doc=True)
		if not team.can_install_paid_apps():
			frappe.throw(
				"You cannot upgrade to paid plan on Free Credits. Please buy credits before trying to upgrade plan."
			)

	subscription = frappe.get_doc("Subscription", subscription)
	subscription.enabled = 1
	subscription.plan = new_plan
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
def update_publisher_profile(profile_data=None):
	"""Update if exists, otherwise create"""
	team = get_current_team()

	publisher_profile_name = frappe.db.exists(
		"Marketplace Publisher Profile", {"team": team}
	)

	if publisher_profile_name:
		profile_doc = frappe.get_doc(
			"Marketplace Publisher Profile", publisher_profile_name, for_update=True
		)
		profile_doc.update(profile_data or {})
		profile_doc.save(ignore_permissions=True)
	else:
		profile_doc = frappe.get_doc({"doctype": "Marketplace Publisher Profile"})
		profile_doc.team = team
		profile_doc.update(profile_data or {})
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
def submit_developer_reply(review, reply):
	return frappe.get_doc(
		{
			"doctype": "Developer Review Reply",
			"review": review,
			"description": reply,
			"developer": frappe.session.user,
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def get_subscriptions_list(marketplace_app: str) -> List:
	app_sub = frappe.qb.DocType("Subscription")
	app_plan = frappe.qb.DocType("Marketplace App Plan")
	site = frappe.qb.DocType("Site")
	usage_record = frappe.qb.DocType("Usage Record")
	team = frappe.qb.DocType("Team")

	conditions = app_plan.price_usd > 0  # noqa: E712
	conditions = conditions & (app_sub.document_name == marketplace_app)

	query = (
		frappe.qb.from_(app_sub)
		.left_join(team)
		.on(app_sub.team == team.name)
		.join(app_plan)
		.on(app_sub.plan == app_plan.name)
		.join(site)
		.on(site.name == app_sub.site)
		.join(usage_record)
		.on(usage_record.subscription == app_sub.name)
		.where(conditions)
		.groupby(usage_record.subscription)
		.select(
			frappe.query_builder.functions.Count("*").as_("active_days"),
			app_sub.site,
			team.user.as_("user_contact"),
			app_sub.plan.as_("app_plan"),
			app_plan.price_usd.as_("price_usd"),
			app_plan.price_inr.as_("price_inr"),
			app_sub.enabled,
		)
		.orderby(app_sub.enabled)
		.orderby(app_sub.creation, order=frappe.qb.desc)
	)

	result = query.run(as_dict=True)

	return result


@frappe.whitelist()
def create_app_plan(marketplace_app: str, plan_data: Dict):
	app_plan_doc = frappe.get_doc(
		{
			"doctype": "Marketplace App Plan",
			"app": marketplace_app,
			"title": plan_data.get("title"),
			"price_inr": plan_data.get("price_inr"),
			"price_usd": plan_data.get("price_usd"),
		}
	)

	feature_list = plan_data.get("features")
	reset_features_for_plan(app_plan_doc, feature_list)
	return app_plan_doc.insert(ignore_permissions=True)


@frappe.whitelist()
def update_app_plan(app_plan_name: str, updated_plan_data: Dict):

	if not updated_plan_data.get("title"):
		frappe.throw("Plan title is required")

	app_plan_doc = frappe.get_doc("Marketplace App Plan", app_plan_name)

	no_of_active_subscriptions = frappe.db.count(
		"Subscription",
		{
			"document_type": "Marketplace App",
			"document_name": app_plan_doc.app,
			"plan": app_plan_doc.name,
			"enabled": True,
		},
	)

	if (
		updated_plan_data["price_inr"] != app_plan_doc.price_inr
		or updated_plan_data["price_usd"] != app_plan_doc.price_usd
	) and no_of_active_subscriptions > 0:
		# Someone is on this plan, don't change price for the plan,
		# instead create and link a new plan
		# TODO: Later we have to figure out a way for plan changes
		frappe.throw(
			"Plan is already in use, cannot update the plan. Please contact support to proceed."
		)

	app_plan_doc.update(
		{
			"price_inr": updated_plan_data.get("price_inr"),
			"price_usd": updated_plan_data.get("price_usd"),
			"title": updated_plan_data.get("title", app_plan_doc.title),
		}
	)
	app_plan_doc.save(ignore_permissions=True)

	feature_list = updated_plan_data.get("features", [])
	reset_features_for_plan(app_plan_doc, feature_list, save=False)
	app_plan_doc.enabled = updated_plan_data.get("enabled", True)
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


@frappe.whitelist()
def get_payouts_list() -> List[Dict]:
	team = get_current_team()
	payouts = frappe.get_all(
		"Payout Order",
		filters={"recipient": team},
		fields=[
			"name",
			"status",
			"period_end",
			"mode_of_payment",
			"net_total_inr",
			"net_total_usd",
		],
		order_by="period_end desc",
	)

	return payouts


@frappe.whitelist()
def get_payout_details(name: str) -> Dict:
	order_items = frappe.get_all(
		"Payout Order Item",
		filters={"parent": name},
		fields=[
			"name",
			"document_name",
			"site",
			"rate",
			"plan",
			"total_amount",
			"currency",
			"net_amount",
			"gateway_fee",
			"quantity",
			"commission",
		],
		order_by="idx",
	)

	payout_order = frappe.db.get_value(
		"Payout Order",
		name,
		["status", "due_date", "mode_of_payment", "net_total_inr", "net_total_usd"],
		as_dict=True,
	)

	grouped_items = {"usd_items": [], "inr_items": [], **payout_order}
	for item in order_items:
		if item.currency == "INR":
			grouped_items["inr_items"].append(item)
		else:
			grouped_items["usd_items"].append(item)

	return grouped_items


@frappe.whitelist(allow_guest=True)
def prepaid_saas_payment(
	name, app, site, plan, amount, credits, payment_option, renewal, subscriptions=None
):
	if renewal:
		line_items = [
			{
				"app": sub["app"],
				"plan": sub["marketplace_app_plan"],
				"subscription": sub["name"],
				"amount": sub["selected_plan"]["amount"],
				"quantity": payment_option,
			}
			for sub in subscriptions
		]
	else:
		line_items = [
			{
				"app": app,
				"plan": plan,
				"subscription": name,
				"amount": amount,
				"quantity": payment_option,
			}
		]
	metadata = {
		"payment_for": "prepaid_marketplace",
		"line_items": json.dumps(line_items),
		"site": site,
		"credits": credits,
	}
	return create_payment_intent_for_prepaid_app(int(amount), metadata)


@frappe.whitelist(allow_guest=True)
def get_plan(name):
	plan, gst, discount_percent, block_monthly = frappe.db.get_value(
		"Marketplace App Plan", name, ["plan", "gst", "discount_percent", "block_monthly"]
	)
	currency = get_current_team(True).currency.lower()
	title, amount = frappe.db.get_value("Plan", plan, ["plan_title", f"price_{currency}"])

	return {
		"title": title,
		"amount": amount,
		"gst": gst,
		"discount_percent": get_discount_percent(name, discount_percent),
		"block_monthly": block_monthly,
	}


def get_discount_percent(plan, discount=0.0):
	team = get_current_team(True)
	partner_discount_percent = {
		"Gold": 50.0,
		"Silver": 40.0,
		"Bronze": 30.0,
	}

	if team.erpnext_partner and frappe.get_value(
		"Marketplace App Plan", plan, "partner_discount"
	):
		client = get_frappe_io_connection()
		response = client.session.post(
			f"{client.url}/api/method/partner_relationship_management.api.get_partner_type",
			data={"email": team.partner_email},
			headers=client.headers,
		)
		if response.ok:
			res = response.json()
			partner_type = res.get("message")
			if partner_type is not None:
				discount = partner_discount_percent.get(partner_type) or discount

	return discount


@frappe.whitelist(allow_guest=True)
def login_via_token(token, team, site):

	if not token or not isinstance(token, str):
		frappe.throw("Invalid Token")

	team = team.replace(" ", "+")
	token_exists = frappe.db.exists(
		"Saas Remote Login",
		{
			"team": team,
			"token": token,
			"status": "Attempted",
			"expires_on": (">", frappe.utils.now()),
		},
	)

	if token_exists:
		doc = frappe.get_doc("Saas Remote Login", token_exists)
		doc.status = "Used"
		doc.save(ignore_permissions=True)
		frappe.local.login_manager.login_as(team)
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = f"/dashboard/sites/{site}/overview"
	else:
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/dashboard/login?showRemoteLoginError=true"


@frappe.whitelist()
def subscriptions():
	team = get_current_team(True)
	free_plans = frappe.get_all(
		"Marketplace App Plan", {"price_usd": ("<=", 0)}, pluck="name"
	)
	subscriptions = frappe.get_all(
		"Subscription",
		{
			"team": team.name,
			"enabled": 1,
			"plan": ("not in", free_plans),
		},
		["name", "document_name as app", "site", "plan"],
	)

	for sub in subscriptions:
		sub["available_plans"] = get_plans_for_app(sub["app"])
		for ele in sub["available_plans"]:
			ele["amount"] = ele[f"price_{team.currency.lower()}"]
			if ele["name"] == sub["plan"]:
				sub["selected_plan"] = ele

	return subscriptions


@protected("App Source")
@frappe.whitelist()
def branches(name):
	from press.api.github import branches as git_branches

	app_source = frappe.get_doc("App Source", name)
	installation_id = app_source.github_installation_id
	repo_owner = app_source.repository_owner
	repo_name = app_source.repository

	return git_branches(repo_owner, repo_name, installation_id)


@protected("Marketplace App")
@frappe.whitelist()
def change_branch(name, source, version, to_branch):
	app = frappe.get_doc("Marketplace App", name)
	app.change_branch(source, version, to_branch)


@protected("Marketplace App")
@frappe.whitelist()
def options_for_version(name, source):
	frappe_version = frappe.get_all("Frappe Version", {"public": True}, pluck="name")
	added_versions = frappe.get_all(
		"Marketplace App Version", {"parent": name}, pluck="version"
	)
	branchesList = branches(source)
	versions = list(set(frappe_version).difference(set(added_versions)))
	branchesList = [branch["name"] for branch in branchesList]

	return [{"version": version, "branch": branchesList} for version in versions]


@protected("Marketplace App")
@frappe.whitelist()
def add_version(name, branch, version):
	app = frappe.get_doc("Marketplace App", name)
	app.add_version(version, branch)


@protected("Marketplace App")
@frappe.whitelist()
def remove_version(name, version):
	app = frappe.get_doc("Marketplace App", name)
	app.remove_version(version)


@protected("Marketplace App")
@frappe.whitelist()
def review_steps(name):
	app = frappe.get_doc("Marketplace App", name)
	return [
		{"step": "Add a logo for your app", "completed": True if app.image else False},
		{
			"step": "Add links",
			"completed": True if app.website and app.support and app.documentation else False,
		},
		{
			"step": "Update description and long description",
			"completed": True if app.description else False,
		},
		{
			"step": "Publish a release for version",
			"completed": True
			if frappe.db.exists("App Release Approval Request", {"marketplace_app": name})
			else False,
		},
	]


@protected("Marketplace App")
@frappe.whitelist()
def start_review(name):
	# TODO: Start security check and auto deploy process here
	app = frappe.get_doc("Marketplace App", name)
	app.status = "In Review"
	app.save(ignore_permissions=True)


@protected("Marketplace App")
@frappe.whitelist()
def communication(name):
	comm = frappe.qb.DocType("Communication")
	user = frappe.qb.DocType("User")
	query = (
		frappe.qb.from_(comm)
		.left_join(user)
		.on(comm.sender == user.email)
		.select(comm.sender, comm.content, comm.communication_date, user.user_image)
		.where((comm.reference_doctype == "Marketplace App") & (comm.reference_name == name))
		.orderby(comm.creation, order=frappe.qb.desc)
	)
	res = query.run(as_dict=True)
	return res


@protected("Marketplace App")
@frappe.whitelist()
def add_reply(name, message):
	doctype = "Marketplace App"
	app = frappe.get_doc(doctype, name)
	recipients = ", ".join(list(app.get_assigned_users()) or [])
	doc = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"reference_doctype": doctype,
			"reference_name": name,
			"subject": f"Marketplace App Review: {name}, New message!",
			"sender": frappe.session.user,
			"content": message,
			"is_notification": True,
			"recipients": recipients,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.send_email()


@protected("Marketplace App")
@frappe.whitelist()
def fetch_readme(name):
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	app.long_description = app.fetch_readme()
	app.save()


@frappe.whitelist(allow_guest=True)
def get_marketplace_apps():
	apps = frappe.cache().get_value("marketplace_apps")
	if not apps:
		apps = frappe.get_all(
			"Marketplace App", {"status": "Published"}, ["name", "title", "route"]
		)
		frappe.cache().set_value("marketplace_apps", apps, expires_in_sec=60 * 60 * 24 * 7)
	return apps
