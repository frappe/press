import frappe

BATCH_SIZE = 1000


def execute():
	"""Reset Remote File team to the site's team.

	Remote Files for backups are created in agent job callbacks running as
	Administrator, so `ensure_team_set` stamped Administrator's team on them,
	which blocked restores with "Remote File {0} does not belong to site's team".

	`tabRemote File` is large, so this runs in the background instead of holding
	a write lock for the length of migrate.
	"""
	frappe.enqueue(
		"press.patches.v0_8_0.fix_remote_file_team_from_site.fix_teams",
		queue="long",
		timeout=24 * 60 * 60,
		job_id="fix_remote_file_team_from_site",
		deduplicate=True,
	)


def fix_teams():
	# ponytail: rescans from the top each batch; fine because fixed rows stop
	# matching. Paginate by name if the tail ever gets slow.
	while True:
		remote_files = frappe.db.sql(
			"""
			SELECT remote_file.name, site.team
			FROM `tabRemote File` remote_file
			INNER JOIN `tabSite` site ON site.name = remote_file.site
			WHERE remote_file.team != site.team
			LIMIT %s
			""",
			BATCH_SIZE,
			as_dict=True,
		)
		if not remote_files:
			break

		for remote_file in remote_files:
			frappe.db.set_value(
				"Remote File", remote_file.name, "team", remote_file.team, update_modified=False
			)
		frappe.db.commit()
