# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.query_builder import Case, CustomFunction
from frappe.query_builder.functions import Coalesce, Count, CurDate, Floor, Min, Star

BAND_DAYS = 30
OLDEST_BAND_DAYS = 360
COMPLETED_MOVES = ("Success", "Recovered")

Least = CustomFunction("LEAST", ["value", "cap"])
Greatest = CustomFunction("GREATEST", ["value", "floor"])
# pypika ships the three argument SQL Server DATEDIFF, not the two argument one
DateDiff = CustomFunction("DATEDIFF", ["end", "start"])


class SiteVersionAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		backfilled: DF.Check
		date: DF.Date
		days_since_update: DF.Int
		frappe_version: DF.Data
		public_bench: DF.Check
		sites: DF.Int
	# end: auto-generated types


def record_audit():
	"""Record how old the frappe running on each active site is today.

	Press keeps no history of fleet state, so the only way to see whether the
	stale tail is shrinking is to write down the distribution every day.
	"""
	save_audit(frappe.utils.today(), count_sites_by_version_and_age())
	frappe.db.commit()


def save_audit(date: str, counts: list[dict], backfilled: bool = False):
	"""Replace the rows for a date, so a rerun cannot double count.

	Does not commit. The caller owns the transaction, so a test can roll this
	back instead of leaving its fixtures behind in the database.
	"""
	frappe.db.delete("Site Version Audit", {"date": date})
	for row in counts:
		frappe.get_doc(doctype="Site Version Audit", date=date, backfilled=backfilled, **row).insert(
			ignore_permissions=True
		)


def count_sites_by_version_and_age() -> list[dict]:
	"""Active sites grouped by version and by the age of their frappe release."""
	site = frappe.qb.DocType("Site")
	query = frappe.qb.from_(site).where(site.status == "Active")
	return _count_by_version_and_age(query, site.bench, site.group, CurDate()).run(as_dict=True)


def count_sites_by_version_and_age_on(month_end: str) -> list[dict]:
	"""The same counts for a past date, rewound through Site Update.

	A site's bench and group before a move are frozen on the Site Update row, and
	those rows are never pruned, so the earliest move after `month_end` says where
	the site was then. A site with no later move never moved, so it still sits
	where it sits now.

	This can only see sites that are still active, so it undercounts. Rows it
	produces are marked `backfilled`.
	"""
	site = frappe.qb.DocType("Site")
	move = _earliest_move_after(month_end)
	query = (
		frappe.qb.from_(site)
		.left_join(move)
		.on(move.site == site.name)
		.where((site.status == "Active") & (site.creation <= month_end))
	)
	return _count_by_version_and_age(
		query,
		Coalesce(move.source_bench, site.bench),
		Coalesce(move.source_group, site.group),
		month_end,
	).run(as_dict=True)


def _count_by_version_and_age(query, bench, group, as_of):
	"""Add the version and release lookups, and count sites per band."""
	release_group = frappe.qb.DocType("Release Group")
	frappe_version = frappe.qb.DocType("Frappe Version")
	bench_app = frappe.qb.DocType("Bench App")
	app_release = frappe.qb.DocType("App Release")

	version = Coalesce(frappe_version.name, "Unknown")
	band = _age_band(app_release, as_of)
	public = Case().when(release_group.public | release_group.central_bench, 1).else_(0)

	return (
		query.left_join(release_group)
		.on(release_group.name == group)
		.left_join(frappe_version)
		.on(frappe_version.name == release_group.version)
		.left_join(bench_app)
		.on(
			(bench_app.parent == bench)
			& (bench_app.parenttype == "Bench")
			& (bench_app.parentfield == "apps")
			& (bench_app.app == "frappe")
		)
		.left_join(app_release)
		.on(app_release.name == bench_app.release)
		.select(
			version.as_("frappe_version"),
			band.as_("days_since_update"),
			public.as_("public_bench"),
			Count(Star()).as_("sites"),
		)
		.groupby(version, band, public)
	)


def _age_band(app_release, as_of):
	"""Age of the deployed release in 30 day bands, capped at a year.

	`timestamp` is the commit time but is unset on most releases, so fall back to
	`creation`, the time Press recorded the release.
	"""
	released_at = Coalesce(app_release.timestamp, app_release.creation)
	age = Greatest(DateDiff(as_of, released_at), 0)
	return Least(Floor(age / BAND_DAYS) * BAND_DAYS, OLDEST_BAND_DAYS)


def _earliest_move_after(month_end: str):
	"""Where each site sat before its first completed move after a date."""
	update = frappe.qb.DocType("Site Update")
	first_move = (
		frappe.qb.from_(update)
		.select(update.site, Min(update.creation).as_("moved_at"))
		.where(update.status.isin(COMPLETED_MOVES) & (update.creation > month_end))
		.groupby(update.site)
	).as_("first_move")

	move = frappe.qb.DocType("Site Update").as_("move")
	return (
		frappe.qb.from_(first_move)
		.inner_join(move)
		.on((move.site == first_move.site) & (move.creation == first_move.moved_at))
		.select(
			move.site.as_("site"),
			move.source_bench.as_("source_bench"),
			move.group.as_("source_group"),
		)
	).as_("move")
