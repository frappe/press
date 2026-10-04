# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import hmac
import re
import secrets
from zoneinfo import ZoneInfo

import frappe
from frappe.model.document import Document
from frappe.utils import (
	add_to_date,
	cint,
	get_datetime,
	get_system_timezone,
	get_url,
	now_datetime,
	sha256_hash,
)

from press.press.doctype.remote_file.remote_file import RemoteFile
from press.press.doctype.site.site import Site
from press.press.doctype.site_activity.site_activity import log_site_activity

PENDING_MINUTES = 10
APPROVED_HOURS = 12
DOWNLOAD_LINK_SECONDS = 24 * 60 * 60
MAX_FAILED_ATTEMPTS = 5
# The longest a token can be used: pending, then approved.
TOKEN_SECONDS = PENDING_MINUTES * 60 + APPROVED_HOURS * 60 * 60
BACKUPS_PAGE_LENGTH = 5
BACKUP_PARTS = ("database", "public", "private", "config")


class V1MigrationRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		approved_at: DF.Datetime | None
		approved_by: DF.Link | None
		domain: DF.Data | None
		expires_at: DF.Datetime | None
		failed_attempts: DF.Int
		requester_ip: DF.Data | None
		site: DF.Link | None
		status: DF.Literal["Pending", "Approved", "Rejected", "Revoked"]
		team: DF.Link | None
	# end: auto-generated types

	@property
	def is_expired(self) -> bool:
		return now_datetime() >= get_datetime(self.expires_at)

	@property
	def is_active(self) -> bool:
		"""A site moved to another team since approval ends the access."""
		return (
			self.status == "Approved"
			and not self.is_expired
			and frappe.db.get_value("Site", self.site, "team") == self.team
		)

	@property
	def code_cache_key(self) -> str:
		"""Holds the code's hash while the request waits. Listed in persistent_cache_keys."""
		return f"v1_migration_request||code||{self.name}"

	@property
	def approval_url(self) -> str:
		return f"{get_url()}/dashboard/sites?v1-migration={self.name}"

	def approve(self, code: str) -> None:
		code_hash = frappe.cache.get_value(self.code_cache_key)
		if self.status != "Pending" or self.is_expired or not code_hash:
			frappe.throw("This request has expired. Start again from Pilot.")
		if not hmac.compare_digest(sha256_hash(code.strip().upper()), code_hash):
			self.reject_code()

		self.status = "Approved"
		self.team = frappe.db.get_value("Site", self.site, "team")
		self.approved_by = frappe.session.user
		self.approved_at = now_datetime()
		self.expires_at = add_to_date(self.approved_at, hours=APPROVED_HOURS)
		self.save(ignore_permissions=True)
		frappe.cache.delete_value(self.code_cache_key)
		reason = f"Pilot at {self.requester_ip} can access the backups for {APPROVED_HOURS} hours."
		log_site_activity(self.site, "Authorize Backup Access", reason=reason)

	def reject_code(self) -> None:
		self.failed_attempts += 1
		if self.failed_attempts >= MAX_FAILED_ATTEMPTS:
			self.status = "Rejected"
			frappe.cache.delete_value(self.code_cache_key)
		self.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.throw("The pass code is not correct.")  # nosemgrep

	def revoke(self) -> None:
		"""Pilot cancels a pending request too, so it can no longer be approved."""
		if self.status in ("Pending", "Approved"):
			self.db_set("status", "Revoked")
		frappe.cache.delete_value(self.code_cache_key)

	def get_backups(self, start: int = 0) -> list[dict]:
		backups = frappe.get_all(
			"Site Backup",
			filters=self.downloadable_backup_filters,
			fields=["name", "creation", "database_size", "public_size", "private_size"],
			order_by="creation desc",
			limit_start=start,
			limit_page_length=BACKUPS_PAGE_LENGTH,
		)
		return [
			{
				"name": backup.name,
				"created_at": to_iso(backup.creation),
				"size": cint(backup.database_size) + cint(backup.public_size) + cint(backup.private_size),
			}
			for backup in backups
		]

	@property
	def downloadable_backup_filters(self) -> dict:
		"""The backups Pilot may list and download. Rotation and archival keep some files of
		an unavailable backup, so its links must not be issued either."""
		return {
			"site": self.site,
			"status": "Success",
			"offsite": 1,
			"with_files": 1,
			"files_availability": ("!=", "Unavailable"),
		}

	def get_running_backup(self) -> str | None:
		return frappe.db.get_value(
			"Site Backup",
			{"site": self.site, "status": ("in", ("Pending", "Running")), "offsite": 1, "with_files": 1},
			"name",
			order_by="creation desc",
		)

	def take_backup(self) -> str:
		return Site("Site", self.site).backup(with_files=True, offsite=True).name

	def get_backup_status(self, backup: str) -> dict:
		"""With the job's dashboard link, so Pilot can show the progress."""
		values = self.get_site_backup(backup, ["status", "job"], as_dict=True)
		job_url = values.job and f"{get_url()}/dashboard/sites/{self.site}/insights/jobs/{values.job}"
		return {"status": values.status, "job_url": job_url or None}

	def get_download_links(self, backup: str) -> dict[str, str]:
		files = self.get_site_backup(
			backup,
			[f"remote_{part}_file" for part in BACKUP_PARTS],
			as_dict=True,
			filters=self.downloadable_backup_filters,
		)
		log_site_activity(
			self.site, "Access Offsite Backups", reason=f"Pilot downloaded the backup {backup}."
		)
		return {
			part: RemoteFile("Remote File", remote_file).get_download_link(
				DOWNLOAD_LINK_SECONDS, log_activity=False
			)
			for part in BACKUP_PARTS
			if (remote_file := files[f"remote_{part}_file"])
		}

	def get_site_backup(self, backup: str, fields, as_dict: bool = False, filters: dict | None = None):
		values = frappe.db.get_value(
			"Site Backup", {**(filters or {"site": self.site}), "name": backup}, fields, as_dict=as_dict
		)
		if not values:
			frappe.throw("The backup does not exist.", frappe.DoesNotExistError)
		return values


