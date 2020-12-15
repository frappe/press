# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def get_context(context):
	# TODO: Caching, Pagination, Filtering, Sorting
	context.no_cache = 1
	context.apps = frappe.get_all(
		"Marketplace App",
		filters={"status": "Published"},
		order_by="creation asc",
		fields=["*"],
	)
