# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import date, timedelta

import frappe
from boto3 import client
from frappe.utils import add_days, cint, getdate
from frappe.utils.password import get_decrypted_password

from press.press.doctype.backup_bucket.backup_bucket import get_replication_target
from press.press.doctype.site_backup.site_backup import get_backup_bucket
from press.utils import chunk

# An auditor asks about a year at a time; anything wider is a mistake, not a question
MAX_RANGE_DAYS = 366

# A finished range barely changes, and an audit means opening the same one repeatedly
CACHE_TTL = 60 * 60

# Keeps the IN clause sane on a year of daily backups
REMOTE_FILE_BATCH = 500

ARTIFACT_BY_FIELD = {
	"remote_database_file": "database",
	"remote_public_file": "public",
	"remote_private_file": "private",
	"remote_config_file": "config",
}

# Longest suffix first: a private files tar also ends in the public one's suffix
ARTIFACT_BY_SUFFIX = (
	("-database.sql.gz", "database"),
	("-private-files.tar", "private"),
	("-files.tar", "public"),
	("-site_config_backup.json", "config"),
)


def get_backup_history(site: str, start_date: str, end_date: str) -> list[dict]:
	"""Every day in the range, newest first, so a day holding nothing is as visible as one that does."""
	start, end = resolve_range(site, start_date, end_date)
	if start > end:
		return []

	cached = get_cached_history(site, start, end)
	if cached is not None:
		return cached

	history = build_history(site, start, end)
	cache_history(site, start, end, history)
	return history


def resolve_range(site: str, start_date: str, end_date: str) -> tuple[date, date]:
	"""Trim the asked-for range to days the site could have been backed up on."""
	start, end = getdate(start_date), getdate(end_date)
	if start > end:
		frappe.throw("Start date must be on or before the end date")
	if (end - start).days >= MAX_RANGE_DAYS:
		frappe.throw(f"Pick a range of {MAX_RANGE_DAYS} days or less")

	created_on = getdate(frappe.db.get_value("Site", site, "creation"))
	return max(start, created_on), min(end, getdate())


def build_history(site: str, start: date, end: date) -> list[dict]:
	days = days_between(start, end)
	backups = get_recorded_backups(site, start, end)
	# Records outlive the objects themselves, so buckets are only worth reading for the gaps
	if any(str(day) not in backups for day in days):
		backups = {**list_stored_backups(site, start, end), **backups}

	return [backups.get(str(day)) or missing_backup(str(day)) for day in days]


def get_cached_history(site: str, start: date, end: date) -> list[dict] | None:
	if end >= getdate():
		return None
	return frappe.cache().get_value(cache_key(site, start, end))


def cache_history(site: str, start: date, end: date, history: list[dict]):
	"""Only a finished range is worth keeping, since today can still gain a backup."""
	if end >= getdate():
		return
	frappe.cache().set_value(cache_key(site, start, end), history, expires_in_sec=CACHE_TTL)


def cache_key(site: str, start: date, end: date) -> str:
	return f"backup_audit_trail:{site}:{start}:{end}"


def days_between(start: date, end: date) -> list[date]:
	return [end - timedelta(days=offset) for offset in range((end - start).days + 1)]


def missing_backup(day: str) -> dict:
	return {"date": day, "status": "Not Available"} | dict.fromkeys(ARTIFACT_BY_FIELD.values(), 0)


def found_backup(day: str) -> dict:
	return missing_backup(day) | {"status": "Success"}


def get_recorded_backups(site: str, start: date, end: date) -> dict[str, dict]:
	"""What Press still has on record, which outlives the objects retention drops from the bucket."""
	backups = frappe.get_all(
		"Site Backup",
		filters={
			"site": site,
			"status": "Success",
			# A backup running over midnight lands in an adjacent day's folder
			"creation": ("between", [add_days(start, -1), add_days(end, 1)]),
		},
		fields=list(ARTIFACT_BY_FIELD),
	)
	remote_files = get_remote_files(backups)

	days: dict[str, dict] = {}
	for backup in backups:
		for field, artifact in ARTIFACT_BY_FIELD.items():
			file_path, file_size = remote_files.get(backup[field], (None, None))
			day, _ = split_backup_key(site, file_path)
			if not day or not (str(start) <= day <= str(end)):
				continue
			entry = days.setdefault(day, found_backup(day))
			entry[artifact] = cint(file_size)
	return days


