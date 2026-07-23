import frappe


def execute():
	"""Reset Remote File team to the site's team.

	Remote Files for backups are created in agent job callbacks running as
	Administrator, so `ensure_team_set` stamped Administrator's team on them,
	which blocked restores with "Remote File {0} does not belong to site's team".
	"""
	frappe.db.sql("""
		UPDATE `tabRemote File` remote_file
		INNER JOIN `tabSite` site ON site.name = remote_file.site
		SET remote_file.team = site.team
		WHERE remote_file.team != site.team
	""")
