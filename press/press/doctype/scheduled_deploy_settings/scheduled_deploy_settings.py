# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.press.doctype.bench_update.bench_update import get_bench_update
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.scheduled_deploy_group.scheduled_deploy_group import WEEKDAYS
from press.utils import log_error


class ScheduledDeploySettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.scheduled_deploy_group.scheduled_deploy_group import ScheduledDeployGroup

		enabled: DF.Check
		groups: DF.Table[ScheduledDeployGroup]
	# end: auto-generated types

	def validate(self):
		seen = set()
		for row in self.groups:
			if not 0 <= row.hour <= 23:
				frappe.throw(f"Row {row.idx}: Hour must be between 0 and 23")
			if not any(row.get(day) for day in WEEKDAYS):
				frappe.throw(f"Row {row.idx}: Select at least one day for {row.release_group}")
			if row.release_group in seen:
				frappe.throw(f"Row {row.idx}: {row.release_group} is listed more than once")
			seen.add(row.release_group)

	@frappe.whitelist()
	def deploy_now(self, release_group: str) -> str | None:
		"""Deploy a listed group right away, with the same checks as a scheduled deploy."""
		if release_group not in {row.release_group for row in self.groups}:
			frappe.throw(f"{release_group} is not listed in Scheduled Deploy Settings")
		return deploy_release_group(release_group)


def deploy_scheduled_release_groups():
	"""Deploy every group due this hour. A failing group is logged and the rest still run."""
	settings = ScheduledDeploySettings("Scheduled Deploy Settings")
	if not settings.enabled:
		return

	now = frappe.utils.now_datetime()
	for row in settings.groups:
		if not row.is_due(now):
			continue
		try:
			deploy_release_group(row.release_group)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error("Scheduled Deploy Error", release_group=row.release_group)


def deploy_release_group(name: str) -> str | None:
	"""Deploy all app updates of a release group, if it has any, and return the build started."""
	group = ReleaseGroup("Release Group", name)
	if not group.deploy_information().update_available:
		return None

	apps = group.get_apps_to_update(apps_to_update=None)
	return get_bench_update(name, apps, ignore_permissions=True).deploy(
		run_will_fail_check=True, ignore_permissions=True
	)
