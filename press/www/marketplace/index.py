# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

import frappe


def get_context(context):
	# TODO: Caching, Pagination, Filtering, Sorting
	context.no_cache = 1
	context.apps = frappe.db.sql(
		"""
		SELECT
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
			site.app = marketplace.name
		WHERE
			marketplace.status = "Published"
		GROUP BY
			marketplace.name
		ORDER BY
			total_installs DESC
	""",
		as_dict=True,
	)

	context.metatags = {
		"title": "Frappe Cloud Marketplace",
		"description": "One Click Apps for your Frappe Sites",
		"og:type": "website",
	}
