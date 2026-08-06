# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Estimate how long a migration (Site Action) will take for a site.

A migration is roughly "back the site up, move it, restore it". The backup part
depends on the site itself, everything else depends on how big the backup is.
So we estimate them separately:

	estimate = this site's usual backup time + what past migrations of
	similar-sized backups spent on top of their own backup

Medians are used throughout so a single stuck migration doesn't skew the number.
"""

from __future__ import annotations

from statistics import median

import frappe
from frappe.utils import add_to_date

SIMILAR_SIZE_BAND = (0.5, 2.0)
HISTORY_DAYS = 90
MINIMUM_SAMPLES = 5
BACKUPS_CONSIDERED = 10


def estimate_duration(site: str, action_type: str) -> int | None:
	"""Estimated seconds a Site Action of this type will take. None if we can't tell."""
	backup_seconds = usual_backup_duration(site)
	if not backup_seconds:
		return None

	overheads = migration_overheads(action_type, last_backup_size(site))
	if len(overheads) < MINIMUM_SAMPLES:
		# ponytail: backup + restore, until there's enough history to do better
		return round(2 * backup_seconds)

	return round(backup_seconds + median(overheads))


def usual_backup_duration(site: str) -> float | None:
	"""Median duration of the site's recent successful backups, in seconds."""
	durations = frappe.db.sql(
		"""
		SELECT TIME_TO_SEC(job.duration)
		FROM `tabSite Backup` backup
		JOIN `tabAgent Job` job ON job.name = backup.job
		WHERE backup.site = %(site)s AND backup.status = 'Success' AND job.duration IS NOT NULL
		ORDER BY backup.creation DESC
		LIMIT %(limit)s
		""",
		{"site": site, "limit": BACKUPS_CONSIDERED},
		pluck=True,
	)
	return median(durations) if durations else None


def last_backup_size(site: str) -> int | None:
	sizes = frappe.db.sql(
		"""
		SELECT COALESCE(database_size, 0) + COALESCE(public_size, 0) + COALESCE(private_size, 0)
		FROM `tabSite Backup`
		WHERE site = %(site)s AND status = 'Success' AND database_size IS NOT NULL
		ORDER BY creation DESC
		LIMIT 1
		""",
		{"site": site},
		pluck=True,
	)
	return sizes[0] if sizes else None


def migration_overheads(action_type: str, backup_size: int | None) -> list[float]:
	"""Seconds past migrations spent on everything other than the backup itself.

	Only migrations of similarly sized backups count, since the move and the
	restore scale with size. Region isn't filtered on — a migration takes about
	as long wherever it lands, and filtering leaves too few samples.
	"""
	if not backup_size:
		return []

	rows = frappe.db.sql(
		"""
		SELECT
			action.duration AS action_seconds,
			MIN(TIME_TO_SEC(job.duration)) AS backup_seconds
		FROM `tabSite Action` action
		JOIN `tabSite Backup` backup
			ON backup.site = action.site
			AND backup.status = 'Success'
			AND backup.creation BETWEEN action.start AND action.end
			AND COALESCE(backup.database_size, 0)
				+ COALESCE(backup.public_size, 0)
				+ COALESCE(backup.private_size, 0) BETWEEN %(smallest)s AND %(largest)s
		JOIN `tabAgent Job` job ON job.name = backup.job AND job.duration IS NOT NULL
		WHERE
			action.action_type = %(action_type)s
			AND action.status = 'Success'
			AND action.duration > 0
			AND action.start > %(since)s
		GROUP BY action.name
		""",
		{
			"action_type": action_type,
			"smallest": backup_size * SIMILAR_SIZE_BAND[0],
			"largest": backup_size * SIMILAR_SIZE_BAND[1],
			"since": add_to_date(None, days=-HISTORY_DAYS),
		},
		as_dict=True,
	)
	# A migration takes exactly one backup, so MIN just picks it out of the group.
	return [max(row.action_seconds - row.backup_seconds, 0) for row in rows]
