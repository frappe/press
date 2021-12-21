# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

import frappe

from press.press.doctype.marketplace_app.marketplace_app import (
	get_total_installs_for_app,
)


def get_context(context):
	# TODO: Caching, Pagination, Filtering, Sorting
	context.no_cache = 1
	context.apps = frappe.get_all(
		"Marketplace App", filters={"status": "Published"}, fields=["*"],
	)

	for app in context.apps:
		app.total_installs = get_total_installs_for_app(app.name)

	# For the time being, sort by number of installs
	context.apps.sort(key=lambda x: x.total_installs)

	context.metatags = {
		"title": "Frappe Cloud Marketplace",
		"description": "One Click Apps for your Frappe Sites",
		"og:type": "website",
	}
