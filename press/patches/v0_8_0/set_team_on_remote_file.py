import frappe

SITE_FILE_FIELDS = (
	"remote_database_file",
	"remote_public_file",
	"remote_private_file",
	"remote_config_file",
)

BATCH_SIZE = 5000

OWN_SITE_QUERY = """
	SELECT remote_file.name AS name, site.team AS team
	FROM `tabRemote File` remote_file
	JOIN `tabSite` site ON site.name = remote_file.site
	WHERE remote_file.team IS NULL AND site.team IS NOT NULL
	LIMIT %s
"""

SITE_USING_FILE_QUERY = """
	SELECT remote_file.name AS name, site.team AS team
	FROM `tabRemote File` remote_file
	JOIN `tabSite` site ON site.{field} = remote_file.name
	WHERE remote_file.team IS NULL AND site.team IS NOT NULL
	LIMIT %s
"""


def execute():
	"""Give older Remote Files a team, so restore can reject the ones without an owner.

	`ensure_team_set` only runs on documents saved after it was added.
	"""
	backfill(OWN_SITE_QUERY)

	# Uploaded files carry no site, so take the team of the site they were restored into
	for field in SITE_FILE_FIELDS:
		backfill(
			SITE_USING_FILE_QUERY.format(field=field)
		)  # nosemgrep: frappe-manual-commit-and-sql-injection


def backfill(query: str):
	"""One batch at a time, so a large table does not hold write locks through the migration."""
	while True:
		files = frappe.db.sql(query, BATCH_SIZE, as_dict=True)
		if not files:
			return

		set_team_on_files(files)


def set_team_on_files(files: list[frappe._dict]):
	teams: dict[str, list[str]] = {}
	for file in files:
		teams.setdefault(file.team, []).append(file.name)

	for team, names in teams.items():
		frappe.db.set_value("Remote File", {"name": ("in", names)}, "team", team, update_modified=False)

	frappe.db.commit()
