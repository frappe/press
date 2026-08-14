import frappe


def execute():
	"""Summarise the backups Press still holds, so the audit trail doesn't start empty.

	Enqueued rather than run inline: it walks every site with a backup in the last year,
	which is not something a migrate should sit through.
	"""
	frappe.enqueue(
		"press.press.doctype.site_backup_summary.site_backup_summary.backfill_backup_summaries",
		queue="long",
		timeout=24 * 60 * 60,
	)
