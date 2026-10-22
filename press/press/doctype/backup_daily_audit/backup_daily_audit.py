# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from datetime import datetime

BACKUP_JOB_TYPE = "Backup Site"
FAILED_STATUSES = ("Failure", "Delivery Failure")
FREQUENT_FAILURE_THRESHOLD = 3


class BackupDailyAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.backup_daily_audit_site.backup_daily_audit_site import BackupDailyAuditSite

		audit_date: DF.Date
		failed_jobs: DF.Int
		sites_with_frequent_failures: DF.Table[BackupDailyAuditSite]
		sites_with_frequent_failures_count: DF.Int
		sites_without_success_in_3_days: DF.Table[BackupDailyAuditSite]
		sites_without_success_in_3_days_count: DF.Int
		sites_without_success_in_day: DF.Table[BackupDailyAuditSite]
		sites_without_success_in_day_count: DF.Int
		success_rate: DF.Percent
		successful_jobs: DF.Int
	# end: auto-generated types

	def validate(self):
		self.sites_with_frequent_failures_count = len(self.sites_with_frequent_failures)
		self.sites_without_success_in_day_count = len(self.sites_without_success_in_day)
		self.sites_without_success_in_3_days_count = len(self.sites_without_success_in_3_days)

	def collect(self):
		self.audit_date = frappe.utils.today()
		self.set_job_counts()
		self.add_sites_with_frequent_failures()
		self.add_sites_without_success("sites_without_success_in_day", days=1)
		self.add_sites_without_success("sites_without_success_in_3_days", days=3)

	def add_sites_with_frequent_failures(self):
		failures = get_sites_with_frequent_failures(frappe.utils.add_days(None, -1))
		details = get_site_details(list(failures))
		for site, count in failures.items():
			self.append("sites_with_frequent_failures", {**details[site], "failed_backups": count})

	def add_sites_without_success(self, table: str, days: int):
		since = frappe.utils.add_days(None, -days)
		sites = get_sites_without_successful_backup(since)
		failures = get_failed_backup_counts(sites, since)
		details = get_site_details(sites)
		for site in sites:
			self.append(table, {**details[site], "failed_backups": failures.get(site, 0)})

	def set_job_counts(self):
		"""Backup Site agent jobs created in the last 24h that have finished, by outcome."""
		counts = dict(
			frappe.get_all(
				"Agent Job",
				filters={
					"job_type": BACKUP_JOB_TYPE,
					"status": ("in", ["Success", *FAILED_STATUSES]),
					"creation": (">=", frappe.utils.add_days(None, -1)),
				},
				fields=["status", "count(name) as jobs"],
				group_by="status",
				as_list=True,
			)
		)
		self.successful_jobs = counts.get("Success", 0)
		self.failed_jobs = sum(counts.get(status, 0) for status in FAILED_STATUSES)
		finished_jobs = self.successful_jobs + self.failed_jobs
		self.success_rate = self.successful_jobs / finished_jobs * 100 if finished_jobs else 0


def record_backup_daily_audit() -> None:
	audit: BackupDailyAudit = frappe.new_doc("Backup Daily Audit")
	audit.collect()
	# A site renamed or deleted since its backup failed must not block the audit
	audit.flags.ignore_links = True
	audit.insert(ignore_permissions=True)


def get_sites_with_frequent_failures(since: datetime) -> dict[str, int]:
	"""Failed logical backup counts of sites at or over the threshold, most failures first."""
	failures_by_site = frappe.get_all(
		"Site Backup",
		filters={"status": ("in", FAILED_STATUSES), "physical": False, "creation": (">=", since)},
		fields=["site", "count(name) as failures"],
		group_by="site",
		order_by="failures desc, site asc",
	)
	return {row.site: row.failures for row in failures_by_site if row.failures >= FREQUENT_FAILURE_THRESHOLD}


def get_sites_without_successful_backup(since: datetime) -> list[str]:
	"""Sites due a scheduled backup with no successful logical backup since the given time."""
	sites_with_success = frappe.get_all(
		"Site Backup",
		filters={"status": "Success", "physical": False, "creation": (">=", since)},
		pluck="site",
		distinct=True,
	)
	# A site deactivated for part of the window was not due a backup all along
	activated_sites = frappe.get_all(
		"Site Activity", {"action": "Activate Site", "creation": (">=", since)}, pluck="site"
	)
	return sorted(
		set(get_sites_due_scheduled_backups(since)) - set(sites_with_success) - set(activated_sites)
	)


def get_failed_backup_counts(site_names: list[str], since: datetime) -> dict[str, int]:
	if not site_names:
		return {}

	return dict(
		frappe.get_all(
			"Site Backup",
			filters={
				"site": ("in", site_names),
				"status": ("in", FAILED_STATUSES),
				"physical": False,
				"creation": (">=", since),
			},
			fields=["site", "count(name) as failures"],
			group_by="site",
			as_list=True,
		)
	)


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
			filters={"site": ("in", site_names), "status": "Success", "physical": False},
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
