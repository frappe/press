# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import date, timedelta

import frappe
from boto3 import client
from frappe.utils import add_days, cint, getdate
from frappe.utils.password import get_decrypted_password

from press.press.doctype.site_backup.site_backup import get_backup_bucket

# An auditor asks about a year at a time; anything wider is a mistake, not a question
MAX_RANGE_DAYS = 366

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
	start, end = getdate(start_date), getdate(end_date)
	if start > end:
		frappe.throw("Start date must be on or before the end date")
	if (end - start).days >= MAX_RANGE_DAYS:
		frappe.throw(f"Pick a range of {MAX_RANGE_DAYS} days or less")

	days = days_between(start, end)
	backups = get_recorded_backups(site, start, end)
	# Records outlive the objects themselves, so the bucket is only worth reading for the gaps
	if any(str(day) not in backups for day in days):
		backups = {**list_stored_backups(site, start, end), **backups}

	return [backups.get(str(day)) or missing_backup(str(day)) for day in days]


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
	if not names:
		return {}

	return {
		name: (file_path, file_size)
		for name, file_path, file_size in frappe.get_all(
			"Remote File",
			{"name": ("in", names)},
			["name", "file_path", "file_size"],
			as_list=True,
			ignore_permissions=True,
		)
	}


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


def list_stored_backups(site: str, start: date, end: date) -> dict[str, dict]:
	"""Walk the site's prefix in its cluster's backup bucket, sizing what is held per day."""
	bucket = get_backup_bucket(frappe.db.get_value("Site", site, "cluster"), region=True)
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
