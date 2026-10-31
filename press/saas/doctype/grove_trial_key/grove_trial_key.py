# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, cint, now_datetime

if TYPE_CHECKING:
	from press.saas.doctype.grove_settings.grove_settings import GroveSettings
	from press.saas.doctype.product_trial_request.product_trial_request import ProductTrialRequest

# One batch per run keeps the job short.
REFILL_BATCH_SIZE = 50
# A revoke Grove refused is tried again once the record has sat this long.
RETRY_AFTER_MINUTES = 60


class GroveTrialKey(Document):
	"""One Grove key minted ahead under the trial team and held here with its secret, until a
	Product Trial site takes it into its site config as `ai_keys`. Press revokes it once the site
	is archived; Grove retires it on its own, Trial Key Expiry after its first use."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Password | None
		assigned_at: DF.Datetime | None
		gateway_url: DF.Data | None
		geography: DF.Data | None
		grove_key: DF.Data
		product_trial_request: DF.Link | None
		site: DF.Link | None
		status: DF.Literal["Available", "Assigned", "Revoking", "Revoked"]
		team: DF.Data | None
	# end: auto-generated types

	@classmethod
	def provision(cls, settings: GroveSettings) -> GroveTrialKey:
		"""Mint one key into the pool. A crash between the mint and the insert leaves a capped,
		untitled key under the trial team that no record names; Grove Desk shows it."""
		minted = settings.provision_key()
		return frappe.get_doc(
			{
				"doctype": "Grove Trial Key",
				"grove_key": minted["name"],
				"team": settings.trial_team,
				"geography": minted["geography"],
				"gateway_url": minted["gateway_url"],
				"api_key": minted["api_key"],
			}
		).insert(ignore_permissions=True)

	@classmethod
	def assign(cls, request: ProductTrialRequest) -> GroveTrialKey | None:
		"""The oldest ready key for the request's site; none on an empty pool. A site that reached
		Site Created before keeps the key it took."""
		if name := frappe.db.get_value("Grove Trial Key", {"site": request.site, "status": "Assigned"}):
			return frappe.get_doc("Grove Trial Key", name)

		name = frappe.db.get_value(
			"Grove Trial Key",
			{"status": "Available"},
			order_by="creation asc",
			for_update=True,
			skip_locked=True,
		)
		if not name:
			return None

		key = frappe.get_doc("Grove Trial Key", name)
		key.db_set(
			{
				"status": "Assigned",
				"site": request.site,
				"product_trial_request": request.name,
				"assigned_at": now_datetime(),
			}
		)
		return key

	def get_site_config(self) -> dict:
		"""The site config entry apps read a Grove key from: the shape Central writes for its own
		trial servers."""
		return {"ai_keys": [{"gateway_url": self.gateway_url, "api_key": self.get_password("api_key")}]}

	def write_config(self) -> None:
		"""`ai_keys` into the site config, an agent job; safe to repeat."""
		ensure_site_config_key("ai_keys", "JSON")
		frappe.get_doc("Site", self.site).update_site_config(self.get_site_config())

	@classmethod
	def queue_revoke(cls, **filters) -> None:
		"""Mark the matching ready or assigned keys Revoking and queue their revoke at Grove."""
		for name in frappe.get_all(
			"Grove Trial Key",
			filters={**filters, "status": ("in", ("Available", "Assigned"))},
			pluck="name",
		):
			frappe.db.set_value("Grove Trial Key", name, "status", "Revoking")
			frappe.enqueue(
				"press.saas.doctype.grove_trial_key.grove_trial_key.revoke_trial_key",
				name=name,
				enqueue_after_commit=True,
			)

	@frappe.whitelist(methods=["POST"])
	def revoke(self) -> None:
		self.check_permission("write")
		if self.status not in ("Available", "Assigned"):
			frappe.throw(_("Only an available or assigned key can be revoked."))

		self.queue_revoke(name=self.name)

	def on_trash(self) -> None:
		# A record must outlive its live key, so that a failed revoke is retried.
		if self.status != "Revoked":
			frappe.throw(_("Use Revoke Key. Only a revoked key record can be deleted."))

	def revoke_at_grove(self) -> None:
		"""Under the team the key was minted under. Safe to repeat: Grove answers a revoked key's
		revoke as done."""
		frappe.get_cached_doc("Grove Settings").revoke_key(self.grove_key, self.team)
		self.db_set("status", "Revoked", commit=True)


def ensure_site_config_key(key: str, type: str) -> None:
	"""An internal Site Config Key: the dashboard neither lists nor edits it, so the customer
	cannot lift the value out of the site config."""
	if not frappe.db.exists("Site Config Key", {"key": key}):
		frappe.get_doc(doctype="Site Config Key", internal=True, key=key, type=type).insert(
			ignore_permissions=True
		)


def revoke_trial_key(name: str) -> None:
	key = frappe.get_doc("Grove Trial Key", name)
	if key.status == "Revoking":
		key.revoke_at_grove()


def refill_trial_keys() -> None:
	"""Cron, every five minutes: retry the revokes Grove refused, then mint what the pool is
	missing, up to one batch. Nothing while Press is not enrolled or the pool is off."""
	settings = frappe.get_cached_doc("Grove Settings")
	if not settings.is_on_for_product_trials:
		return

	retry_revokes()
	missing = cint(settings.trial_pool_size) - frappe.db.count("Grove Trial Key", {"status": "Available"})
	for _attempt in range(min(missing, REFILL_BATCH_SIZE)):
		try:
			GroveTrialKey.provision(settings)
		except Exception:
			frappe.log_error(title="Grove trial key mint failed")
			break


def retry_revokes() -> None:
	"""A Revoking record left alone for an hour is tried again. Why Grove refused is Grove's to say;
	each attempt writes the record, so `modified` spaces the attempts."""
	stale = add_to_date(now_datetime(), minutes=-RETRY_AFTER_MINUTES)
	for name in frappe.get_all(
		"Grove Trial Key", filters={"status": "Revoking", "modified": ("<", stale)}, pluck="name"
	):
		key = frappe.get_doc("Grove Trial Key", name)
		try:
			key.revoke_at_grove()
		except Exception:
			key.db_set("status", "Revoking")
			frappe.log_error(title=f"Grove trial key revoke failed for {name}")


def revoke_archived() -> None:
	"""Hourly: a trial site archived takes its key with it. Grove refuses a revoke inside six hours
	of the mint; the record stays Revoking and the refill job tries again once it has sat an hour."""
	if not frappe.get_cached_doc("Grove Settings").is_enrolled:
		return
	key, site = frappe.qb.DocType("Grove Trial Key"), frappe.qb.DocType("Site")
	names = (
		frappe.qb.from_(key)
		.join(site)
		.on(site.name == key.site)
		.select(key.name)
		.where((key.status == "Assigned") & (site.status == "Archived"))
	).run(pluck=True)
	if names:
		GroveTrialKey.queue_revoke(name=("in", names))
