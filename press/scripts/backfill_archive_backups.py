# In bench IPython console:  %run press/scripts/backfill_archive_backups.py
# Archive Site takes a final offsite backup, but Press did not record it when the
# proxy job finished last (frappe/press#8096). Prints how many archives lost the
# record, then use backfill() to create their Site Backup and Remote File records.
import frappe
from frappe.utils import add_to_date

from press.press.doctype.site_backup.site_backup import _create_site_backup_from_agent_job


def unrecorded_archive_jobs():
	"""Only 6 months back: an older record makes the retention job delete the files at once."""
	AgentJob = frappe.qb.DocType("Agent Job")
	Site = frappe.qb.DocType("Site")
	SiteBackup = frappe.qb.DocType("Site Backup")
	return (
		frappe.qb.from_(AgentJob)
		.join(Site)
		.on(Site.name == AgentJob.site)
		.left_join(SiteBackup)
		.on(SiteBackup.job == AgentJob.name)
		.select(AgentJob.name)
		.where(AgentJob.job_type == "Archive Site")
		.where(AgentJob.status == "Success")
		.where(AgentJob.creation >= add_to_date(None, months=-6))
		.where(AgentJob.data.like('%"offsite": {%'))
		.where(Site.status == "Archived")
		.where(SiteBackup.name.isnull())
	).run(pluck=True)


def record_archive_backup(job_name):
	job = frappe.get_doc("Agent Job", job_name)
	_create_site_backup_from_agent_job(job)  # logs to Error Log on failure
	backup = frappe.db.get_value("Site Backup", {"job": job_name})
	if backup:  # date the backup when it was taken, not today
		frappe.db.set_value("Site Backup", backup, "creation", job.creation, update_modified=False)
	return bool(backup)


def backfill():
	jobs = unrecorded_archive_jobs()
	created = 0
	for job_name in jobs:
		created += record_archive_backup(job_name)
		frappe.db.commit()
	print(f"created {created}, failed {len(jobs) - created} (see Error Log)")


print(len(unrecorded_archive_jobs()), "archive jobs have an offsite backup but no Site Backup")
