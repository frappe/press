# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, add_to_date, getdate

from press.utils import log_error

if TYPE_CHECKING:
	from datetime import date

# A nightly pass with an hour of overlap, so a run that starts late loses nothing
ROLLUP_WINDOW_HOURS = 25


class SiteBackupSummary(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		days: DF.JSON | None
		month: DF.Data
		site: DF.Link
	# end: auto-generated types


def month_of(day) -> str:
	return str(getdate(day))[:7]


def summary_name(site: str, month: str) -> str:
	return f"{site}::{month}"


def months_between(start: date, end: date) -> list[str]:
	"""Every month the range touches, listed out.

	The month is text, and a between on it is read as numbers: frappe turns the bounds
	into 0.0 and folds the rest of the filter into them, which quietly answers for every
	site at once.
	"""
	months, month = [], getdate(start).replace(day=1)
	last = month_of(end)
	while month_of(month) <= last:
		months.append(month_of(month))
		month = add_months(month, 1)
	return months


def get_summarised_days(site: str, start: date, end: date) -> dict[str, dict]:
	"""What the summaries remember for a range, long after the backups themselves are pruned."""
	months = frappe.get_all(
		"Site Backup Summary",
		{"site": site, "month": ("in", months_between(start, end))},
		pluck="days",
		# The trail is read for a site the caller already has access to
		ignore_permissions=True,
	)

	days = {}
	for month in months:
		for day, entry in (frappe.parse_json(month) or {}).items():
			if str(start) <= day <= str(end):
				days[day] = entry
	return days


def record_days(site: str, entries: dict[str, dict]):
	"""Keep these days for good, whatever happens to the Site Backup rows behind them."""
	by_month: dict[str, dict] = {}
	for day, entry in entries.items():
		by_month.setdefault(month_of(day), {})[day] = entry

	for month, days in by_month.items():
		record_month(site, month, days)


def record_month(site: str, month: str, days: dict[str, dict]):
	summary = frappe.db.get_value(
		"Site Backup Summary", summary_name(site, month), ["name", "days"], as_dict=True
	)
	if not summary:
		frappe.get_doc({"doctype": "Site Backup Summary", "site": site, "month": month, "days": days}).insert(
			ignore_permissions=True
		)
		return

	frappe.db.set_value(
		"Site Backup Summary",
		summary.name,
		"days",
		frappe.as_json((frappe.parse_json(summary.days) or {}) | days),
	)


def update_backup_summaries():
	"""Roll every backup that changed today into its site's summary."""
	frappe.enqueue(_update_backup_summaries, queue="long", timeout=3600)


def _update_backup_summaries():
	"""Keyed on what changed rather than on the day.

	A backup is written once and then touched again days later when retention takes its
	files, and the trail wants to remember both.
	"""
	since = add_to_date(None, hours=-ROLLUP_WINDOW_HOURS)
	for site in changed_sites(since):
		try:
			record_site_backups(site, since)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			# One site's bad row shouldn't cost every other site its day
			log_error("Backup Summary Rollup Failed", site=site)


def backfill_backup_summaries(months: int = 12):
	"""Summarise the backups Press still has, so the trail doesn't start empty.

	Only reaches as far back as the Site Backup rows themselves: days pruned before this
	ran are answered by the bucket, or not at all.
	"""
	since = add_to_date(None, months=-months)
	for site in changed_sites(since):
		try:
			record_site_backups(site, since)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error("Backup Summary Backfill Failed", site=site)


def changed_sites(since) -> list[str]:
	return frappe.get_all("Site Backup", {"modified": (">", since)}, pluck="site", distinct=True)


def record_site_backups(site: str, since):
	"""Re-read every day this site's changed backups touch, and store what Press knows now."""
	from press.press.doctype.site_backup.backup_history import get_recorded_backups

	touched = frappe.get_all(
		"Site Backup", {"site": site, "modified": (">", since)}, pluck="creation", order_by="creation asc"
	)
	if not touched:
		return

	entries = get_recorded_backups(site, getdate(touched[0]), getdate(touched[-1]))
	record_days(site, {day: without_source(entry) for day, entry in entries.items()})


def without_source(entry: dict) -> dict:
	"""The source is where the answer came from, which is the summary once it is stored here."""
	return {key: value for key, value in entry.items() if key != "source"}
