# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Max

if TYPE_CHECKING:
	from datetime import datetime

BACKUP_JOB_TYPE = "Backup Site"
FAILED_STATUSES = ("Failure", "Delivery Failure")
FREQUENT_FAILURE_THRESHOLD = 3
# Sites back up once per backup interval, so allow this long for queue time on top of it
BACKUP_GRACE_HOURS = 6
# Sites with a custom backup time back up once a day, whatever the interval
MINIMUM_BACKUP_INTERVAL_HOURS = 24
# Frappe Compute and DigitalOcean snapshots aren't recorded on press, so those machines are left out
SNAPSHOT_CLOUD_PROVIDERS = ("AWS EC2", "OCI", "Hetzner")
DAILY_SNAPSHOT_FILTERS = {"physical_backup": False, "rolling_snapshot": False}
TABLES = (
	"sites_with_frequent_failures",
	"sites_without_success_in_day",
	"sites_without_success_in_3_days",
	"servers_without_snapshot_in_day",
)


class BackupDailyAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.backup_daily_audit_server.backup_daily_audit_server import (
			BackupDailyAuditServer,
		)
		from press.press.doctype.backup_daily_audit_site.backup_daily_audit_site import BackupDailyAuditSite

		audit_date: DF.Date
		day_window_hours: DF.Int
		failed_jobs: DF.Int
		servers_without_snapshot_in_day: DF.Table[BackupDailyAuditServer]
		servers_without_snapshot_in_day_count: DF.Int
		sites_with_frequent_failures: DF.Table[BackupDailyAuditSite]
		sites_with_frequent_failures_count: DF.Int
		sites_without_success_in_3_days: DF.Table[BackupDailyAuditSite]
		sites_without_success_in_3_days_count: DF.Int
		sites_without_success_in_day: DF.Table[BackupDailyAuditSite]
		sites_without_success_in_day_count: DF.Int
		success_rate: DF.Percent
		successful_jobs: DF.Int
		window_end: DF.Datetime | None
	# end: auto-generated types

	def validate(self):
		self.sites_with_frequent_failures_count = len(self.sites_with_frequent_failures)
		self.sites_without_success_in_day_count = len(self.sites_without_success_in_day)
		self.sites_without_success_in_3_days_count = len(self.sites_without_success_in_3_days)
		self.servers_without_snapshot_in_day_count = len(self.servers_without_snapshot_in_day)

	def collect(self, listed: dict[str, list[str]] | None = None):
		"""Fill every list for the windows ending at `window_end`, now for a new audit.
		A refresh passes the sites and machines already `listed`, so it re-checks only those."""
		listed = listed or {}
		self.window_end = self.window_end or frappe.utils.now_datetime()
		self.day_window_hours = self.day_window_hours or get_daily_backup_window_hours()
		self.audit_date = frappe.utils.getdate(self.window_end)
		for table in TABLES:
			self.set(table, [])
		self.set_job_counts()
		self.add_sites_with_frequent_failures()
		self.add_sites_without_success("sites_without_success_in_day", self.day_window_hours, listed)
		self.add_sites_without_success("sites_without_success_in_3_days", 3 * 24, listed)
		self.add_servers_without_snapshot(listed)

	@frappe.whitelist()
	def refresh_lists(self):
		frappe.only_for("System Manager")
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"recollect",
			queue="long",
			timeout=1800,
			job_id=f"backup_daily_audit||{self.name}||recollect",
			deduplicate=True,
			enqueue_after_commit=True,
		)

	def recollect(self):
		self.collect(self.listed_names())
		self.flags.ignore_links = True
		self.save(ignore_permissions=True)

	def listed_names(self) -> dict[str, list[str]]:
		"""Sites and machines on each list whose eligibility a refresh must keep."""
		return {
			"sites_without_success_in_day": [row.site for row in self.sites_without_success_in_day],
			"sites_without_success_in_3_days": [row.site for row in self.sites_without_success_in_3_days],
			"servers_without_snapshot_in_day": [
				row.virtual_machine for row in self.servers_without_snapshot_in_day
			],
		}

	def window(self, hours: int) -> tuple[datetime, datetime]:
		end = frappe.utils.get_datetime(self.window_end)
		return frappe.utils.add_to_date(end, hours=-hours), end

	def add_sites_with_frequent_failures(self):
		failures = get_sites_with_frequent_failures(*self.window(24))
		details = get_site_details(list(failures), self.window_end)
		for site, count in failures.items():
			self.append("sites_with_frequent_failures", {**details[site], "failed_backups": count})

	def add_sites_without_success(self, table: str, hours: int, listed: dict[str, list[str]]):
		since, until = self.window(hours)
		sites = get_sites_without_successful_backup(since, until, listed.get(table))
		failures = get_failed_backup_counts(sites, since, until)
		details = get_site_details(sites, until)
		for site in sites:
			self.append(table, {**details[site], "failed_backups": failures.get(site, 0)})

	def add_servers_without_snapshot(self, listed: dict[str, list[str]]):
		since, until = self.window(24)
		machines = get_virtual_machines_without_snapshot(
			since, until, listed.get("servers_without_snapshot_in_day")
		)
		failures = get_failed_snapshot_counts(machines, since, until)
		details = get_virtual_machine_details(machines, until)
		for machine in machines:
			self.append(
				"servers_without_snapshot_in_day",
				{**details[machine], "failed_snapshots": failures.get(machine, 0)},
			)

	def set_job_counts(self):
		"""Backup Site agent jobs created in the 24h window that have finished, by outcome."""
		counts = dict(
			frappe.get_all(
				"Agent Job",
				filters={
					"job_type": BACKUP_JOB_TYPE,
					"status": ("in", ["Success", *FAILED_STATUSES]),
					"creation": ("between", self.window(24)),
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


def get_daily_backup_window_hours() -> int:
	interval = frappe.get_cached_value("Press Settings", "Press Settings", "backup_interval") or 6
	return max(interval, MINIMUM_BACKUP_INTERVAL_HOURS) + BACKUP_GRACE_HOURS


def get_sites_with_frequent_failures(since: datetime, until: datetime) -> dict[str, int]:
	"""Failed backup counts of sites at or over the threshold, most failures first."""
	failures_by_site = frappe.get_all(
		"Site Backup",
		filters={"status": ("in", FAILED_STATUSES), "creation": ("between", [since, until])},
		fields=["site", "count(name) as failures"],
		group_by="site",
		order_by="failures desc, site asc",
	)
	return {row.site: row.failures for row in failures_by_site if row.failures >= FREQUENT_FAILURE_THRESHOLD}


def get_sites_without_successful_backup(
	since: datetime, until: datetime, candidates: list[str] | None = None
) -> list[str]:
	"""Sites due a backup through the window, or the `candidates` given, with no successful backup in it."""
	if candidates is None:
		candidates = get_sites_due_scheduled_backups(since)
	backup, query = successful_backups_query()
	sites_with_success = (
		query.select(backup.site).distinct().where(backup.creation.between(since, until)).run(pluck=True)
	)
	return sorted(set(candidates) - set(sites_with_success) - set(get_sites_started_within(since, until)))


def get_sites_started_within(since: datetime, until: datetime) -> list[str]:
	"""Sites activated, or claimed from a standby pool at signup, in the window, so not due a backup all along."""
	window = ("between", [since, until])
	activated_sites = frappe.get_all(
		"Site Activity", {"action": "Activate Site", "creation": window}, pluck="site"
	)
	# A pooled site's creation is when the pool made it, months before a signup can claim it
	signed_up_sites = frappe.get_all("Site", {"signup_time": window}, pluck="name")
	return activated_sites + signed_up_sites


def successful_backups_query():
	"""Successful backups, counting a physical one only once its disk snapshot has completed."""
	backup = frappe.qb.DocType("Site Backup")
	snapshot = frappe.qb.DocType("Virtual Disk Snapshot")
	query = (
		frappe.qb.from_(backup)
		.left_join(snapshot)
		.on(backup.database_snapshot == snapshot.name)
		.where(backup.status == "Success")
		.where((backup.physical == 0) | (snapshot.status == "Completed"))
	)
	return backup, query


def get_failed_backup_counts(site_names: list[str], since: datetime, until: datetime) -> dict[str, int]:
	if not site_names:
		return {}

	return dict(
		frappe.get_all(
			"Site Backup",
			filters={
				"site": ("in", site_names),
				"status": ("in", FAILED_STATUSES),
				"creation": ("between", [since, until]),
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
		},
		or_filters={"skip_scheduled_logical_backups": False, "skip_scheduled_physical_backups": False},
		pluck="name",
	)


def get_site_details(site_names: list[str], until: datetime) -> dict[str, dict]:
	"""Server, team, plan and last successful backup up to the window end of each site, as audit rows."""
	if not site_names:
		return {}

	sites = {
		site.name: site
		for site in frappe.get_all("Site", {"name": ("in", site_names)}, ["name", "server", "team", "plan"])
	}
	backup, query = successful_backups_query()
	last_successes = dict(
		query.select(backup.site, Max(backup.creation))
		.where(backup.site.isin(site_names))
		.where(backup.creation <= until)
		.groupby(backup.site)
		.run()
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


def get_virtual_machines_without_snapshot(
	since: datetime, until: datetime, candidates: list[str] | None = None
) -> list[str]:
	"""Machines due an automated snapshot, or the `candidates` given, with no completed daily snapshot."""
	if candidates is None:
		candidates = get_virtual_machines_due_snapshot(since)
	machines_with_snapshot = frappe.get_all(
		"Virtual Disk Snapshot",
		filters={**DAILY_SNAPSHOT_FILTERS, "status": "Completed", "creation": ("between", [since, until])},
		pluck="virtual_machine",
		distinct=True,
	)
	return sorted(set(candidates) - set(machines_with_snapshot))


def get_virtual_machines_due_snapshot(created_before: datetime) -> list[str]:
	return frappe.get_all(
		"Virtual Machine",
		{
			"status": "Running",
			"skip_automated_snapshot": False,
			"cloud_provider": ("in", SNAPSHOT_CLOUD_PROVIDERS),
			"creation": ("<=", created_before),
		},
		pluck="name",
	)


def get_failed_snapshot_counts(machines: list[str], since: datetime, until: datetime) -> dict[str, int]:
	if not machines:
		return {}

	return dict(
		frappe.get_all(
			"Virtual Disk Snapshot",
			filters={
				**DAILY_SNAPSHOT_FILTERS,
				"virtual_machine": ("in", machines),
				"status": "Error",
				"creation": ("between", [since, until]),
			},
			fields=["virtual_machine", "count(name) as failures"],
			group_by="virtual_machine",
			as_list=True,
		)
	)


def get_virtual_machine_details(machines: list[str], until: datetime) -> dict[str, dict]:
	"""Server, team, provider and last daily snapshot up to the window end of each machine, as audit rows."""
	from press.press.doctype.virtual_machine.virtual_machine import server_doctypes

	if not machines:
		return {}

	servers = {}
	for doctype in server_doctypes:
		for server in frappe.get_all(
			doctype, {"virtual_machine": ("in", machines)}, ["name", "virtual_machine"]
		):
			servers[server.virtual_machine] = (doctype, server.name)
	virtual_machines = {
		machine.name: machine
		for machine in frappe.get_all(
			"Virtual Machine", {"name": ("in", machines)}, ["name", "team", "cloud_provider", "series"]
		)
	}
	last_snapshots = dict(
		frappe.get_all(
			"Virtual Disk Snapshot",
			filters={
				**DAILY_SNAPSHOT_FILTERS,
				"virtual_machine": ("in", machines),
				"status": "Completed",
				"creation": ("<=", until),
			},
			fields=["virtual_machine", "max(creation) as last_snapshot"],
			group_by="virtual_machine",
			as_list=True,
		)
	)
	details = {}
	for name in machines:
		server_type, server = servers.get(name, (None, None))
		machine = virtual_machines.get(name) or frappe._dict()
		details[name] = {
			"virtual_machine": name,
			"server_type": server_type,
			"server": server,
			"team": machine.team,
			"cloud_provider": machine.cloud_provider,
			"series": machine.series,
			"last_successful_snapshot": last_snapshots.get(name),
		}
	return details
