# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.utils import get_current_team

if TYPE_CHECKING:
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.release_group.release_group import ReleaseGroup


class BenchUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.bench_site_update.bench_site_update import BenchSiteUpdate
		from press.press.doctype.bench_update_app.bench_update_app import BenchUpdateApp
		from press.press.doctype.release_group.release_group import ReleaseGroup

		apps: DF.Table[BenchUpdateApp]
		bench: DF.Link | None
		candidate: DF.Link | None
		group: DF.Link
		is_inplace_update: DF.Check
		sites: DF.Table[BenchSiteUpdate]
	# end: auto-generated types

	def validate(self):
		if not self.is_new():
			return

		self.validate_pending_updates()
		self.validate_pending_site_updates()

		if self.is_inplace_update:
			self.validate_inplace_update()

	def before_save(self):
		if not self.is_inplace_update:
			return

		site = self.sites[0].site  # validation should throw if no sites
		self.bench = frappe.get_value("Site", site, "bench")

	def validate_pending_updates(self):
		if frappe.get_doc("Release Group", self.group).deploy_in_progress:
			frappe.throw("A deploy for this bench is already in progress", frappe.ValidationError)

	def validate_pending_site_updates(self):
		for site in self.sites:
			if frappe.db.exists(
				"Site Update",
				{"site": site.site, "status": ("in", ("Pending", "Running"))},
			):
				frappe.throw("An update is already pending for this site", frappe.ValidationError)

	def validate_inplace_update(self):
		sites = [s.site for s in self.sites if s.site]
		if len(sites) == 0:
			frappe.throw(
				"In place update cannot be run without a site being selected",
			)

		benches = frappe.get_all(
			"Site",
			fields=["bench"],
			filters={"name": ["in", sites]},
			pluck="bench",
		)

		if len(set(benches)) > 1:
			frappe.throw(
				"In place update can be used only to update single benches",
				frappe.ValidationError,
			)

	def deploy(self, run_will_fail_check=False) -> str:
		rg: ReleaseGroup = frappe.get_doc("Release Group", self.group)
		candidate = rg.create_deploy_candidate(self.apps, run_will_fail_check)
		deploy = candidate.schedule_build_and_deploy()

		self.candidate = candidate.name
		self.save()

		if not isinstance(candidate.name, str):
			raise Exception(
				f"Invalid name found for deploy candidate '{candidate.name}' of type {type(candidate.name)}"
			)

		return deploy["name"]

	def update_inplace(self) -> str:
		if not self.is_inplace_update:
			raise Exception("In place update flag is not set, aborting in place update.")

		bench: "Bench" = frappe.get_doc("Bench", self.bench)
		sites = [s.site for s in self.sites]

		return bench.update_inplace(self.apps, sites)

	def update_sites_on_server(self, bench, server):
		# This method gets called multiple times concurrently when a new candidate is deployed
		# Avoid saving the doc to avoid TimestampMismatchError
		if frappe.get_value("Bench", bench, "status") != "Active":
			return

		for row in self.sites:
			if row.server != server:
				continue

			# Don't try to update if the site is already on another bench
			# It already could be on newest bench and Site Update couldn't be scheduled
			# In any case our job was to move site to a newer than this, which is already done
			current_site_bench = frappe.get_value("Site", row.site, "bench")
			if row.source_candidate != frappe.get_value("Bench", current_site_bench, "candidate"):
				frappe.db.set_value("Bench Site Update", row.name, "status", "Success")
				frappe.db.commit()
				continue

			if row.status == "Pending" and not row.site_update:
				try:
					if frappe.get_all(
						"Site Update",
						{"site": row.site, "status": ("in", ("Pending", "Running", "Failure"))},
						ignore_ifnull=True,
						limit=1,
					):
						continue
					site_update = frappe.get_doc("Site", row.site).schedule_update(
						skip_failing_patches=row.skip_failing_patches, skip_backups=row.skip_backups
					)
					frappe.db.set_value("Bench Site Update", row.name, "site_update", site_update)
					frappe.db.commit()
				except Exception:
					# Rollback the failed attempt and set status to Failure
					# So, we don't try again
					# TODO: Add Notifications
					frappe.db.rollback()
					frappe.db.set_value("Bench Site Update", row.name, "status", "Failure")
					traceback = frappe.get_traceback(with_context=True)
					comment = f"Failed to schedule update for {row.site} <br><br><pre><code>{traceback}</pre></code>"
					self.add_comment(text=comment)
					frappe.db.commit()


def get_bench_update(
	name: str,
	apps: list,
	sites: str | list[str] | None = None,
	is_inplace_update: bool = False,
) -> BenchUpdate:
	if sites is None:
		sites = []

	current_team = get_current_team()
	rg_team = frappe.db.get_value("Release Group", name, "team")

	if rg_team != current_team:
		frappe.throw("Bench can only be deployed by the bench owner", exc=frappe.PermissionError)

	bench_update: "BenchUpdate" = frappe.get_doc(
		{
			"doctype": "Bench Update",
			"group": name,
			"apps": apps,
			"sites": [
				{
					"site": site["name"],
					"server": site["server"],
					"skip_failing_patches": site["skip_failing_patches"],
					"skip_backups": site["skip_backups"],
					"source_candidate": frappe.get_value("Bench", site["bench"], "candidate"),
				}
				for site in sites
			],
			"is_inplace_update": is_inplace_update,
		}
	).insert(ignore_permissions=True)
	return bench_update