def get_remote_files(backups: list[dict]) -> dict[str, tuple[str, str]]:
	names = [backup[field] for backup in backups for field in ARTIFACT_BY_FIELD if backup[field]]

	files = {}
	for batch in chunk(names, REMOTE_FILE_BATCH):
		rows = frappe.get_all(
			"Remote File",
			{"name": ("in", batch)},
			["name", "file_path", "file_size"],
			as_list=True,
			ignore_permissions=True,
		)
		files.update({name: (file_path, file_size) for name, file_path, file_size in rows})
	return files


def split_backup_key(site: str, file_path: str | None) -> tuple[str | None, str | None]:
	"""Backup objects are keyed <site>/<day>/<file>. Anything shaped otherwise isn't one."""
	parts = (file_path or "").split("/")
	if len(parts) != 3 or parts[0] != site:
		return None, None
	return parts[1], parts[2]


def artifact_of(file_name: str) -> str | None:
	for suffix, artifact in ARTIFACT_BY_SUFFIX:
		if file_name.endswith(suffix):
			return artifact
	return None


def resolve_bucket(bucket_name: str) -> dict:
	"""Where to read a bucket from, following replication the way Remote File does."""
	target = get_replication_target(bucket_name)
	if target:
		return target

	row = frappe.db.get_value("Backup Bucket", bucket_name, ["region", "endpoint_url"], as_dict=True)
	if row:
		return {"name": bucket_name, "region": row.region, "endpoint_url": row.endpoint_url}

	return {
		"name": bucket_name,
		"region": frappe.db.get_single_value("Press Settings", "backup_region"),
		"endpoint_url": None,
	}


def get_read_bucket(cluster: str) -> dict:
	return resolve_bucket(get_backup_bucket(cluster, region=True)["name"])


def get_site_buckets(site: str) -> list[dict]:
	"""The site's own cluster bucket first, then any it used before, so a move between clusters still reads."""
	cluster = frappe.db.get_value("Site", site, "cluster")
	current = get_read_bucket(cluster)

	buckets = {current["name"]: current}
	used_before = frappe.get_all("Remote File", {"site": site, "bucket": ("is", "set")}, pluck="bucket")
	for bucket_name in set(used_before):
		buckets.setdefault(bucket_name, resolve_bucket(bucket_name))
	return list(buckets.values())


def list_stored_backups(site: str, start: date, end: date) -> dict[str, dict]:
	days: dict[str, dict] = {}
	for bucket in get_site_buckets(site):
		# The current cluster's bucket is walked first, so it wins where both hold a day
		for day, entry in list_bucket(bucket, site, start, end).items():
			days.setdefault(day, entry)
	return days


def list_bucket(bucket: dict, site: str, start: date, end: date) -> dict[str, dict]:
	"""Walk the site's prefix in one bucket, sizing what is held per day."""
	prefix = f"{site}/"
	pages = (
		get_s3_client(bucket)
		.get_paginator("list_objects_v2")
		.paginate(Bucket=bucket["name"], Prefix=prefix, StartAfter=f"{prefix}{start}")
	)

	days: dict[str, dict] = {}
	for page in pages:
		for s3_object in page.get("Contents", []):
			day, file_name = split_backup_key(site, s3_object["Key"])
			# Keys sort by day, so the first one past the range ends the walk
			if day and day > str(end):
				return days
			if not day or not file_name:
				continue
			entry = days.setdefault(day, found_backup(day))
			if artifact := artifact_of(file_name):
				entry[artifact] = s3_object["Size"]
	return days


def get_s3_client(bucket: dict):
	return client(
		"s3",
		aws_access_key_id=frappe.db.get_single_value("Press Settings", "offsite_backups_access_key_id"),
		aws_secret_access_key=get_decrypted_password(
			"Press Settings", "Press Settings", "offsite_backups_secret_access_key"
		),
		region_name=bucket["region"],
		endpoint_url=bucket["endpoint_url"],
	)
