import frappe

BATCH_SIZE = 1000


def execute():
	"""Reset Remote File team to the site's team.

	Remote Files for backups are created in agent job callbacks running as
	Administrator, so `ensure_team_set` stamped Administrator's team on them,
	which blocked restores with "Remote File {0} does not belong to site's team".

	`tabRemote File` is large, so this walks it in batches by name instead of
	holding a write lock for the length of one big UPDATE.
	"""
	last_name = ""
	while True:
		remote_files = frappe.db.sql(
			"""
			SELECT remote_file.name, site.team
			FROM `tabRemote File` remote_file
			INNER JOIN `tabSite` site ON site.name = remote_file.site
			WHERE remote_file.name > %s AND remote_file.team != site.team
			ORDER BY remote_file.name
			LIMIT %s
			""",
			(last_name, BATCH_SIZE),
			as_dict=True,
		)
		if not remote_files:
			break

		for remote_file in remote_files:
			frappe.db.set_value(
				"Remote File", remote_file.name, "team", remote_file.team, update_modified=False
			)
		frappe.db.commit()
		last_name = remote_files[-1].name
