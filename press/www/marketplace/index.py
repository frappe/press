# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import Order
from frappe.query_builder.functions import Count


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

	MarketplaceApp = frappe.qb.DocType("Marketplace App")
	SiteApp = frappe.qb.DocType("Site App")
	total_installs = Count("*").as_("total_installs")
	context.apps["Most Installed"] = (
		frappe.qb.from_(MarketplaceApp)
		.left_join(SiteApp)
		.on(SiteApp.app == MarketplaceApp.app)
		.select(
			MarketplaceApp.name,
			MarketplaceApp.title,
			MarketplaceApp.image,
			MarketplaceApp.route,
			MarketplaceApp.description,
			total_installs,
		)
		.where(MarketplaceApp.status == "Published")
		.groupby(MarketplaceApp.name)
		.orderby(total_installs, order=Order.desc)
		.limit(6)
		.run(as_dict=True)
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
def search(query: str, offset: int = 0, limit: int = 20):
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
	MarketplaceApp = frappe.qb.DocType("Marketplace App")
	Category = frappe.qb.DocType("Marketplace App Categories")
	return (
		frappe.qb.from_(MarketplaceApp)
		.left_join(Category)
		.on(Category.parent == MarketplaceApp.name)
		.select(
			MarketplaceApp.name,
			MarketplaceApp.title,
			MarketplaceApp.image,
			MarketplaceApp.route,
			MarketplaceApp.description,
		)
		.where((MarketplaceApp.status == "Published") & (Category.category == category))
		.orderby(MarketplaceApp.frappe_approved, order=Order.desc)
		.run(as_dict=True)
	)
