# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.api.site import protected
from press.utils import get_current_team


@frappe.whitelist()
@protected("Site")
def version_upgrade(
	name, destination_group, scheduled_datetime=None, skip_failing_patches=False, skip_backups=False
):
	site = frappe.get_doc("Site", name)
	current_version, shared_site, central_site = frappe.db.get_value(
		"Release Group", site.group, ["version", "public", "central_bench"]
	)
	next_version = f"Version {int(current_version.split(' ')[1]) + 1}"

	if shared_site or central_site:
		ReleaseGroup = frappe.qb.DocType("Release Group")
		ReleaseGroupServer = frappe.qb.DocType("Release Group Server")

		destination_group = (
			frappe.qb.from_(ReleaseGroup)
			.select(ReleaseGroup.name)
			.join(ReleaseGroupServer)
			.on(ReleaseGroupServer.parent == ReleaseGroup.name)
			.where(ReleaseGroup.version == next_version)
			.where(ReleaseGroup.public == shared_site)
			.where(ReleaseGroup.central_bench == central_site)
			.where(ReleaseGroup.enabled == 1)
			.where(ReleaseGroupServer.server == site.server)
			.run(as_dict=True, pluck="name")
		)

		if destination_group:
			destination_group = destination_group[0]
		else:
			frappe.throw(
				f"There are no public benches with the version {frappe.bold(next_version)}. Please try with another public bench or reach out to us at<a href='https://support.frappe.io'> support.frappe.io </a>."
			)  # nosemgrep

	version_upgrade = frappe.get_doc(
		{
			"doctype": "Version Upgrade",
			"site": name,
			"destination_group": destination_group,
			"scheduled_time": scheduled_datetime,
			"skip_failing_patches": skip_failing_patches,
			"skip_backups": skip_backups,
		}
	).insert()

	if not scheduled_datetime:
		version_upgrade.start()


@frappe.whitelist()
@protected("Site")
def check_existing_upgrade_bench(name, version):
	"""
	Check if existing next-version benches exist on the same server that includes all the apps installed on the site.

	Returns: {
		"benches":[{
				"bench_name": str,
				"release_group":str,
				"release_group_title": str,
			}]
	}
	"""
	site_server = frappe.db.get_value("Site", name, "server")
	current_team = get_current_team()
	site_apps = set(frappe.db.get_all("Site App", filters={"parent": name}, pluck="app"))
	compatible_benches = []

	version_number = frappe.db.get_value("Frappe Version", version, "number")
	next_version = frappe.db.get_value(
		"Frappe Version",
		{
			"number": version_number + 1,
			"status": ("in", ("Stable", "End of Life")),
			"public": True,
		},
		"name",
	)

	if not next_version:
		return {"benches": compatible_benches}

	# Find private benches on same server with next version
	Bench = frappe.qb.DocType("Bench")
	ReleaseGroup = frappe.qb.DocType("Release Group")

	benches = (
		frappe.qb.from_(Bench)
		.join(ReleaseGroup)
		.on(Bench.group == ReleaseGroup.name)
		.select(Bench.name, Bench.group, ReleaseGroup.title)
		.where(Bench.status == "Active")
		.where(Bench.server == site_server)
		.where(Bench.team == current_team)
		.where(ReleaseGroup.version == next_version)
	).run(as_dict=True)

	if not benches:
		return {"benches": compatible_benches}

	bench_groups = [bench.group for bench in benches]
	all_bench_apps = frappe.db.get_all(
		"Release Group App", filters={"parent": ("in", bench_groups)}, fields=["parent", "app"]
	)
	bench_apps_map = {}
	for row in all_bench_apps:
		if row.parent not in bench_apps_map:
			bench_apps_map[row.parent] = []
		bench_apps_map[row.parent].append(row.app)

	for bench in benches:
		bench_app_list = bench_apps_map.get(bench.group, [])
		if site_apps.issubset(bench_app_list):
			compatible_benches.append(
				{
					"bench_name": bench.name,
					"release_group": bench.group,
					"release_group_title": bench.title,
				}
			)

	return {"benches": compatible_benches}


