# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Lets Pilot copy the backups of a Frappe Cloud site after its team approves."""

from __future__ import annotations

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from press.api.client import is_owned_by_team
from press.guards import role_guard
from press.press.doctype.v1_migration_request.v1_migration_request import (
	V1MigrationRequest,
	create_request,
	find_request,
	to_iso,
	token_cache_key,
)
from press.utils import user as utils_user
from press.utils.user import as_administrator

TOKEN_HEADER = "X-Press-Migration-Token"
NO_ACCESS_MESSAGE = "You do not have access to allow this request. Ask the owner of the site to approve it."


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60)
def request_access(domain: str, code: str) -> dict:
	request, token = create_request(domain, code)
	return {
		"request": request.name,
		"site": request.domain,
		"token": token,
		"approval_url": request.approval_url,
		"expires_at": to_iso(request.expires_at),
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=720, seconds=60 * 60)
def get_status() -> dict:
	request = find_request(frappe.get_request_header(TOKEN_HEADER) or "")
	status = "Expired" if request.status in ("Pending", "Approved") and request.is_expired else request.status
	return {
		"status": status,
		"site": request.domain,
		"expires_at": to_iso(request.expires_at),
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=120, seconds=60 * 60)
def get_backups(start: int = 0) -> list[dict]:
	return active_request().get_backups(max(cint(start), 0))


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=720, seconds=60 * 60)
def get_running_backup() -> str | None:
	return active_request().get_running_backup()


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def take_backup() -> str:
	request = active_request()
	with as_administrator():  # Site.backup inserts a Site Backup as the session user
		return request.take_backup()


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=1500, seconds=60 * 60)  # Pilot polls every 3 seconds, which is 1200 an hour
def get_backup_status(backup: str) -> dict:
	return active_request().get_backup_status(backup)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60 * 60)
def get_download_links(backup: str) -> dict[str, str]:
	request = active_request()
	with as_administrator():  # Each link logs a Site Activity as the session user
		return request.get_download_links(backup)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60 * 60)
def revoke() -> None:
	token = frappe.get_request_header(TOKEN_HEADER) or ""
	find_request(token).revoke()
	frappe.cache.delete_value(token_cache_key(token))


@frappe.whitelist()
def get_request(name: str) -> dict:
	request = owned_request(name)
	return {
		"name": request.name,
		"site": request.site,
		"status": request.status,
		"requester_ip": request.requester_ip,
		"creation": request.creation,
		"is_expired": request.is_expired,
	}


@frappe.whitelist(methods=["POST"])
def approve_request(name: str, code: str) -> None:
	owned_request(name).approve(code)


def active_request() -> V1MigrationRequest:
	"""The approved request of the token. The caller stays Guest."""
	request = find_request(frappe.get_request_header(TOKEN_HEADER) or "")
	if not request.is_active:
		frappe.throw("The access has expired or was revoked.", frappe.AuthenticationError)
	return request


def owned_request(name: str) -> V1MigrationRequest:
	"""One message for every refusal, so it never tells whether the request or its site exists."""
	site = frappe.db.get_value("V1 Migration Request", name, "site")
	if not site or not is_owned_by_team("Site", site, raise_exception=False) or not can_manage_site(site):
		frappe.throw(NO_ACCESS_MESSAGE, frappe.PermissionError)
	return V1MigrationRequest("V1 Migration Request", name)


def can_manage_site(site: str) -> bool:
	"""The check of `role_guard.document`, as a value instead of an error."""
	return (
		not role_guard.roles_enabled()
		or role_guard.skip_roles()
		or utils_user.is_system_manager()
		or bool(role_guard.check("Site", site))
	)
