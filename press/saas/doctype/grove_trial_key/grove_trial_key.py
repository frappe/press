# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import add_to_date, cint, flt, now_datetime

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site
	from press.saas.doctype.grove_settings.grove_settings import GroveSettings
	from press.saas.doctype.grove_trial_product.grove_trial_product import GroveTrialProduct

# One batch per run keeps the job short.
REFILL_BATCH_SIZE = 50
# A revoke Grove refused is tried again once the record has sat this long.
RETRY_AFTER_MINUTES = 60


class GroveTrialKey(Document):
	"""One Grove key minted ahead under the trial team for one Product Trial and held here with its
	secret, until a site of that product takes it into its site config as `ai_keys`. The key carries
	no expiry at Grove: Press revokes it once the site is archived, or once Grove Settings' Revokes
	Automatically After days have passed since the site took it."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Password | None
		assigned_at: DF.Datetime | None
		cap: DF.Currency
		gateway_url: DF.Data | None
		geography: DF.Data | None
		grove_key: DF.Data
		last_error: DF.SmallText | None
		product_trial: DF.Link | None
		product_trial_request: DF.Link | None
		site: DF.Link | None
		status: DF.Literal["Available", "Assigned", "Revoking", "Revoked"]
		team: DF.Data | None
	# end: auto-generated types

	@classmethod
	def provision(cls, settings: GroveSettings, row: GroveTrialProduct) -> GroveTrialKey:
		"""Mint one key into `row`'s product's pool, titled at Grove by this record's id (taken from the
		series before the mint), in the row's Model Group on top of the team's when it names one. A
		crash between the mint and the insert leaves a capped key under the trial team titled by an id
		no record carries; Grove Desk shows it."""
		name = make_autoname(frappe.get_meta("Grove Trial Key").autoname)
		minted = settings.provision_key(row, title=name)
		return frappe.get_doc(
			{
				"doctype": "Grove Trial Key",
				"grove_key": minted["name"],
				"product_trial": row.product_trial,
				"team": settings.trial_team,
				"geography": minted["geography"],
				"gateway_url": minted["gateway_url"],
				"cap": cint(settings.trial_key_cap),
				"api_key": minted["api_key"],
			}
		).insert(set_name=name, ignore_permissions=True)

	@classmethod
	def assign(cls, site: Site, product_trial: str, request: str | None = None) -> GroveTrialKey | None:
		"""The oldest ready key of the product, taken for the site and written into its configuration;
		the job the caller raises carries it. None on an empty pool or while assignment is paused: the
		trial runs without AI."""
		if frappe.db.get_single_value("Grove Settings", "pause_key_assignment"):
			return None

		name = frappe.db.get_value(
			"Grove Trial Key",
			{"status": "Available", "product_trial": product_trial},
			order_by="creation asc",
			for_update=True,
			skip_locked=True,
		)
		if not name:
			return None

		key = cls("Grove Trial Key", name)
		key.db_set(
			{
				"status": "Assigned",
				"site": site.name,
				"product_trial_request": request,
				"assigned_at": now_datetime(),
			}
		)
		key.write_config(site)
		return key

	def write_config(self, site: Site) -> None:
		"""`ai_keys` into the site's configuration, the shape Central writes for its own trial servers.
		The caller saves: a new site carries it in its creation job, a standby site in its config job."""
		ensure_site_config_key("ai_keys", "JSON")
		site._update_configuration(
			{"ai_keys": [{"gateway_url": self.gateway_url, "api_key": self.get_password("api_key")}]},
			save=False,
		)

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

	@frappe.whitelist(methods=["POST"])
	def raise_cap(self, cap: float) -> None:
		"""Lift the cap of a running site's key at Grove. Only an Assigned record is one: a revoke
		moves it on, and a ready key's cap is the setting's."""
		self.check_permission("write")
		if self.status != "Assigned":
			frappe.throw(_("Only the key of a running trial site can have its cap raised."))
		if flt(cap) <= flt(self.cap):
			frappe.throw(_("The cap is {0} USD already; enter more.").format(self.cap))

		frappe.get_cached_doc("Grove Settings").update_caps(self.team, {self.grove_key: flt(cap)})
		self.db_set("cap", flt(cap))

	def on_trash(self) -> None:
		# A record must outlive its live key, so that a failed revoke is retried.
		if self.status != "Revoked":
			frappe.throw(_("Use Revoke Key. Only a revoked key record can be deleted."))

	def revoke_at_grove(self) -> None:
		"""Under the team the key was minted under. Safe to repeat: Grove answers a revoked key's
		revoke as done."""
		frappe.get_cached_doc("Grove Settings").revoke_key(self.grove_key, self.team)
		self.db_set({"status": "Revoked", "last_error": None}, commit=True)

	def try_revoke_at_grove(self) -> None:
		"""One try. A refusal (Grove's six-hour mint guard, Grove down) is kept on the record as
		`last_error`; the write spaces the hourly retries."""
		try:
			self.revoke_at_grove()
		except Exception as error:
			frappe.log_error(title=f"Grove trial key revoke failed for {self.name}")
			self.db_set({"status": "Revoking", "last_error": str(error) or type(error).__name__})


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
		key.try_revoke_at_grove()


def refill_trial_keys() -> None:
	"""Cron, every five minutes: retry the revokes Grove refused, revoke the keys past their days,
	then mint the keys each product's pool is missing, up to one batch across them. Nothing while
	Press is not enrolled; the retries and the revokes run with the pools off or paused too, the
	mint does not."""
	settings: GroveSettings = frappe.get_cached_doc("Grove Settings")
	if not settings.is_enrolled:
		return

	retry_revokes()
	revoke_expired_keys(settings)
	if settings.pause_pool_refill:
		return
	budget = REFILL_BATCH_SIZE
	for row in settings.trial_products:
		ready = frappe.db.count(
			"Grove Trial Key", {"status": "Available", "product_trial": row.product_trial}
		)
		for _attempt in range(min(cint(row.pool_size) - ready, budget)):
			try:
				GroveTrialKey.provision(settings, row)
			except Exception:
				frappe.log_error(title="Grove trial key mint failed")
				return
			budget -= 1


def retry_revokes() -> None:
	"""A Revoking record left alone for an hour is tried again. Why Grove refused is Grove's to say;
	each attempt writes the record, so `modified` spaces the attempts."""
	stale = add_to_date(now_datetime(), minutes=-RETRY_AFTER_MINUTES)
	for name in frappe.get_all(
		"Grove Trial Key", filters={"status": "Revoking", "modified": ("<", stale)}, pluck="name"
	):
		frappe.get_doc("Grove Trial Key", name).try_revoke_at_grove()


def revoke_expired_keys(settings: GroveSettings) -> None:
	"""An Assigned key older than Revokes Automatically After since its site took it is revoked,
	whatever the site is doing: the site runs on without AI. 0 turns this off."""
	days = cint(settings.trial_key_revoke_after_days)
	if not days:
		return

	# Only an Assigned key has an assignment: a `<` alone would also match the NULL of a ready
	# key, which Frappe compares as the oldest date.
	expired = frappe.get_all(
		"Grove Trial Key",
		filters={"status": "Assigned", "assigned_at": ("<", add_to_date(now_datetime(), days=-days))},
		pluck="name",
	)
	if expired:
		GroveTrialKey.queue_revoke(name=("in", expired))


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
