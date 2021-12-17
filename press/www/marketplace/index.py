# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe

from press.press.doctype.marketplace_app.marketplace_app import (
	get_total_installs_for_app,
)


def get_context(context):
	# TODO: Caching, Pagination, Filtering, Sorting
	context.no_cache = 1
	context.apps = frappe.get_all(
		"Marketplace App",
		filters={"status": "Published"},
		order_by="creation asc",
		fields=["*"],
	)

	for app in context.apps:
		app.total_installs = get_total_installs_for_app(app.name)

	context.metatags = {
		"title": "Frappe Cloud Marketplace",
		"description": "One Click Apps for your Frappe Sites",
		"og:type": "website",
	}
