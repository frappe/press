# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import create_batch

if TYPE_CHECKING:
	from datetime import datetime

# The statuses the auto-update scheduler moves, so the ones adoption is measured on
ACTIVE_SITE_STATUSES = ("Active", "Inactive", "Suspended")
HOURLY_RETENTION_DAYS = 30
REASON_FIELDS = {
	"Fatal Update": "fatal_update",
	"Failed Update": "failed_update",
	"Updating": "updating",
	"Auto Updates Off": "auto_updates_off",
	"Own Update Schedule": "own_schedule",
	"Waiting": "waiting",
}
COUNT_FIELDS = ("current_sites", "behind_sites", "standby_behind", "old_benches", *REASON_FIELDS.values())


class SiteAdoptionSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_updates_off: DF.Int
		behind_sites: DF.Int
		current_sites: DF.Int
		failed_update: DF.Int
		fatal_update: DF.Int
		group_type: DF.Literal["Signup", "Central", "Public", "Private"]
		old_benches: DF.Int
		own_schedule: DF.Int
		release_group: DF.Link | None
		standby_behind: DF.Int
		tier: DF.Literal["Hourly", "Daily"]
		timestamp: DF.Datetime
		updating: DF.Int
		waiting: DF.Int
	# end: auto-generated types

	pass


def record_hourly_snapshot():
	"""Record adoption of each signup, public and central group, one row per group."""
	timestamp = frappe.utils.now_datetime()
	for group, counts in count_sites_by_group(get_shared_groups()).items():
		insert_snapshot(timestamp, "Hourly", counts, release_group=group)
	frappe.db.commit()


def record_daily_snapshot():
	"""Record fleet-wide adoption by group type, and prune hourly rows past retention."""
	timestamp = frappe.utils.now_datetime()
	totals: dict[str, frappe._dict] = {}
	for counts in count_sites_by_group().values():
		total = totals.setdefault(counts.group_type, new_counts(counts.group_type))
		for field in COUNT_FIELDS:
			total[field] += counts[field]

	for total in totals.values():
		insert_snapshot(timestamp, "Daily", total)

	cutoff = frappe.utils.add_days(timestamp, -HOURLY_RETENTION_DAYS)
	frappe.db.delete("Site Adoption Snapshot", {"tier": "Hourly", "timestamp": ("<", cutoff)})
	frappe.db.commit()


def insert_snapshot(timestamp: datetime, tier: str, counts: frappe._dict, release_group: str | None = None):
	frappe.get_doc(
		{
			"doctype": "Site Adoption Snapshot",
			"timestamp": timestamp,
			"tier": tier,
			"group_type": counts.group_type,
			"release_group": release_group,
			**{field: counts[field] for field in COUNT_FIELDS},
		}
	).insert(ignore_permissions=True)


def count_sites_by_group(groups: list[str] | None = None) -> dict[str, frappe._dict]:
	"""Count current and behind sites of each group, with why the behind ones have not moved."""
	benches = get_active_benches(groups)
	newest = {bench.name for bench in newest_by_server(benches).values()}
	sites = get_active_sites(groups)
	blocked = get_blocked_sites([site.name for site in sites if site.bench not in newest])
	counts: dict[str, frappe._dict] = {}
	for site in sites:
		group_counts = counts.setdefault(site.group, new_counts())
		if site.bench in newest:
			group_counts.current_sites += 1
			continue
		group_counts.behind_sites += 1
		group_counts.standby_behind += int(bool(site.is_standby))
		group_counts[REASON_FIELDS[behind_reason(site, blocked)]] += 1

	for bench in benches:
		if bench.name not in newest and bench.group in counts:
			counts[bench.group].old_benches += 1

	group_types = get_group_types(list(counts))
	for group, group_counts in counts.items():
		group_counts.group_type = group_types.get(group, "Private")
	return counts


def new_counts(group_type: str | None = None) -> frappe._dict:
	return frappe._dict({"group_type": group_type, **{field: 0 for field in COUNT_FIELDS}})


def get_newest_benches(groups: list[str] | None = None) -> dict[tuple[str, str], frappe._dict]:
	"""The newest active bench of each group on each server, where an update moves sites to."""
	return newest_by_server(get_active_benches(groups))


def newest_by_server(benches: list[frappe._dict]) -> dict[tuple[str, str], frappe._dict]:
	newest: dict[tuple[str, str], frappe._dict] = {}
	for bench in sorted(benches, key=lambda bench: bench.creation, reverse=True):
		newest.setdefault((bench.group, bench.server), bench)
	return newest


def get_active_benches(groups: list[str] | None = None) -> list[frappe._dict]:
	Bench = frappe.qb.DocType("Bench")
	query = (
		frappe.qb.from_(Bench)
		.select(Bench.name, Bench.group, Bench.server, Bench.creation)
		.where(Bench.status == "Active")
	)
	if groups is not None:
		query = query.where(Bench.group.isin(groups or [""]))
	return query.run(as_dict=True)


def get_active_sites(groups: list[str] | None = None) -> list[frappe._dict]:
	Site = frappe.qb.DocType("Site")
	query = (
		frappe.qb.from_(Site)
		.select(
			Site.name,
			Site.group,
			Site.server,
			Site.bench,
			Site.is_standby,
			Site.skip_auto_updates,
			Site.only_update_at_specified_time,
			Site.fatal_site_update,
		)
		.where(Site.status.isin(ACTIVE_SITE_STATUSES))
	)
	if groups is not None:
		query = query.where(Site.group.isin(groups or [""]))
	return query.run(as_dict=True)


def get_blocked_sites(sites: list[str]) -> dict[str, str]:
	"""Which of the sites the auto-update scheduler skips for an unfinished or a failed update."""
	blocked: dict[str, str] = {}
	# Filtered by site so the lookup uses the site index of the large Site Update table
	for batch in create_batch(sites, 500):
		for update in frappe.get_all(
			"Site Update",
			{"site": ("in", batch), "status": ("in", ("Failure", "Pending", "Running", "Scheduled"))},
			["site", "status"],
		):
			if blocked.get(update.site) != "Failed Update":
				blocked[update.site] = "Failed Update" if update.status == "Failure" else "Updating"
	return blocked


def behind_reason(site: frappe._dict, blocked: dict[str, str]) -> str:
	"""Why a site behind has not moved, in the order the scheduler checks."""
	if site.fatal_site_update:
		return "Fatal Update"
	if site.name in blocked:
		return blocked[site.name]
	if site.skip_auto_updates:
		return "Auto Updates Off"
	if site.only_update_at_specified_time:
		return "Own Update Schedule"
	return "Waiting"


def get_signup_groups() -> set[str]:
	return set(frappe.get_all("Product Trial", {"release_group": ("is", "set")}, pluck="release_group"))


def get_shared_groups() -> list[str]:
	"""Signup, public and central groups, the ones the hourly snapshot covers."""
	shared = frappe.get_all("Release Group", {"public": 1}, pluck="name")
	shared += frappe.get_all("Release Group", {"central_bench": 1}, pluck="name")
	return list(set(shared) | get_signup_groups())


def get_group_types(groups: list[str]) -> dict[str, str]:
	signup_groups = get_signup_groups()
	group_types = {}
	for group in frappe.get_all(
		"Release Group", {"name": ("in", groups or [""])}, ["name", "public", "central_bench"]
	):
		group_types[group.name] = get_group_type(group, signup_groups)
	return group_types


def get_group_type(group: frappe._dict, signup_groups: set[str]) -> str:
	if group.name in signup_groups:
		return "Signup"
	if group.central_bench:
		return "Central"
	if group.public:
		return "Public"
	return "Private"
