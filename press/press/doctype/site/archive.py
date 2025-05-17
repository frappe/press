# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe

from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site


def archive_suspended_trial_sites():
	ARCHIVE_AFTER_DAYS = 21
	ARCHIVE_AT_ONCE = 10

	filters = [
		["status", "=", "Suspended"],
		["trial_end_date", "is", "set"],
		[
			"trial_end_date",
			"<",
			frappe.utils.add_to_date(None, days=-(ARCHIVE_AFTER_DAYS + 1)),
		],  # Don't look at sites that are unlikely to be archived
	]

	sites = frappe.get_all(
		"Site",
		filters=filters,
		fields=["name", "team", "trial_end_date"],
		order_by="creation asc",
	)

	archived_now = 0
	for site in sites:
		if archived_now > ARCHIVE_AT_ONCE:
			break
		try:
			suspension_date = frappe.get_all(
				"Site Activity",
				filters={"site": site.name, "action": "Suspend Site"},
				pluck="creation",
				order_by="creation desc",
				limit=1,
			)[0]
			suspended_days = frappe.utils.date_diff(frappe.utils.today(), suspension_date)

			if suspended_days > ARCHIVE_AFTER_DAYS:
				site: Site = frappe.get_doc("Site", site.name, for_update=True)
				site.archive(reason="Archive suspended trial site")
				archived_now = archived_now + 1
		except Exception:
			log_error("Suspended Site Archive Error")


def delete_offsite_backups_for_archived_sites():
	archived_sites = frappe.db.sql(
		"""
		SELECT
			backup.site,
			COUNT(*) as offsite_backups
		FROM
			`tabSite Backup` backup
		LEFT JOIN
			`tabSite` site
		ON
			backup.site = site.name
		WHERE
			site.status = "Archived" AND
			backup.files_availability = "Available" AND
			backup.offsite = True
		GROUP BY
			backup.site
		HAVING
			offsite_backups > 1
		ORDER BY
			offsite_backups DESC
	""",
		as_dict=True,
	)
	for site in archived_sites:
		try:
			frappe.get_doc("Site", site.site).delete_offsite_backups()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
