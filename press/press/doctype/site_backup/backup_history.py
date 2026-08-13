# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import frappe
from boto3 import client
from frappe.utils import add_days, cint, getdate
from frappe.utils.password import get_decrypted_password

from press.agent import Agent
from press.press.doctype.backup_bucket.backup_bucket import get_replication_target
from press.press.doctype.site_backup.site_backup import get_backup_bucket
from press.utils import chunk

# An auditor asks about a year at a time; anything wider is a mistake, not a question
MAX_RANGE_DAYS = 366

# A finished range barely changes, and an audit means opening the same one repeatedly
CACHE_TTL = 60 * 60

# Keeps the IN clause sane on a year of daily backups
REMOTE_FILE_BATCH = 500

# Most servers run an agent without this endpoint, and will for a while. Remembering
# that keeps every page view from retrying and logging against them.
AGENT_SILENCE_TTL = 60 * 60

# The agent names the config artifact after the file it dumps
ARTIFACT_BY_JOB_KEY = {
	"database": "database",
	"public": "public",
	"private": "private",
	"site_config": "config",
}

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


def get_backup_history(site: str, start_date: str, end_date: str) -> dict:
	"""Every day in the range, newest first, so a day holding nothing is as visible as one that does."""
	start, end = resolve_range(site, start_date, end_date)
	if start > end:
		return {"days": [], "pending": False, "unconfirmed": False}

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


def build_history(site: str, start: date, end: date) -> dict:
	"""Ask each source only for the days the ones before it could not answer."""
	days = days_between(start, end)
	backups = get_recorded_backups(site, start, end)

	# The server knows a backup ran even where nothing was kept, and knows which failed
	state = "answered"
	if has_gaps(backups, days):
		jobs, state = get_agent_backup_jobs(site, start, end)
		backups = {**jobs, **backups}

	if needs_bucket(backups, days):
		backups = merge_stored(backups, list_stored_backups(site, start, end))

	waiting = state != "answered" and has_gaps(backups, days)

	return {
		"days": [backups.get(str(day)) or missing_backup(str(day)) for day in days],
		"pending": waiting and state == "pending",
		"unconfirmed": waiting and state == "unavailable",
	}


def has_gaps(backups: dict[str, dict], days: list[date]) -> bool:
	return any(str(day) not in backups for day in days)


def needs_bucket(backups: dict[str, dict], days: list[date]) -> bool:
	"""A failed run still leaves a day worth looking for, so it is not the end of the search."""
	return has_gaps(backups, days) or any(day["status"] == "Failure" for day in backups.values())


def merge_stored(backups: dict[str, dict], stored: dict[str, dict]) -> dict[str, dict]:
	"""An object sitting in the bucket outranks a job row saying the run did not finish."""
	merged = dict(backups)
	for day, entry in stored.items():
		if merged.get(day, {}).get("status") in (None, "Failure"):
			merged[day] = entry
	return merged


def get_agent_backup_jobs(site: str, start: date, end: date) -> tuple[dict[str, dict], str]:
	"""What the site's server remembers running, and how far the asking got.

	Walking the job database takes seconds, so the server does it as a job and the answer
	arrives on the next look. Only the current server is asked: jobs a site ran before
	moving stay on the server it left, and its objects come from the buckets it used.
	"""
	server = frappe.db.get_value("Site", site, "server")
	if not server:
		return {}, "unavailable"

	answer = frappe.cache().get_value(agent_answer_key(site, start, end))
	if answer is None:
		return {}, request_agent_backup_jobs(server, site, start, end)

	days: dict[str, dict] = {}
	for job in answer["jobs"]:
		day = str(getdate(job["start"])) if job.get("start") else None
		# A day that ran twice is answered by whichever run got furthest
		if not day or outranks(days.get(day), job):
			continue
		days[day] = backup_from_job(day, job)
	# A truncated answer dropped the oldest days in the range, so it is not the whole story
	return days, "unavailable" if answer.get("truncated") else "answered"


def request_agent_backup_jobs(server: str, site: str, start: date, end: date) -> str:
	"""Queue the read, unless this server has already shown it cannot do it."""
	if is_agent_silenced(server):
		return "unavailable"

	try:
		# Deduplicated by Agent, so a second look while one is running adds nothing
		Agent(server).fetch_site_backup_jobs(site, str(start), str(end))
	except Exception:
		silence_agent(server)
		return "unavailable"
	return "pending"


def agent_answer_key(site: str, start, end) -> str:
	return f"backup_audit_trail_jobs:{site}:{start}:{end}"


def process_fetch_backup_jobs_update(job):
	"""Put the server's answer where the audit trail looks for it, or stop asking."""
	if job.status in ("Failure", "Delivery Failure"):
		# An agent without the route fails every time, so leave it alone for a while
		silence_agent(job.server)
		return
	if job.status != "Success" or not job.data:
		return

	query = parse_qs(urlparse(job.request_path).query)
	site, start, end = query.get("site"), query.get("start"), query.get("end")
	if not (site and start and end):
		return

	frappe.cache().set_value(
		agent_answer_key(site[0], start[0], end[0]),
		frappe.parse_json(job.data),
		expires_in_sec=CACHE_TTL,
	)


def agent_silence_key(server: str) -> str:
	return f"backup_audit_trail_agent_unavailable:{server}"


def is_agent_silenced(server: str) -> bool:
	return bool(frappe.cache().get_value(agent_silence_key(server)))


def silence_agent(server: str):
	frappe.cache().set_value(agent_silence_key(server), 1, expires_in_sec=AGENT_SILENCE_TTL)


def outranks(existing: dict | None, job: dict) -> bool:
	if not existing:
		return False
	return existing["status"] == "Success" and job["status"] != "Success"


def backup_from_job(day: str, job: dict) -> dict:
	status = "Success" if job["status"] == "Success" else "Failure"
	sizes = job.get("sizes") or {}
	return (
		missing_backup(day)
		| {"status": status}
		| {artifact: cint(sizes.get(key)) for key, artifact in ARTIFACT_BY_JOB_KEY.items()}
	)


def get_cached_history(site: str, start: date, end: date) -> dict | None:
	if end >= getdate():
		return None
	return frappe.cache().get_value(cache_key(site, start, end))


def cache_history(site: str, start: date, end: date, history: dict):
	"""Only a finished, fully answered range is worth keeping."""
	if end >= getdate() or history["pending"] or history["unconfirmed"]:
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
	credentials = get_offsite_credentials()
	if not credentials:
		return {}

	days: dict[str, dict] = {}
	for bucket in get_site_buckets(site):
		# The current cluster's bucket is walked first, so it wins where both hold a day
		for day, entry in list_bucket(bucket, site, start, end, credentials).items():
			days.setdefault(day, entry)
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


def list_bucket(
	bucket: dict, site: str, start: date, end: date, credentials: tuple[str, str]
) -> dict[str, dict]:
	"""Walk the site's prefix in one bucket, sizing what is held per day."""
	prefix = f"{site}/"
	pages = (
		get_s3_client(bucket, credentials)
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


def get_s3_client(bucket: dict, credentials: tuple[str, str]):
	access_key, secret_key = credentials
	return client(
		"s3",
		aws_access_key_id=access_key,
		aws_secret_access_key=secret_key,
		region_name=bucket["region"],
		endpoint_url=bucket["endpoint_url"],
	)
