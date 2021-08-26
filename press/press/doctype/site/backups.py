# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import functools
from datetime import date, datetime, timedelta
from itertools import groupby
from typing import Dict, List

import frappe
import pytz
from press.press.doctype.remote_file.remote_file import delete_remote_backup_objects
from press.utils import log_error


class BackupRotationScheme:
	"""
	Represents backup rotation scheme for maintaining offsite backups.

	Rotation is maintained by controlled deletion of daily backups.
	"""

	def _expire_and_get_remote_files(
		self, offsite_backups: List[Dict[str, str]]
	) -> List[str]:
		"""Mark backup as unavailable and return remote files to delete."""
		remote_files_to_delete = []
		for backup in offsite_backups:
			remote_files = frappe.db.get_value(
				"Site Backup",
				backup,
				["remote_database_file", "remote_private_file", "remote_public_file"],
			)
			remote_files_to_delete.extend(remote_files)
			frappe.db.set_value("Site Backup", backup, "files_availability", "Unavailable")
		return remote_files_to_delete

	def expire_local_backups(self):
		"""Mark local backups deleted by FF as unavailable."""
		sites_with_config = frappe.db.sql(
			"""
						SELECT tabSite.name, tabBench.config
						FROM tabSite
						JOIN tabBench ON tabSite.bench=tabBench.name
						WHERE tabSite.status != "Archived"
						ORDER BY tabBench.config
			""",
			as_dict=True,
		)
		for d in sites_with_config:
			d.config = self._get_expiry(d.config)

		for config, site_confs in groupby(sites_with_config, lambda d: d.config):
			sites = []
			for site_conf in list(site_confs):
				sites.append(site_conf.name)
			self._expire_backups_of_site_in_bench(sites, config)

	@functools.lru_cache(maxsize=128)
	def _get_expiry(self, config: str):
		return frappe.parse_json(config or "{}").keep_backups_for_hours or 24

	def _expire_backups_of_site_in_bench(self, sites: List[str], expiry: int):
		if sites:
			frappe.db.set_value(
				"Site Backup",
				{
					"site": ("in", sites),
					"status": "Success",
					"files_availability": "Available",
					"offsite": False,
					"creation": ("<", datetime.now() - timedelta(hours=expiry)),
				},
				"files_availability",
				"Unavailable",
			)

	def expire_offsite_backups(self) -> List[str]:
		"""Expire and return list of offsite backups to delete."""
		raise NotImplementedError

	def cleanup_offsite(self):
		"""Expire backups according to the rotation scheme."""
		expired_remote_files = self.expire_offsite_backups()
		delete_remote_backup_objects(expired_remote_files)


class FIFO(BackupRotationScheme):
	"""Represents First-in-First-out backup rotation scheme."""

	def __init__(self):
		self.offsite_backups_count = (
			frappe.db.get_single_value("Press Settings", "offsite_backups_count") or 30
		)

	def expire_offsite_backups(self) -> List[str]:
		offsite_expiry = self.offsite_backups_count
		to_be_expired_backups = []
		sites = frappe.get_all("Site", {"status": ("!=", "Archived")}, pluck="name")
		for site in sites:
			to_be_expired_backups += frappe.get_all(
				"Site Backup",
				filters={
					"site": site,
					"status": "Success",
					"files_availability": "Available",
					"offsite": True,
				},
				order_by="creation desc",
			)[offsite_expiry:]
		return self._expire_and_get_remote_files(to_be_expired_backups)