@frappe.whitelist()
@protected("Site")
def check_app_compatibility_for_upgrade(name, version):
	"""
	Check which apps in the current site are compatible with the next Frappe version.
	Returns list of custom apps installed on the site, if any and other custom apps in the release group for selecting a compatible branch.
	"""
	next_version = get_next_version(version)
	site_group = frappe.db.get_value("Site", name, "group")

	site_app_names = frappe.db.get_all("Site App", filters={"parent": name}, pluck="app")
	release_group_apps = frappe.db.get_all(
		"Release Group App",
		filters={"parent": site_group},
		fields=["app", "source"],
	)

	source_names = list({a.source for a in release_group_apps})
	app_sources = frappe.db.get_all(
		"App Source",
		filters={"name": ("in", source_names)},
		fields=[
			"name",
			"app_title",
			"app",
			"public",
			"enabled",
			"repository",
			"repository_url",
			"repository_owner",
			"github_installation_id",
			"branch",
		],
	)
	source_map = {s.app: s for s in app_sources}
	public_apps = []
	public_source_map = {}
	for app in site_app_names:
		source = source_map.get(app)
		if not source or not source.enabled:
			frappe.throw(f"Could not find a valid source for app {app}.")  # nosemgrep
		# Treat frappe-owned apps as public apps requiring compatibility checks
		if source.public or source.repository_owner == "frappe":
			public_apps.append(app)
			public_source_map[app] = source

	incompatible_apps = _check_public_apps_compatibility(
		public_apps,
		public_source_map,
		next_version,
	)
	if incompatible_apps:
		return {
			"incompatible": incompatible_apps,
			"site_custom_apps": [],
			"other_custom_apps_on_rg": [],
			"can_upgrade": False,
		}

	site_custom_apps = []
	other_custom_apps_on_rg = []  # Custom apps in the release group which aren't installed on the site
	for row in release_group_apps:
		source = source_map.get(row.app)
		if not source or source.public or source.repository_owner == "frappe" or not source.enabled:
			continue

		app_data = {
			"app": row.app,
			"source": source.name,
			"title": source.app_title or row.app,
			"repository": source.repository,
			"repository_url": source.repository_url,
			"repository_owner": source.repository_owner,
			"branch": source.branch,
		}

		if row.app in site_app_names:
			site_custom_apps.append(app_data)
		else:
			other_custom_apps_on_rg.append(app_data)

	return {
		"incompatible": [],
		"site_custom_apps": site_custom_apps,
		"other_custom_apps_on_rg": other_custom_apps_on_rg,
		"can_upgrade": True,
	}


@frappe.whitelist()
@protected("Site")
def create_private_bench_for_site_upgrade(
	name,
	version,
	release_group_title,
	custom_app_sources=None,
	scheduled_time=None,
	skip_failing_patches=False,
	skip_backups=False,
):
	"""
	Deploy private release group and schedule version upgrade.
	"""
	from press.press.doctype.release_group.release_group import new_release_group

	next_version = get_next_version(version)
	site_group, site_server = frappe.db.get_value("Site", name, ["group", "server"])
	team = get_current_team()
	custom_app_sources = custom_app_sources or []
	custom_source_map = {c.get("app"): c for c in custom_app_sources}

	current_rg_apps = frappe.db.get_all(
		"Release Group App",
		filters={"parent": site_group},
		fields=["app", "source"],
	)
	current_site_apps = frappe.db.get_all(
		"Site App",
		filters={"parent": name},
		pluck="app",
	)

	if not current_rg_apps:
		frappe.throw(
			"No apps found in current bench group. Please <a class='underline' href='https://docs.frappe.io/cloud/installing-an-app#bench-group'> add apps </a> to the bench group."
		)

	app_names = [a.app for a in current_rg_apps]
	source_names = [a.source for a in current_rg_apps]

	app_sources = frappe.db.get_all(
		"App Source",
		filters={"name": ("in", source_names)},
		fields=[
			"name",
			"repository_owner",
			"app",
			"public",
			"enabled",
			"repository",
			"repository_url",
			"github_installation_id",
		],
	)

	source_map = {s.name: s for s in app_sources}
	_, compatible_apps_map = get_compatible_public_apps_and_sources(
		app_names,
		next_version,
	)

	apps_for_new_group = _get_apps_for_version_upgrade(
		current_site_apps,
		current_rg_apps,
		source_map,
		compatible_apps_map,
		custom_source_map,
		next_version,
		team,
	)
	apps_payload = [{"app": app, "source": source} for app, source in apps_for_new_group]

	# Validate all site apps are covered before creating bench
	new_bench_app_names = {a["app"] for a in apps_payload}
	missing_site_apps = set(current_site_apps) - new_bench_app_names
	if missing_site_apps:
		frappe.throw(
			f"Cannot upgrade site: the following apps are installed on {name} but no compatible source for {next_version} could be resolved — "
			f"{', '.join(sorted(missing_site_apps))}"
		)  # nosemgrep

	try:
		release_group_doc = new_release_group(
			title=release_group_title,
			version=next_version,
			apps=apps_payload,
			team=team,
			server=site_server,
		)
		version_upgrade = frappe.get_doc(
			{
				"doctype": "Version Upgrade",
				"site": name,
				"deploy_private_bench": 1,
				"destination_group": release_group_doc.name,
				"scheduled_time": scheduled_time,
				"skip_failing_patches": skip_failing_patches,
				"skip_backups": skip_backups,
				"status": "Pending",
			}
		)
		version_upgrade.insert()
		return release_group_doc.name
	except Exception as e:
		frappe.throw(f"Failed to create and deploy bench: {e!s}")  # nosemgrep


