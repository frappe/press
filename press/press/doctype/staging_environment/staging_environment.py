# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.site.site import Site


class StagingEnvironment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		expiry_time: DF.Datetime | None
		site: DF.Link
		site_backup: DF.Link | None
		site_creation_method: DF.Literal["New Site", "Restore From Backup"]
		staging_release_group: DF.Link | None
		staging_site: DF.Link | None
		team: DF.Link
	# end: auto-generated types

	def validate(self):
		if self.site_creation_method == "Restore From Backup" and not self.site_backup:
			frappe.throw("Please select a site backup")

		if not self.expiry_time:
			self.expiry_time = frappe.utils.now_datetime() + timedelta(hours=24)


	@frappe.whitelist()
	def create_release_group(self):
		if self.staging_release_group:
			frappe.throw("Staging release group already exists")

		site = frappe.get_doc("Site", self.site)
		group = frappe.get_doc("Release Group", site.group)

		# create staging release group by copying the current release group
		group_id = group.name[6:]
		staging_group = frappe.get_doc(
			{
				"doctype": "Release Group",
				"title": f"Staging {group_id}",
				"team": self.team,
				"public": 0,
				"enabled": 1,
				"version": group.version,
				"dependencies": group.dependencies,
				"is_redisearch_enabled": group.is_redisearch_enabled,
				"servers": [
					{
						"server": server.server,
						"default": server.default,
					}
					for server in group.servers
				], # TODO: do staging deployment to some specific servers instead of team's release group server
				"apps": group.apps,
				"staging": 1,
			}
		).insert(ignore_permissions=True)

		candidate = staging_group.create_deploy_candidate()
		candidate.schedule_build_and_deploy()
		self.staging_release_group = staging_group.name
		self.save()


	def create_site(self, bench:str):
		if self.staging_site:
			frappe.throw("Staging site already exists")
			return
		bench: Bench = frappe.get_doc("Bench", bench)
		site: Site = frappe.get_doc("Site", self.site)
		staging_site = frappe.get_doc({
			"doctype": "Site",
			"subdomain": f"staging-{self.name}",
			"domain": site.domain,
			"server": bench.server,
			"bench": bench.name,
			"group": bench.group,
			"cluster": bench.cluster,
			"team": site.team,
			"plan": site.plan, # TODO: set plan to staging plan configured in press settings
			"apps": [{"app": app.app} for app in site.apps],
			"skip_auto_updates": 1,
			"skip_scheduled_backups": 1, # disable backups for staging sites
			"staging": 1,
		}).insert(ignore_permissions=True)
		self.staging_site = staging_site.name
		self.save()

	def delete_site(self):
		pass
