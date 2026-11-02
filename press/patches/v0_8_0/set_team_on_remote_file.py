import frappe

SITE_FILE_FIELDS = (
	"remote_database_file",
	"remote_public_file",
	"remote_private_file",
	"remote_config_file",
)

BATCH_SIZE = 5000


def execute():
	"""Give older Remote Files a team, so restore can reject the ones without an owner.

	`ensure_team_set` only runs on documents saved after it was added.
	"""
	backfill()

	# Uploaded files carry no site, so take the team of the site they were restored into
	for field in SITE_FILE_FIELDS:
		backfill(field)


def backfill(field: str | None = None):
	"""One batch at a time, so a large table does not hold write locks through the migration."""
	while True:
		files = get_files_without_team(field)
		if not files:
			return

		set_team_on_files(files)


def get_files_without_team(field: str | None):
	"""Take the team from the file's own site, or from the site that uses the file."""
	remote_file = frappe.qb.DocType("Remote File")
	site = frappe.qb.DocType("Site")
	joined_on = site[field] == remote_file.name if field else site.name == remote_file.site

	return (
		frappe.qb.from_(remote_file)
		.join(site)
		.on(joined_on)
		.select(remote_file.name.as_("name"), site.team.as_("team"))
		.where(remote_file.team.isnull())
		.where(site.team.isnotnull())
		.limit(BATCH_SIZE)
		.run(as_dict=True)
	)


def set_team_on_files(files: list[frappe._dict]):
	teams: dict[str, list[str]] = {}
	for file in files:
		teams.setdefault(file.team, []).append(file.name)

	for team, names in teams.items():
		frappe.db.set_value("Remote File", {"name": ("in", names)}, "team", team, update_modified=False)

	frappe.db.commit()
