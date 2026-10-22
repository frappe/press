# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime

# Every five minutes: three hours of Grove being down, then Failed and a Retry button.
MAX_ATTEMPTS = 36
# The cron leaves a row the immediate job may still be on: one it has not touched in this long.
RETRY_AFTER_MINUTES = 4


class GroveKeyRequest(Document):
	"""One trial site's Grove (AI) key, tried until it sits in the site config as `ai_keys` or the
	attempts run out. One row per site (`site` is unique) and one mint per row: what Grove answered
	stays on the row (the secret in a Password field, cleared on Success), so a retry after a
	half-done try writes the config again rather than asking Grove, which titles a key by the site
	and refuses a second one for it."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Password | None
		attempts: DF.Int
		gateway_url: DF.Data | None
		geography: DF.Data | None
		grove_key: DF.Data | None
		last_error: DF.SmallText | None
		product_trial_request: DF.Link | None
		site: DF.Link
		status: DF.Literal["Pending", "Success", "Failed", "Revoked"]
		team: DF.Data | None
	# end: auto-generated types

	def after_insert(self):
		frappe.enqueue_doc(self.doctype, self.name, "attempt", enqueue_after_commit=True)

	@frappe.whitelist()
	def attempt(self):
		"""One try: mint unless minted, then the config. A failure counts on the row; no Error Log
		per try, the row is the record."""
		if self.status != "Pending":
			return
		try:
			self.mint()
			self.write_config()
		except Exception as e:
			self.attempts += 1
			self.last_error = str(e)[:500]
			self.status = "Failed" if self.attempts >= MAX_ATTEMPTS else "Pending"
			self.save()
			return
		self.update({"status": "Success", "api_key": None, "last_error": ""})
		self.save()

	def mint(self):
		"""Grove's answer onto the row, once, with the team it was minted under. `save` keeps the
		secret encrypted."""
		if self.grove_key:
			return
		settings = frappe.get_cached_doc("Grove Settings")
		minted = settings.provision_key(self.site)
		self.update(
			{
				"grove_key": minted["name"],
				"team": settings.trial_team,
				"geography": minted["geography"],
				"gateway_url": minted["gateway_url"],
				"api_key": minted["api_key"],
			}
		)
		self.save()

	def write_config(self):
		"""`ai_keys` into the site config; a retry runs it again, every step of it idempotent."""
		ensure_site_config_key("ai_keys", "JSON")
		frappe.get_doc("Site", self.site).update_site_config({"ai_keys": [self.key_row]})

	@property
	def key_row(self) -> dict:
		"""What `ai_keys` carries: the shape a Frappe Cloud server gets for its team's keys."""
		return {
			"name": self.grove_key,
			"title": self.site,
			"geography": self.geography,
			"gateway_url": self.gateway_url,
			"api_key": self.get_password("api_key"),
		}

	@frappe.whitelist()
	def retry(self):
		"""Desk button on a Failed row: from the top, now. A key already minted is kept."""
		self.update({"status": "Pending", "attempts": 0, "last_error": ""})
		self.save()
		self.attempt()


def ensure_site_config_key(key: str, type: str):
	"""An internal Site Config Key: the dashboard neither lists nor edits it, so the customer
	cannot lift the value out of the site config."""
	if not frappe.db.exists("Site Config Key", {"key": key}):
		frappe.get_doc(doctype="Site Config Key", internal=True, key=key, type=type).insert(
			ignore_permissions=True
		)


def run_pending():
	"""Cron, every five minutes: every Pending row the immediate job has not touched lately."""
	stale = add_to_date(now_datetime(), minutes=-RETRY_AFTER_MINUTES)
	for name in frappe.get_all(
		"Grove Key Request", filters={"status": "Pending", "modified": ("<", stale)}, pluck="name"
	):
		frappe.get_doc("Grove Key Request", name).attempt()


def revoke_archived():
	"""Hourly: a trial site archived takes its key with it. Grove refuses a revoke inside six hours
	of the mint and may be down: the row keeps Success and the reason, and next hour tries again."""
	settings = frappe.get_cached_doc("Grove Settings")
	if not settings.is_enrolled:
		return
	request, site = frappe.qb.DocType("Grove Key Request"), frappe.qb.DocType("Site")
	rows = (
		frappe.qb.from_(request)
		.join(site)
		.on(site.name == request.site)
		.select(request.name, request.grove_key, request.team)
		.where((request.status == "Success") & (site.status == "Archived"))
	).run(as_dict=True)
	for row in rows:
		try:
			settings.revoke_key(row.grove_key, row.team)
		except Exception as e:
			frappe.db.set_value("Grove Key Request", row.name, "last_error", str(e)[:500])
			continue
		frappe.db.set_value("Grove Key Request", row.name, {"status": "Revoked", "last_error": ""})
