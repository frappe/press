# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def get_context(context):
	context.no_cache = 1
	context.apps = {}

	featured = frappe.get_all(
		"Featured App",
		filters={"parent": "Marketplace Settings", "parentfield": "featured_apps"},
		pluck="app",
		order_by="idx",
	)
	context.apps["Featured Apps"] = sorted(
		filter(
			lambda x: x.name in featured,
			frappe.get_all(
				"Marketplace App",
				{"name": ("in", featured), "status": "Published"},
				["name", "title", "description", "image", "route"],
			),
		),
		key=lambda y: featured.index(y.name),
	)

	context.apps["Most Installed"] = frappe.db.sql(
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
		LIMIT 6
	""",
		as_dict=True,
	)

	context.apps["Recently Added"] = frappe.get_all(
		"Marketplace App",
		{"status": "Published"},
		["name", "title", "description", "image", "route"],
		order_by="creation DESC",
		limit=6,
	)

	context.categories = sorted(
		frappe.db.get_all("Marketplace App Categories", pluck="category", distinct=True)
	)
	context.metatags = {
		"title": "Frappe Cloud Marketplace",
		"description": "One Click Apps for your Frappe Sites",
		"og:type": "website",
	}


@frappe.whitelist(allow_guest=True)
def search(query, offset=0, limit=20):
	return frappe.qb.get_query(
		"Marketplace App",
		filters={
			"status": "Published",
			"title": ("like", f"%{query}%"),
		},
		fields=["name", "image", "title", "description", "image", "route"],
		offset=offset,
		limit=limit,
	).run(as_dict=1)


@frappe.whitelist(allow_guest=True)
def filter_by_category(category):
	return frappe.db.sql(
		"""
		SELECT
			marketplace.name,
			marketplace.title,
			marketplace.image,
			marketplace.route,
			marketplace.description
		FROM
			`tabMarketplace App` marketplace
		LEFT JOIN
			`tabMarketplace App Categories` category
		ON
			category.parent = marketplace.name
		WHERE
			marketplace.status = "Published"
		AND
			category.category = %s
		ORDER BY marketplace.frappe_approved DESC
	""",
		category,
		as_dict=True,
	)
