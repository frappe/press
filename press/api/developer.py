# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from typing import Dict, List
from press.api.site import protected
from press.utils import get_current_team, get_last_doc
from press.press.doctype.marketplace_app.marketplace_app import MarketplaceApp
from press.press.doctype.app_release.app_release import AppRelease
from press.press.doctype.app_release_approval_request.app_release_approval_request import (
	AppReleaseApprovalRequest,
)


@frappe.whitelist()
def get_apps() -> List[Dict]:
	"""Return list of apps developed by the current team"""
	team = get_current_team()
	apps = frappe.get_all(
		"Marketplace App",
		fields=["name", "title", "image", "app", "status", "description"],
		filters={"team": team},
	)

	return apps


@frappe.whitelist()
@protected("Marketplace App")
def get_app(name: str) -> MarketplaceApp:
	"""Return the `Marketplace App` document with name"""
	app: MarketplaceApp = frappe.get_doc("Marketplace App", name)
	return app


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
def releases(app: str) -> List[Dict]:
	"""Return list of App Releases for this `app` in order of creation time"""
	app_releases = frappe.get_all(
		"App Release", filters={"app": app}, fields="*", order_by="creation desc"
	)

	for release in app_releases:
		app_source = frappe.get_doc("App Source", release.source)
		release.source = app_source

	return app_releases


@frappe.whitelist()
def latest_approved_release(app: str) -> AppRelease:
	"""Return the latest app release with `approved` status"""
	return get_last_doc("App Release", {"app": app, "status": "Approved"})


@frappe.whitelist()
def create_approval_request(marketplace_app: str, app_release: str):
	"""Create a new Approval Request for given `app_release`"""
	AppReleaseApprovalRequest.create(marketplace_app, app_release)


@frappe.whitelist()
def cancel_approval_request(marketplace_app: str, app_release: str):
	"""Cancel Approval Request for given `app_release`"""
	approval_requests = frappe.get_all(
		"App Release Approval Request",
		filters={"marketplace_app": marketplace_app, "app_release": app_release},
		pluck="name",
	)

	if len(approval_requests) == 0:
		frappe.throw("No approval request exists for the given app release")

	approval_request: AppReleaseApprovalRequest = frappe.get_doc(
		"App Release Approval Request", approval_requests[0]
	)

	approval_request.cancel()