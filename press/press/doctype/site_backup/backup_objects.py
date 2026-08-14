# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""What the backup buckets still hold, read as sizes per day per artifact.

Object storage only, so nothing here knows what a day of the audit trail looks like.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from boto3 import client
from frappe.utils.password import get_decrypted_password

from press.press.doctype.backup_bucket.backup_bucket import get_replication_target
from press.press.doctype.site_backup.site_backup import get_backup_bucket

if TYPE_CHECKING:
	from datetime import date

# Longest suffix first: a private files tar also ends in the public one's suffix
ARTIFACT_BY_SUFFIX = (
	("-database.sql.gz", "database"),
	("-private-files.tar", "private"),
	("-files.tar", "public"),
	("-site_config_backup.json", "config"),
)


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


def list_stored_objects(site: str, start: date, end: date) -> dict[str, dict[str, int]]:
	"""What each bucket still holds for this site, as a size per artifact per day."""
	credentials = get_offsite_credentials()
	if not credentials:
		return {}

	days: dict[str, dict[str, int]] = {}
	for bucket in get_site_buckets(site):
		# The current cluster's bucket is walked first, so it wins where both hold a day
		for day, sizes in walk_bucket(bucket, site, start, end, credentials).items():
			days.setdefault(day, sizes)
	return days


def get_offsite_credentials() -> tuple[str, str] | None:
	"""None on a bench where offsite backups were never set up, which is not an error."""
	access_key = frappe.db.get_single_value("Press Settings", "offsite_backups_access_key_id")
	secret_key = get_decrypted_password(
		"Press Settings",
		"Press Settings",
		"offsite_backups_secret_access_key",
		raise_exception=False,
	)
	if not (access_key and secret_key):
		return None
	return access_key, secret_key


def walk_bucket(
	bucket: dict, site: str, start: date, end: date, credentials: tuple[str, str]
) -> dict[str, dict]:
	"""Walk the site's prefix in one bucket, sizing what is held per day."""
	prefix = f"{site}/"
	pages = (
		get_s3_client(bucket, credentials)
		.get_paginator("list_objects_v2")
		.paginate(Bucket=bucket["name"], Prefix=prefix, StartAfter=f"{prefix}{start}")
	)

	days: dict[str, dict[str, int]] = {}
	for page in pages:
		for s3_object in page.get("Contents", []):
			day, file_name = split_backup_key(site, s3_object["Key"])
			# Keys sort by day, so the first one past the range ends the walk
			if day and day > str(end):
				return days
			if not day or not file_name:
				continue
			sizes = days.setdefault(day, {})
			if artifact := artifact_of(file_name):
				sizes[artifact] = s3_object["Size"]
	return days


def get_s3_client(bucket: dict, credentials: tuple[str, str]):
	access_key, secret_key = credentials
	return client(
		"s3",
		aws_access_key_id=access_key,
		aws_secret_access_key=secret_key,
		region_name=bucket["region"],
		endpoint_url=bucket["endpoint_url"],
	)
