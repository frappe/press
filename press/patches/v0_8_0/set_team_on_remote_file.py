import frappe

SITE_FILE_FIELDS = (
	"remote_database_file",
	"remote_public_file",
	"remote_private_file",
	"remote_config_file",
)


def execute():
	"""Give older Remote Files a team, so restore can reject the ones without an owner.

	`ensure_team_set` only runs on documents saved after it was added.
	"""
	set_team_from_own_site()
	for field in SITE_FILE_FIELDS:
		set_team_from_site_using_file(field)

	frappe.db.commit()


def set_team_from_own_site():
	frappe.db.sql(
		"""
		UPDATE `tabRemote File` remote_file
		JOIN `tabSite` site ON site.name = remote_file.site
		SET remote_file.team = site.team
		WHERE remote_file.team IS NULL AND site.team IS NOT NULL
		"""
	)


def set_team_from_site_using_file(field: str):
	"""Uploaded files carry no site, so take the team of the site they were restored into."""
	frappe.db.sql(
		f"""
		UPDATE `tabRemote File` remote_file
		JOIN `tabSite` site ON site.{field} = remote_file.name
		SET remote_file.team = site.team
		WHERE remote_file.team IS NULL AND site.team IS NOT NULL
		"""  # nosemgrep: frappe-manual-commit-and-sql-injection
	)
