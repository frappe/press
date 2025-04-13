# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class BenchApp(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link
		hash: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		release: DF.Link
		source: DF.Link
	# end: auto-generated types

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		if not filters or not (parent := filters.get("parent")):
			return query

		AppSource = frappe.qb.DocType("App Source")
		AppRelease = frappe.qb.DocType("App Release")
		Bench = frappe.qb.DocType("Bench")
		BenchApp = frappe.qb.DocType("Bench App")

		q = (
			frappe.qb.from_(BenchApp)
			.join(Bench)
			.on(Bench.name == BenchApp.parent)
			.join(AppRelease)
			.on(BenchApp.release == AppRelease.name)
			.join(AppSource)
			.on(BenchApp.source == AppSource.name)
			.select(
				BenchApp.app,
				BenchApp.hash,
				BenchApp.release,
				AppRelease.message.as_("commit_message"),
				AppSource.app_title.as_("title"),
				AppSource.branch,
				AppSource.repository_url,
			)
			.where(BenchApp.parent == parent)
		)

		if owner := filters.get("repository_owner"):
			q = q.where(AppSource.repository_owner == owner)

		if branch := filters.get("branch"):
			q = q.where(AppSource.branch == branch)

		apps = q.run(as_dict=True)

		# Apply is_app_patched flag to installed_apps
		app_names = [a["app"] for a in apps]
		patched_apps = frappe.get_all(
			"App Patch",
			fields=["app"],
			filters={
				"bench": parent,
				"app": ["in", app_names],
			},
			pluck="app",
		)

		for app in apps:
			if app["app"] in patched_apps:
				app["is_app_patched"] = True
		return apps
