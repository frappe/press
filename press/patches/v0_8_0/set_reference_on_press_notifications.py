# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, now_datetime

from press.press.doctype.press_notification.reference import RELEASE_GROUP_FIELDS

DAYS = 90


def execute():
	"""Set the Site, Release Group or Server on recent notifications, so Press Roles can filter them.

	Older notifications stay without one, and only unrestricted members see them.
	"""
	since = add_days(now_datetime(), -DAYS)
	set_agent_job_references(since)
	for document_type, field in RELEASE_GROUP_FIELDS.items():
		set_release_group_references(document_type, field, since)


def set_agent_job_references(since):
	frappe.db.sql(
		"""
		UPDATE `tabPress Notification` notification
		JOIN `tabAgent Job` job ON job.name = notification.document_name
		LEFT JOIN `tabBench` bench ON bench.name = job.bench
		SET
			notification.reference_doctype = CASE
				WHEN IFNULL(job.site, '') != '' THEN 'Site'
				WHEN IFNULL(bench.`group`, '') != '' THEN 'Release Group'
				ELSE job.server_type
			END,
			notification.reference_name = CASE
				WHEN IFNULL(job.site, '') != '' THEN job.site
				WHEN IFNULL(bench.`group`, '') != '' THEN bench.`group`
				ELSE job.server
			END
		WHERE notification.document_type = 'Agent Job'
			AND IFNULL(notification.reference_doctype, '') = ''
			AND notification.creation > %s
		""",
		since,
	)


def set_release_group_references(document_type: str, field: str, since):
	frappe.db.sql(
		f"""
		UPDATE `tabPress Notification` notification
		JOIN `tab{document_type}` document ON document.name = notification.document_name
		SET
			notification.reference_doctype = 'Release Group',
			notification.reference_name = document.`{field}`
		WHERE notification.document_type = %s
			AND IFNULL(notification.reference_doctype, '') = ''
			AND notification.creation > %s
		""",
		(document_type, since),
	)