def create_request(domain: str, code: str) -> tuple[V1MigrationRequest, str]:
	"""A pending request and the token Pilot keeps. The token and the code live only in the
	cache. An unknown domain gets a request no one can approve, so the answer never tells which
	sites exist."""
	if not re.fullmatch(r"[A-Z0-9]{8}", code) or code.isdigit():
		frappe.throw("The pass code must have 8 letters and digits.")  # nosemgrep

	domain = domain.strip().lower().removeprefix("https://").removeprefix("http://").rstrip("/")
	site = find_site(domain)
	token = secrets.token_urlsafe(32)
	request = frappe.get_doc(
		{
			"doctype": "V1 Migration Request",
			"site": site,
			"domain": domain,
			"team": site and frappe.db.get_value("Site", site, "team"),
			"requester_ip": frappe.local.request_ip,
			"expires_at": add_to_date(now_datetime(), minutes=PENDING_MINUTES),
		}
	).insert(ignore_permissions=True)
	frappe.cache.set_value(request.code_cache_key, sha256_hash(code), expires_in_sec=PENDING_MINUTES * 60)
	frappe.cache.set_value(token_cache_key(token), request.name, expires_in_sec=TOKEN_SECONDS)
	return request, token


def find_site(domain: str) -> str | None:
	site = frappe.db.get_value("Site Domain", domain, "site") or domain
	if frappe.db.get_value("Site", site, "status") in (None, "Archived"):
		return None
	return site


def find_request(token: str) -> V1MigrationRequest:
	"""The request's status and expiry still decide whether the token gives access."""
	name = token and frappe.cache.get_value(token_cache_key(token))
	if not name:
		frappe.throw("The token is not valid.", frappe.AuthenticationError)
	return V1MigrationRequest("V1 Migration Request", name)


def token_cache_key(token: str) -> str:
	"""Hashed, so the cache never holds a usable token. Listed in persistent_cache_keys."""
	return f"v1_migration_request||token||{sha256_hash(token)}"


def to_iso(value) -> str:
	"""With its offset, as Pilot runs in another timezone."""
	return get_datetime(value).replace(tzinfo=ZoneInfo(get_system_timezone())).isoformat()