class GFS(BackupRotationScheme):
	"""
	Represents Grandfather-father-son backup rotation scheme.

	Daily backups are kept for specified number of days.
	Weekly backups are kept for 4 weeks.
	Monthly backups are kept for a year.
	Yearly backups are kept for a decade.
	"""

	daily = 7  # no. of daily backups to keep
	weekly_backup_day = 1  # days of the week (1-7) (SUN-SAT)
	monthly_backup_day = 1  # days of the month (1-31)
	yearly_backup_day = 1  # days of the year (1-366)

	def expire_offsite_backups(self) -> List[str]:
		today = date.today()
		oldest_daily = today - timedelta(days=self.daily)
		oldest_weekly = today - timedelta(weeks=4)
		oldest_monthly = today - timedelta(days=366)
		oldest_yearly = today - timedelta(days=3653)
		to_be_expired_backups = frappe.db.sql(
			f"""
			SELECT name from `tabSite Backup`
			WHERE
				site in (select name from tabSite where status != "Archived") and
				status="Success" and
				files_availability="Available" and
				offsite=True and
				creation < "{oldest_daily}" and
				(DAYOFWEEK(creation) != {self.weekly_backup_day} or creation < "{oldest_weekly}") and
				(DAYOFMONTH(creation) != {self.monthly_backup_day} or creation < "{oldest_monthly}") and
				(DAYOFYEAR(creation) != {self.yearly_backup_day} or creation < "{oldest_yearly}")
			""",
			as_dict=True,
		)
		# XXX: DAYOFWEEK in sql gives 1-7 for SUN-SAT in sql
		# datetime.weekday() in python gives 0-6 for MON-SUN
		# datetime.isoweekday() in python gives 1-7 for MON-SUN

		return self._expire_and_get_remote_files(to_be_expired_backups)


def is_backup_hour(hour: int) -> bool:
	"""hour: 0-23

	Returns true if backup is supposed to be taken at this hour
	"""
	interval: int = (
		frappe.get_cached_value("Press Settings", "Press Settings", "backup_interval") or 6
	)
	backup_offset: int = (
		frappe.get_cached_value("Press Settings", "Press Settings", "backup_offset") or 0
	)
	return (hour + backup_offset) % interval == 0


def schedule():
	"""Schedule backups for all Active sites based on their local timezones. Also trigger offsite backups once a day."""

	sites = frappe.get_all(
		"Site", fields=["name", "timezone"], filters={"status": "Active", "standby": "False"},
	)
	plans_without_offsite_backups = frappe.get_all(
		"Plan", filters={"offsite_backups": 0}, pluck="name"
	)
	sites_without_offsite_backups = set(
		frappe.get_all(
			"Subscription",
			filters={"document_type": "Site", "plan": ("in", plans_without_offsite_backups)},
			pluck="document_name",
		)
	)
	offsite_setup = any(
		frappe.db.get_value(
			"Press Settings",
			"Press Settings",
			["aws_s3_bucket", "offsite_backups_access_key_id"],
		)
	)

	for site in sites:
		try:
			server_time = datetime.now()
			timezone = site.timezone or "Asia/Kolkata"
			site_timezone = pytz.timezone(timezone)
			site_time = server_time.astimezone(site_timezone)

			if is_backup_hour(site_time.hour):
				today = site_time.date()
				common_filters = {
					"creation": ("between", [today, today]),
					"site": site.name,
					"status": "Success",
				}
				offsite = (
					offsite_setup
					and site.name not in sites_without_offsite_backups
					and not frappe.get_all(
						"Site Backup",
						fields=["count(*) as total"],
						filters={**common_filters, "offsite": 1},
					)[0]["total"]
				)
				with_files = (
					not frappe.get_all(
						"Site Backup",
						fields=["count(*) as total"],
						filters={**common_filters, "with_files": 1},
					)[0]["total"]
					or offsite
				)

				frappe.get_doc("Site", site.name).backup(with_files=with_files, offsite=offsite)
				frappe.db.commit()

		except Exception:
			log_error("Site Backup Exception", site=site)
			frappe.db.rollback()


def cleanup_offsite():
	"""Delete expired (based on policy) offsite backups and mark em as Unavailable."""
	scheme = (
		frappe.db.get_single_value("Press Settings", "backup_rotation_scheme") or "FIFO"
	)
	if scheme == "FIFO":
		rotation = FIFO()
	elif scheme == "Grandfather-father-son":
		rotation = GFS()
	rotation.cleanup_offsite()
	frappe.db.commit()


def cleanup_local():
	"""Mark expired onsite backups as Unavailable."""
	brs = BackupRotationScheme()
	brs.expire_local_backups()
	frappe.db.commit()
