# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from datetime import datetime

BACKUP_JOB_TYPE = "Backup Site"
FAILED_JOB_STATUSES = ("Failure", "Delivery Failure")
# A pending or running job may still succeed, so its site is not flagged yet
UNFLAGGED_JOB_STATUSES = ("Success", "Pending", "Running")
NO_SUCCESS_WINDOW_DAYS = 3


class BackupDailyAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.backup_daily_audit_site.backup_daily_audit_site import BackupDailyAuditSite

		audit_date: DF.Date
		failed_jobs: DF.Int
		failed_site_count: DF.Int
		failed_sites: DF.Table[BackupDailyAuditSite]
		sites_without_success: DF.Table[BackupDailyAuditSite]
		sites_without_success_count: DF.Int
		success_rate: DF.Percent
		successful_jobs: DF.Int
	# end: auto-generated types

	def validate(self):
		self.failed_site_count = len(self.failed_sites)
		self.sites_without_success_count = len(self.sites_without_success)

	def collect(self):
		from press.press.doctype.site_backup.site_backup import get_max_failed_backup_attempts

		self.audit_date = frappe.utils.today()
		self.set_job_counts()
		failed_sites = get_sites_with_all_backup_attempts_failed(get_max_failed_backup_attempts())
		sites_without_success = get_sites_without_successful_backup_job()
		details = get_site_details([row.site for row in failed_sites] + sites_without_success)
		for row in failed_sites:
			self.append("failed_sites", {**details[row.site], "failed_backups": row.failures})
		for site in sites_without_success:
			self.append("sites_without_success", details[site])

	def set_job_counts(self):
		"""Backup Site agent jobs created in the last 24h that have finished, by outcome."""
		counts = dict(
			frappe.get_all(
				"Agent Job",
				filters={
					"job_type": BACKUP_JOB_TYPE,
					"status": ("in", ["Success", *FAILED_JOB_STATUSES]),
					"creation": (">=", frappe.utils.add_days(None, -1)),
				},
				fields=["status", "count(name) as jobs"],
				group_by="status",
				as_list=True,
			)
		)
		self.successful_jobs = counts.get("Success", 0)
		self.failed_jobs = sum(counts.get(status, 0) for status in FAILED_JOB_STATUSES)
		finished_jobs = self.successful_jobs + self.failed_jobs
		self.success_rate = self.successful_jobs / finished_jobs * 100 if finished_jobs else 0


def record_backup_daily_audit() -> None:
	audit: BackupDailyAudit = frappe.new_doc("Backup Daily Audit")
	audit.collect()
	# A site renamed or deleted since its backup failed must not block the audit
	audit.flags.ignore_links = True
	audit.insert(ignore_permissions=True)


def get_sites_with_all_backup_attempts_failed(max_attempts: int) -> list[frappe._dict]:
	"""Sites that hit the daily failed backup limit, the same limit that emails the team."""
	failures_by_site = frappe.get_all(
		"Site Backup",
		filters={
			"status": ("in", ["Failure", "Delivery Failure"]),
			"creation": (">=", frappe.utils.add_days(None, -1)),
		},
		fields=["site", "count(name) as failures"],
		group_by="site",
		order_by="failures desc, site asc",
	)
	return [row for row in failures_by_site if row.failures >= max_attempts]


def get_sites_without_successful_backup_job() -> list[str]:
	"""Sites due a scheduled backup with no successful, pending or running backup job in the window."""
	since = frappe.utils.add_days(None, -NO_SUCCESS_WINDOW_DAYS)
	sites_with_jobs = frappe.get_all(
		"Agent Job",
		filters={
			"job_type": BACKUP_JOB_TYPE,
			"status": ("in", UNFLAGGED_JOB_STATUSES),
			"creation": (">=", since),
		},
		pluck="site",
		distinct=True,
	)
	# A site deactivated for part of the window was not due a backup all along
	activated_sites = frappe.get_all(
		"Site Activity", {"action": "Activate Site", "creation": (">=", since)}, pluck="site"
	)
	return sorted(set(get_sites_due_scheduled_backups(since)) - set(sites_with_jobs) - set(activated_sites))


def get_sites_due_scheduled_backups(created_before: datetime) -> list[str]:
	servers = frappe.get_all("Server", {"status": "Active", "skip_scheduled_backups": False}, pluck="name")
	return frappe.get_all(
		"Site",
		{
			"status": "Active",
			"creation": ("<=", created_before),
			"is_standby": False,
			"plan": ("not like", "%Trial"),
			"server": ("in", servers),
			"skip_scheduled_logical_backups": False,
		},
		pluck="name",
	)


def get_site_details(site_names: list[str]) -> dict[str, dict]:
	"""Server, team, plan and last successful backup of each site, as audit rows."""
	if not site_names:
		return {}

	sites = {
		site.name: site
		for site in frappe.get_all("Site", {"name": ("in", site_names)}, ["name", "server", "team", "plan"])
	}
	last_successes = dict(
		frappe.get_all(
			"Site Backup",
			filters={"site": ("in", site_names), "status": "Success"},
			fields=["site", "max(creation) as last_success"],
			group_by="site",
			as_list=True,
		)
	)
	details = {}
	for name in site_names:
		site = sites.get(name) or frappe._dict()
		details[name] = {
			"site": name,
			"server": site.server,
			"team": site.team,
			"plan": site.plan,
			"last_successful_backup": last_successes.get(name),
		}
	return details
