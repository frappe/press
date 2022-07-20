# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def get_context(context):
	# TODO: Caching, Pagination, Filtering, Sorting
	context.no_cache = 1
	all_published_apps = frappe.db.sql(
		"""
		SELECT
			marketplace.name,
			marketplace.title,
			marketplace.image,
			marketplace.route,
			marketplace.description,
			COUNT(*) AS total_installs
		FROM
			`tabMarketplace App` marketplace
		LEFT JOIN
			`tabSite App` site
		ON
			site.app = marketplace.app
		WHERE
			marketplace.status = "Published"
		GROUP BY
			marketplace.name
		ORDER BY
			total_installs DESC
	""",
		as_dict=True,
	)

	context.apps = all_published_apps

	featured_apps = frappe.get_all(
		"Featured App",
		filters={"parent": "Marketplace Settings"},
		pluck="app",
		order_by="idx",
	)

	context.featured_apps = sorted(
		filter(lambda x: x.name in featured_apps, all_published_apps),
		key=lambda y: featured_apps.index(y.name),
	)

	context.metatags = {
		"title": "Frappe Cloud Marketplace",
		"description": "One Click Apps for your Frappe Sites",
		"og:type": "website",
	}
