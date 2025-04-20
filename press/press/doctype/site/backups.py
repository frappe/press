# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import functools
from collections import deque
from datetime import datetime, timedelta
from functools import wraps
from itertools import groupby
from time import time

import frappe
import pytz

from press.press.doctype.press_settings.press_settings import PressSettings
from press.press.doctype.remote_file.remote_file import delete_remote_backup_objects
from press.press.doctype.site.site import Literal, Site
from press.press.doctype.site_backup.site_backup import SiteBackup
from press.press.doctype.subscription.subscription import Subscription
from press.utils import log_error


def timing(f):
	@wraps(f)
	def wrap(*args, **kw):
		ts = time()
		result = f(*args, **kw)
		te = time()
		print(f"Took {te - ts}s")
		return result

	return wrap


BACKUP_TYPES = Literal["Logical", "Physical"]


class BackupRotationScheme:
	"""
	Represents backup rotation scheme for maintaining offsite backups.

	Rotation is maintained by controlled deletion of daily backups.
	"""

	def _expire_and_get_remote_files(self, offsite_backups: list[dict[str, str]]) -> list[str]:
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

	@functools.lru_cache(maxsize=128)  # noqa: B019
	def _get_expiry(self, config: str):
		return frappe.parse_json(config or "{}").keep_backups_for_hours or 24

	def _expire_backups_of_site_in_bench(self, sites: list[str], expiry: int):
		if sites:
			frappe.db.set_value(
				"Site Backup",
				{
					"site": ("in", sites),
					"status": "Success",
					"files_availability": "Available",
					"physical": False,
					"offsite": False,
					"creation": ("<", frappe.utils.add_to_date(None, hours=-expiry)),
				},
				"files_availability",
				"Unavailable",
			)

	def _mark_physical_backups_as_expired(self, backups: list[str]):
		site_backups = frappe.get_all(
			"Site Backup",
			filters={
				"name": ("in", backups),
				"files_availability": "Available",
				"physical": True,
			},
			fields=["name", "database_snapshot"],
			pluck="name",
		)
		for backup in site_backups:
			# set snapshot as Unavailable
			frappe.db.set_value(
				"Site Backup",
				backup.name,
				"files_availability",
				"Unavailable",
			)
			frappe.db.set_value(
				"Virtual Disk Snapshot",
				backup.database_snapshot,
				"expired",
				True,
			)

	def get_backups_due_for_expiry(self, backup_type: BACKUP_TYPES) -> list[str]:
		raise NotImplementedError

	def expire_offsite_backups(self) -> list[str]:
		"""Expire and return list of offsite backups to delete."""
		return self._expire_and_get_remote_files(self.get_backups_due_for_expiry("Logical"))

	def cleanup_offsite(self):
		"""Expire backups according to the rotation scheme."""
		expired_remote_files = self.expire_offsite_backups()
		delete_remote_backup_objects(expired_remote_files)

	def expire_physical_backups(self):
		"""Expire backups according to the rotation scheme"""
		self._mark_physical_backups_as_expired(self.get_backups_due_for_expiry("Physical"))


