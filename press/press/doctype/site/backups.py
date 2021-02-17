# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import functools
import time
from datetime import date, datetime, timedelta
from typing import Dict, List
from unittest.mock import patch, Mock

import frappe
import pytz

from press.press.doctype.remote_file.remote_file import delete_remote_backup_objects
from press.press.doctype.site.site import Site
from press.utils import log_error


def timeit(func):
	"""Time function without commit."""

	@patch("press.press.doctype.site.backups.delete_remote_backup_objects", Mock())
	@patch("press.press.doctype.site.backups.frappe.db.commit", Mock())
	def wrapper(*args, **kwargs):
		start = time.perf_counter()
		ret = func(*args, **kwargs)
		end = time.perf_counter()
		print("*" * 20)
		print("*" * 20)
		print(f"Time taken for function {func.__name__}: {end-start}")
		print("*" * 20)
		print("*" * 20)
		return ret

	return wrapper


@functools.lru_cache(maxsize=128)
def keep_backups_for_(bench: str) -> int:
	"""Get no. of hours for which backups are kept on site."""
	return (
		frappe.parse_json(
			frappe.db.get_value("Bench", bench, "config") or "{}"
		).keep_backups_for_hours
		or 24
	)


class BackupRotationScheme:
	"""
	Represents backup rotation scheme for maintaining offsite backups.

	Rotation is maintained by controlled deletion of daily backups.
	"""

	@timeit
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

	@timeit
	def expire_local_backups(self, site: Site):
		expiry = keep_backups_for_(site.bench)
		expired_local_backups = frappe.get_all(
			"Site Backup",
			filters={
				"site": site.name,
				"status": "Success",
				"files_availability": "Available",
				"offsite": False,
				"creation": ("<", datetime.now() - timedelta(hours=expiry)),
			},
			pluck="name",
		)

		for local_backup in expired_local_backups:
			# we're assuming each Frappe site does it's work as per conf and marking them
			# as available
			frappe.db.set_value("Site Backup", local_backup, "files_availability", "Unavailable")

	def expire_offsite_backups(self, site: Site) -> List[str]:
		"""Expire and return list of offsite backups to delete."""
		raise NotImplementedError

	@timeit
	def cleanup(self):
		"""Expire backups according to the rotation scheme."""
		sites = frappe.get_all(
			"Site", filters={"status": ("!=", "Archived")}, fields=["name", "bench"],
		)
		for site in sites:
			self.expire_local_backups(site)
		sites = [site.name for site in sites]
		expired_remote_files = self.expire_offsite_backups(sites)
		delete_remote_backup_objects(expired_remote_files)
		frappe.db.commit()


class FIFO(BackupRotationScheme):
	"""Represents First-in-First-out backup rotation scheme."""

	def __init__(self):
		self.offsite_backups_count = (
			frappe.db.get_single_value("Press Settings", "offsite_backups_count") or 30
		)

	def expire_offsite_backups(self, sites: List[str]) -> List[str]:
		offsite_expiry = self.offsite_backups_count
		to_be_expired_backups = []
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

	@timeit
	def expire_offsite_backups(self, sites: List[str]) -> List[str]:
		today = date.today()
		oldest_daily = today - timedelta(days=self.daily)
		oldest_weekly = today - timedelta(weeks=4)
		oldest_monthly = today - timedelta(days=366)
		oldest_yearly = today - timedelta(days=3653)
		sites_sql_list = '(' + ','.join([f"\'{site}\'" for site in sites]) + ')'
		to_be_expired_backups = frappe.db.sql(
			f"""
			SELECT name from `tabSite Backup`
			WHERE
				site in {sites_sql_list} and
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


def schedule():
	"""Schedule backups for all Active sites based on their local timezones. Also trigger offsite backups once a day."""

	sites = frappe.get_all(
		"Site", fields=["name", "timezone"], filters={"status": "Active"},
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
	interval = frappe.db.get_single_value("Press Settings", "backup_interval") or 6
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

			if site_time.hour % interval == 0:
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

		except Exception:
			log_error("Site Backup Exception", site=site)


@timeit
def cleanup():
	"""Delete expired offsite backups and set statuses for old local ones."""

	scheme = (
		frappe.db.get_single_value("Press Settings", "backup_rotation_scheme") or "FIFO"
	)
	if scheme == "FIFO":
		rotation = FIFO()
	elif scheme == "Grandfather-father-son":
		rotation = GFS()
	rotation.cleanup()