def get_next_version(version):
	version_number = frappe.db.get_value("Frappe Version", version, "number")
	if not version_number:
		frappe.throw(f"Invalid Frappe version: {version}")  # nosemgrep

	next_version = frappe.db.get_value(
		"Frappe Version",
		{
			"number": version_number + 1,
			"status": ("in", ("Stable", "End of Life")),
			"public": True,
		},
		"name",
	)
	if not next_version:
		frappe.throw(f"Next version not found for {version}")  # nosemgrep

	return next_version


def _check_public_apps_compatibility(public_apps, source_map, next_version):
	compatible_set, _ = get_compatible_public_apps_and_sources(
		public_apps,
		next_version,
	)
	incompatible = []

	for app in public_apps:
		if app in compatible_set:
			continue

		source = source_map.get(app)
		incompatible.append(source.app_title if source else app)

	return incompatible


def _get_apps_for_version_upgrade(  # noqa: C901
	site_apps,
	release_group_apps,
	source_map,
	compatible_map,
	custom_source_map,
	next_version,
	team,
):
	apps = []
	frappe_app = None

	for row in release_group_apps:
		app_name = row.app
		source = source_map.get(row.source)
		is_site_app = app_name in site_apps

		if not source or not source.enabled:
			if not is_site_app:
				continue
			frappe.throw(f"Invalid source for {app_name}")

		# Public / Frappe app
		if source.public or source.repository_owner == "frappe":
			compatible_source = compatible_map.get(app_name)

			if not compatible_source:
				if not is_site_app:
					continue
				frappe.throw(
					f"No compatible source for app {app_name} for {next_version}. Please reach out to <a href='https://support.frappe.io'>support.frappe.io</a>"
				)

			app_entry = (app_name, compatible_source)

			if app_name == "frappe":
				frappe_app = app_entry
			else:
				apps.append(app_entry)
			continue

		# Custom app
		custom_source = custom_source_map.get(app_name)
		if not custom_source:
			if not is_site_app:
				continue
			frappe.throw(f"Custom app source not provided for {app_name}")

		custom_source_name = _get_custom_app_upgrade_source(
			app_name=app_name,
			app_source=source,
			custom_source=custom_source,
			next_version=next_version,
			team=team,
		)
		apps.append((app_name, custom_source_name))

	return [frappe_app, *apps]


def _get_custom_app_upgrade_source(
	app_name,
	app_source,
	custom_source,
	next_version,
	team,
):
	from press.press.doctype.marketplace_app.marketplace_app import (
		validate_frappe_version_for_branch,
	)

	branch = custom_source.get("branch")
	repository_url = app_source.repository_url
	github_installation_id = app_source.github_installation_id
	if not branch:
		frappe.throw(f"Branch not provided for {app_name}")  # nosemgrep
	if not repository_url:
		frappe.throw(f"Repository URL not provided for {app_name}")  # nosemgrep

	validate_frappe_version_for_branch(
		app_name=app_name,
		owner=app_source.repository_owner,
		repository=app_source.repository,
		branch=branch,
		version=next_version,
		github_installation_id=github_installation_id,
		ease_versioning_constrains=True,
	)

	existing_source = frappe.db.get_value(
		"App Source",
		{
			"app": app_name,
			"repository_url": repository_url.removesuffix(".git"),
			"branch": branch,
			"team": team,
			"enabled": True,
		},
		"name",
	)
	if existing_source:
		source_doc = frappe.get_doc("App Source", existing_source)
		if next_version not in [v.version for v in source_doc.versions]:
			source_doc.add_version(next_version)
		return source_doc.name

	app_doc = frappe.get_cached_doc("App", app_name)
	custom_source = app_doc.add_source(
		repository_url=repository_url,
		branch=branch,
		frappe_version=next_version,
		team=team,
		github_installation_id=github_installation_id,
	)
	return custom_source.name


def get_compatible_public_apps_and_sources(app_names, next_version):
	if not app_names:
		return set(), {}

	AppSource = frappe.qb.DocType("App Source")
	AppSourceVersion = frappe.qb.DocType("App Source Version")
	rows = (
		frappe.qb.from_(AppSourceVersion)
		.join(AppSource)
		.on(AppSourceVersion.parent == AppSource.name)
		.select(
			AppSource.app,
			AppSource.name.as_("source"),
		)
		.where(AppSourceVersion.version == next_version)
		.where(AppSource.app.isin(app_names))
		.where(AppSource.public == 1)
		.where(AppSource.enabled == 1)
	).run(as_dict=True)

	compatible_apps = set()
	compatible_sources = {}
	for r in rows:
		compatible_apps.add(r.app)
		compatible_sources[r.app] = r.source

	return compatible_apps, compatible_sources