class FIFO(BackupRotationScheme):
	"""Represents First-in-First-out backup rotation scheme."""

	def __init__(self):
		self.offsite_backups_count = (
			frappe.db.get_single_value("Press Settings", "offsite_backups_count") or 30
		)

	def get_backups_due_for_expiry(self, backup_type: BACKUP_TYPES) -> list[str]:
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
					"offsite": backup_type == "Logical",
					"physical": backup_type == "Physical",
				},
				order_by="creation desc",
			)[offsite_expiry:]
		return to_be_expired_backups


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

	def get_backups_due_for_expiry(self, backup_type: BACKUP_TYPES) -> list[str]:
		today = frappe.utils.getdate()
		oldest_daily = today - timedelta(days=self.daily)
		oldest_weekly = today - timedelta(weeks=4)
		oldest_monthly = today - timedelta(days=366)
		oldest_yearly = today - timedelta(days=3653)
		return frappe.db.sql(
			f"""
			SELECT name from `tabSite Backup`
			WHERE
				site in (select name from tabSite where status != "Archived") and
				status="Success" and
				files_availability="Available" and
				offsite={backup_type == "Logical"} and
				physical={backup_type == "Physical"} and
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


class ModifiableCycle:
	def __init__(self, items=()):
		self.deque = deque(items)

	def __iter__(self):
		return self

	def __next__(self):
		if not self.deque:
			raise StopIteration
		item = self.deque.popleft()
		self.deque.append(item)
		return item

	def delete_next(self):
		self.deque.popleft()

	def delete_prev(self):
		self.deque.pop()


class ScheduledBackupJob:
	"""Represents Scheduled Backup Job that takes backup for all active sites."""

	def is_backup_hour(self, hour: int) -> bool:
		"""
		hour: 0-23

		Return true if backup is supposed to be taken at this hour
		"""
		# return (hour + self.offset) % self.interval == 0
		return True

	def __init__(self, backup_type: BACKUP_TYPES):
		self.backup_type: BACKUP_TYPES = backup_type
		self.interval: int = (
			frappe.get_cached_value("Press Settings", "Press Settings", "backup_interval") or 6
		)
		self.offset: int = frappe.get_cached_value("Press Settings", "Press Settings", "backup_offset") or 0
		self.limit = frappe.get_cached_value("Press Settings", "Press Settings", "backup_limit") or 100
		self.max_failed_backup_attempts_in_a_day = (
			frappe.get_cached_value("Press Settings", "Press Settings", "max_failed_backup_attempts_in_a_day")
			or 6
		)

		self.offsite_setup = PressSettings.is_offsite_setup()
		self.server_time = datetime.now()
		self.sites = Site.get_sites_for_backup(self.interval, backup_type=self.backup_type)
		if self.backup_type == "Logical":
			self.sites_without_offsite = Subscription.get_sites_without_offsite_backups()
		else:
			self.sites_without_offsite = []

	def take_offsite(self, site: frappe._dict, day: datetime.date) -> bool:
		return (
			self.offsite_setup
			and site.name not in self.sites_without_offsite
			and not SiteBackup.offsite_backup_exists(site.name, day)
		)

	def get_site_time(self, site: dict[str, str]) -> datetime:
		timezone = site.timezone or "Asia/Kolkata"
		site_timezone = pytz.timezone(timezone)
		return self.server_time.astimezone(site_timezone)

	def start(self):
		"""Schedule backups for all Active sites based on their local timezones. Also trigger offsite backups once a day."""
		sites_by_server = []
		for server, sites in groupby(self.sites, lambda d: d.server):
			sites_by_server.append((server, iter(list(sites))))

		sites_by_server_cycle = ModifiableCycle(sites_by_server)
		self._take_backups_in_round_robin(sites_by_server_cycle)

	def _take_backups_in_round_robin(self, sites_by_server_cycle: ModifiableCycle):
		limit = min(len(self.sites), self.limit)
		for _server, sites in sites_by_server_cycle:
			try:
				site = next(sites)
				while not self.backup(site):
					site = next(sites)
			except StopIteration:
				sites_by_server_cycle.delete_prev()  # no more sites in this server
				continue
			limit -= 1
			if limit <= 0:
				break

	def backup(self, site) -> bool:
		"""Return true if backup was taken."""
		try:
			site_time = self.get_site_time(site)
			failed_backup_attempts_in_a_day = frappe.db.count(
				"Site Backup",
				{
					"site": site.name,
					"status": ("in", ["Failure", "Delivery Failure"]),
					"physical": self.backup_type == "Physical",
					"creation": [
						">=",
						frappe.utils.add_days(None, -1),
					],
				},
			)
			if (
				self.is_backup_hour(site_time.hour)
				and failed_backup_attempts_in_a_day <= self.max_failed_backup_attempts_in_a_day
			):
				today = frappe.utils.getdate()

				"""
				Offsite backup is applicable only for logical backups
				In physical backup, we can't take backup with files
				"""
				offsite = self.backup_type == "Logical" and self.take_offsite(site, today)
				with_files = self.backup_type == "Logical" and (
					offsite or not SiteBackup.file_backup_exists(site.name, today)
				)

				frappe.get_doc("Site", site.name).backup(
					with_files=with_files,
					offsite=offsite,
					physical=(self.backup_type == "Physical"),
					deactivate_site_during_backup=(self.backup_type == "Physical"),
				)
				frappe.db.commit()
				return True
			return False

		except Exception:
			log_error("Site Backup Exception", site=site)
			frappe.db.rollback()


def schedule_logical_backups_for_sites_with_backup_time():
	"""
	Schedule logical backups for sites with backup time.

	Run this hourly only
	"""
	sites = Site.get_sites_with_backup_time("Logical")
	for site in sites:
		site_doc: Site = frappe.get_doc("Site", site.name)
		site_doc.backup(with_files=True, offsite=True, physical=False)
		frappe.db.commit()


def schedule_physical_backups_for_sites_with_backup_time():
	"""
	Schedule physical backups for sites with backup time.

	Run this hourly only
	"""
	sites = Site.get_sites_with_backup_time("Physical")
	for site in sites:
		site_doc: Site = frappe.get_doc("Site", site.name)
		site_doc.backup(with_files=False, offsite=False, physical=True, deactivate_site_during_backup=True)
		frappe.db.commit()


def schedule_logical_backups():
	scheduled_backup_job = ScheduledBackupJob(backup_type="Logical")
	scheduled_backup_job.start()


def schedule_physical_backups():
	scheduled_backup_job = ScheduledBackupJob(backup_type="Physical")
	scheduled_backup_job.start()


def cleanup_offsite():
	"""Delete expired (based on policy) offsite backups and mark em as Unavailable."""
	frappe.enqueue("press.press.doctype.site.backups._cleanup_offsite", queue="long", timeout=3600)


def _cleanup_offsite():
	scheme = frappe.db.get_single_value("Press Settings", "backup_rotation_scheme") or "FIFO"
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


def expire_physical():
	"""Mark physical snapshot as expired (based on policy) and backups mark em as Unavailable."""
	frappe.enqueue("press.press.doctype.site.backups._expire_physical_backups")


def _expire_physical_backups():
	scheme = frappe.db.get_single_value("Press Settings", "backup_rotation_scheme") or "FIFO"
	if scheme == "FIFO":
		rotation = FIFO()
	elif scheme == "Grandfather-father-son":
		rotation = GFS()
	rotation.expire_physical_backups()
	frappe.db.commit()
