# -*- coding: utf-8 -*-
# imports - standard imports
import atexit
import getpass
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

# imports - module imports
import frappe
import frappe.utils.backups
from frappe.core.utils import find
from frappe.utils import get_installed_apps_info, update_progress_bar
from frappe.utils.backups import BackupGenerator
from frappe.utils.change_log import get_versions
from frappe.utils.commands import add_line_after, add_line_before, render_table

# third party imports

try:
	print("Setting Up requirements...")
	# imports - third party imports
	import click
	import html2text
	import requests
	from requests_toolbelt.multipart import encoder
	from semantic_version import Version
	from tenacity import (
		RetryError,
		retry,
		retry_if_exception_type,
		retry_unless_exception_type,
		stop_after_attempt,
		wait_fixed,
	)
except ImportError:
	dependencies = [
		"tenacity",
		"html2text",
		"requests",
		"click",
		"semantic-version",
		"requests-toolbelt",
	]
	install_command = shlex.split(
		"{} -m pip install {}".format(sys.executable, " ".join(dependencies))
	)
	subprocess.call(install_command, stdout=open(os.devnull, "w"))
	import click
	import html2text
	import requests
	from requests_toolbelt.multipart import encoder
	from semantic_version import Version
	from tenacity import (
		RetryError,
		retry,
		retry_if_exception_type,
		retry_unless_exception_type,
		stop_after_attempt,
		wait_fixed,
	)

if sys.version[0] == "2":
	reload(sys)  # noqa
	sys.setdefaultencoding("utf-8")


@retry(stop=stop_after_attempt(5))
def get_new_site_options():
	site_options_sc = session.post(options_url)

	if site_options_sc.ok:
		site_options = site_options_sc.json()["message"]
		return site_options
	else:
		print("Couldn't retrive New site information: {}".format(site_options_sc.status_code))


@retry(stop=stop_after_attempt(5))
def is_subdomain_available(subdomain):
	res = session.post(site_exists_url, {"subdomain": subdomain})
	if res.ok:
		available = not res.json()["message"]
		if not available:
			print("Subdomain already exists! Try another one")

		return available


@retry(
	stop=stop_after_attempt(2) | retry_if_exception_type(SystemExit), wait=wait_fixed(5)
)
def upload_backup_file(file_type, file_name, file_path):
	def _update_progress_bar(monitor):
		update_progress_bar(
			"Uploading {} file".format(file_type), monitor.bytes_read, monitor.len
		)

	from math import ceil

	K = 1024
	M = K**2

	max_size = (
		100  # in M: Max Size for multipart uploads - break down big files in `n` MB parts
	)
	file_size = os.path.getsize(file_path) / M

	total_size = ceil(file_size / 1024)  # in G
	allowed_max_size = (
		4  # in G: aws allows max 5G but we'll cap single requests at 4 instead
	)

	parts = 1

	if total_size > allowed_max_size:
		parts = ceil(file_size / max_size)

	# retreive upload link
	upload_ticket = session.get(remote_link_url, data={"file": file_name, "parts": parts})

	if not upload_ticket.ok:
		handle_request_failure(upload_ticket)

	payload = upload_ticket.json()["message"]

	if parts > 1:

		def get_file_data(path, part):
			value = part * max_size * M
			with open(path, "rb") as f:
				f.seek(value)
				return f.read(max_size * M)

		upload_id = payload["UploadId"]
		key = payload["Key"]
		signed_urls = payload["signed_urls"]
		file_parts = []

		for count in range(parts):
			signed_url = signed_urls[count]
			file_data = get_file_data(file_path, count)
			update_progress_bar("Uploading {} File".format(file_type), count, parts)

			res = requests.put(signed_url, data=file_data)
			etag = res.headers["ETag"]
			file_parts.append(
				{"ETag": etag, "PartNumber": count + 1}
			)  # you have to append etag and partnumber of each parts

		upload_remote = session.post(
			finish_multipart_url,
			data={
				"file": key,
				"id": upload_id,
				"action": "complete",
				"parts": json.dumps(file_parts),
			},
		)
		print()
		if not upload_remote.ok:
			# not needed. try the failed parts again!!!
			handle_request_failure(upload_remote)

	else:
		url = payload["url"]
		fields = payload["fields"]

		# upload remote file
		fields["file"] = (file_name, open(file_path, "rb"))
		multipart_payload = encoder.MultipartEncoder(fields=fields)
		multipart_payload = encoder.MultipartEncoderMonitor(
			multipart_payload, _update_progress_bar
		)

		upload_remote = session.post(
			url,
			data=multipart_payload,
			headers={
				"Accept": "application/json",
				"Content-Type": multipart_payload.content_type,
			},
		)
		print()
		if not upload_remote.ok:
			handle_request_failure(upload_remote)

	# register remote file to site
	register_press = session.post(
		register_remote_url,
		{
			"file": file_name,
			"path": fields["key"],
			"type": "application/x-gzip" if file_type == "database" else "application/x-tar",
			"size": os.path.getsize(file_path),
		},
	)

	if register_press.ok:
		return register_press.json()["message"]

	handle_request_failure(register_press)


def render_actions_table():
	actions_table = [["#", "Action"]]
	actions = []

	for n, action in enumerate(migrator_actions):
		actions_table.append([n + 1, action["title"]])
		actions.append(action["fn"])

	render_table(actions_table)
	return actions


def render_site_table(sites_info, version_info):
	sites_table = [["#", "Site Name", "Frappe", "Status"]]
	available_sites = {}

	for n, site_data in enumerate(sites_info):
		name, status = site_data["name"], site_data["status"]
		frappe = version_info[name]
		if status in ("Active", "Broken"):
			sites_table.append([n + 1, name, frappe, status])
			available_sites[name] = {
				"status": status,
				"frappe": frappe,
				"name": name,
				"branch": version_info,
			}

	render_table(sites_table)
	return available_sites


def render_teams_table(teams):
	teams_table = [["#", "Team"]]

	for n, team in enumerate(teams):
		teams_table.append([n + 1, team])

	render_table(teams_table)


def render_plan_table(plans_list):
	plans_table = [["Plan", "CPU Time"]]
	visible_headers = ["name", "cpu_time_per_day"]

	for plan in plans_list:
		plan, cpu_time = [plan[header] for header in visible_headers]
		plans_table.append(
			[plan, "{} hour{}/day".format(cpu_time, "" if cpu_time < 2 else "s")]
		)

	render_table(plans_table)


def render_group_table(versions):
	# title row
	versions_table = [["#", "Version", "Bench", "Apps"]]

	# all rows
	idx = 0
	for version in versions:
		for group in version["groups"]:
			apps_list = ", ".join(
				["{}:{}".format(app["app"], app["branch"]) for app in group["apps"]]
			)
			row = [idx + 1, version["name"], group["name"], apps_list]
			versions_table.append(row)
			idx += 1

	render_table(versions_table)
	return versions_table


def handle_request_failure(request=None, message=None, traceback=True, exit_code=1):
	message = message or "Request failed with error code {}".format(request.status_code)
	response = html2text.html2text(request.text) if traceback else ""

	print("{0}{1}".format(message, "\n" + response))
	sys.exit(exit_code)


@add_line_after
def select_primary_action():
	actions = render_actions_table()
	idx = click.prompt("What do you want to do?", type=click.IntRange(1, len(actions))) - 1

	return actions[idx]


def get_site_info(site):
	site_info_response = session.post(site_info_url, {"name": site})
	if site_info_response.ok:
		return site_info_response.json()["message"]
	return {}


def get_version(info, app="frappe"):
	for app in info.get("installed_apps", {}):
		if app.get("frappe", 0) == 1:
			return app.get("name").lower().strip("frappe").strip().title()


def get_branch(info, app="frappe"):
	for app in info.get("installed_apps", {}):
		if app.get("frappe", 0) == 1:
			return app.get("branch")


def get_version_from_branch(branch):
	try:
		return int(re.findall(r"[0-9]+", branch)[0])
	except Exception:
		return


def is_downgrade(cloud_data):
	current = get_versions().get("frappe")
	current_version = Version(current["version"]).major

	cloud_branch = get_branch(cloud_data)
	cloud_version = get_version_from_branch(cloud_branch) or 1000

	return current_version > cloud_version


def raise_limits_warning():
	raise_warn = False
	files = BackupGenerator(
		frappe.conf.db_name, frappe.conf.db_name, frappe.conf.db_password
	).get_recent_backup(older_than=24 * 30)

	for file in files:
		if file:
			file_size_in_mb = os.path.getsize(file) / (1024 * 1024)
			if "database" in file and file_size_in_mb > 500:
				raise_warn = True
	return raise_warn


@add_line_after
def select_site():
	get_all_sites_request = session.post(
		all_site_url,
		headers={
			"accept": "application/json",
			"accept-encoding": "gzip, deflate, br",
			"content-type": "application/json; charset=utf-8",
		},
	)

	if get_all_sites_request.ok:
		# the following lines have data with a lot of redundancy, but there's no real reason to bother cleaning them up
		all_sites = get_all_sites_request.json()["message"]
		sites_info = {site["name"]: get_site_info(site["name"]) for site in all_sites}
		sites_version = {x: get_version(y) for x, y in sites_info.items()}
		available_sites = render_site_table(all_sites, sites_version)

		while True:
			selected_site = click.prompt(
				"Name of the site you want to restore to", type=str
			).strip()
			if selected_site in available_sites:
				site_data = available_sites[selected_site]
				downgrade = is_downgrade(sites_info[selected_site])

				if (not downgrade) or (
					downgrade
					and click.confirm(
						"Downgrading may lead to a broken site. Are you sure you want to do this?"
					)
				):
					return site_data

			else:
				print("Site {} does not exist. Try again ❌".format(selected_site))
	else:
		print("Couldn't retrive sites list...Try again later")
		sys.exit(1)


@add_line_before
def select_team(session):
	# get team options
	account_details_sc = session.post(account_details_url)
	if account_details_sc.ok:
		account_details = account_details_sc.json()["message"]
		available_teams = account_details["teams"]

	# ask if they want to select, go ahead with if only one exists
	if len(available_teams) == 1:
		team = available_teams[0]
	else:
		render_teams_table(available_teams)
		idx = click.prompt("Select Team", type=click.IntRange(1, len(available_teams))) - 1
		team = available_teams[idx]

	print("Team '{}' set for current session".format(team))

	return team


def is_valid_subdomain(subdomain):
	if len(subdomain) < 5:
		print("Subdomain too short. Use 5 or more characters")
		return False
	matched = re.match("^[a-z0-9][a-z0-9-]*[a-z0-9]$", subdomain)
	if matched:
		return True
	print(
		"Subdomain contains invalid characters. Use lowercase characters, numbers and hyphens"
	)


@add_line_after
def choose_plan(plans_list):
	print("{} plans available".format(len(plans_list)))
	available_plans = [plan["name"] for plan in plans_list]
	render_plan_table(plans_list)

	while True:
		input_plan = click.prompt("Select Plan").strip()
		if input_plan in available_plans:
			print("{} Plan selected ✅".format(input_plan))
			return input_plan
		else:
			print("Invalid Selection ❌")


@add_line_after
def check_app_compat(available_group):
	is_compat = True
	incompatible_apps, filtered_apps, branch_msgs = [], [], []
	existing_group = [
		(app["app_name"], app["branch"]) for app in get_installed_apps_info()
	]
	print("Checking availability of existing app group")

	for (app, branch) in existing_group:
		info = [(a["app"], a["branch"]) for a in available_group["apps"] if a["app"] == app]
		if info:
			app_title, available_branch = info[0]

			if branch != available_branch:
				print("⚠️  App {}:{} => {}".format(app, branch, available_branch))
				branch_msgs.append([app, branch, available_branch])
				filtered_apps.append(app_title)
				is_compat = False

			else:
				print("✅ App {}:{}".format(app, branch))
				filtered_apps.append(app_title)

		else:
			incompatible_apps.append(app)
			print("❌ App {}:{}".format(app, branch))
			is_compat = False

	start_msg = "\nSelecting this group will "
	incompatible_apps = (
		("\n\nDrop the following apps:\n" + "\n".join(incompatible_apps))
		if incompatible_apps
		else ""
	)
	branch_change = (
		(
			"\n\nUpgrade the following apps:\n"
			+ "\n".join(["{}: {} => {}".format(*x) for x in branch_msgs])
		)
		if branch_msgs
		else ""
	)
	changes = (incompatible_apps + branch_change) or "be perfect for you :)"
	warning_message = start_msg + changes
	print(warning_message)

	return is_compat, filtered_apps


@add_line_after
def filter_apps(versions):
	rendered_group_table = render_group_table(versions)
	while True:
		version_index = click.prompt("Select Version Number", type=int) - 1
		try:
			if version_index < 0:
				raise IndexError
			version, group = (
				rendered_group_table[version_index][1],
				rendered_group_table[version_index][2],
			)
			selected_group = find(
				versions[version_index]["groups"], lambda g: g["name"] == group
			)
		except IndexError:
			print("Invalid Selection ❌")
			continue

		is_compat, filtered_apps = check_app_compat(selected_group)

		if is_compat or click.confirm("Continue anyway?"):
			print("App Group {} selected! ✅".format(selected_group["name"]))
			break

	return selected_group["name"], filtered_apps


@add_line_after
def get_subdomain(domain):
	while True:
		subdomain = click.prompt("Enter subdomain").strip()
		if is_valid_subdomain(subdomain) and is_subdomain_available(subdomain):
			print("Site Domain: {}.{}".format(subdomain, domain))
			return subdomain


@add_line_after
def upload_backup(local_site):
	# take backup
	files_uploaded = {}
	print("Taking backup for site {}".format(local_site))
	odb = frappe.utils.backups.new_backup(ignore_files=False, force=True)

	# upload files
	for x, (file_type, file_path) in enumerate(
		[
			(
				"config",
				getattr(odb, "site_config_backup_path", None)
				or getattr(odb, "backup_path_conf", None),
			),
			("database", odb.backup_path_db),
			("public", odb.backup_path_files),
			("private", odb.backup_path_private_files),
		]
	):
		file_name = file_path.split(os.sep)[-1]

		uploaded_file = upload_backup_file(file_type, file_name, file_path)

		if uploaded_file:
			files_uploaded[file_type] = uploaded_file
		else:
			print("Upload failed for: {}".format(file_path))
			print("Cannot create site on Frappe Cloud without all site backup files uploaded.")
			print("Exitting...")
			sys.exit(1)

	print("Uploaded backup files! ✅")

	return files_uploaded


def new_site(local_site):
	# get new site options
	site_options = get_new_site_options()

	# set preferences from site options
	subdomain = get_subdomain(site_options["domain"])
	plan = choose_plan(site_options["plans"])

	versions = site_options["versions"]
	selected_group, filtered_apps = filter_apps(versions)
	files_uploaded = upload_backup(local_site)

	# push to frappe_cloud
	payload = json.dumps(
		{
			"site": {
				"apps": filtered_apps,
				"files": files_uploaded,
				"group": selected_group,
				"name": subdomain,
				"plan": plan,
			}
		}
	)

	session.headers.update({"Content-Type": "application/json; charset=utf-8"})
	site_creation_request = session.post(upload_url, payload)

	if site_creation_request.ok:
		site_url = site_creation_request.json()["message"]
		print("Your site {} is being migrated ✨".format(local_site))
		print(
			"View your site dashboard at https://{}/dashboard/sites/{}".format(
				remote_site, site_url
			)
		)
		print("Your site URL: https://{}".format(site_url))
	else:
		handle_request_failure(site_creation_request)


def restore_site(local_site):
	# get list of existing sites they can restore
	selected_site = select_site()["name"]

	# TODO: check if they can restore it

	click.confirm(
		"This is an irreversible action. Are you sure you want to continue?", abort=True
	)

	# backup site
	files_uploaded = upload_backup(local_site)

	# push to frappe_cloud
	payload = json.dumps({"name": selected_site, "files": files_uploaded})
	headers = {"Content-Type": "application/json; charset=utf-8"}
	site_restore_request = session.post(restore_site_url, payload, headers=headers)

	if site_restore_request.ok:
		print("Your site {0} is being restored on {1} ✨".format(local_site, selected_site))
		print(
			"View your site dashboard at https://{}/dashboard/sites/{}".format(
				remote_site, selected_site
			)
		)
		print("Your site URL: https://{}".format(selected_site))
	else:
		handle_request_failure(site_restore_request)


@add_line_after
@retry(
	stop=stop_after_attempt(3)
	| retry_if_exception_type(SystemExit) & retry_unless_exception_type(KeyboardInterrupt)
)
def create_session():
	print("\nFrappe Cloud credentials @ {}".format(remote_site))

	# take user input from STDIN
	username = click.prompt("Username").strip()
	password = getpass.unix_getpass()

	auth_credentials = {"usr": username, "pwd": password}

	session = requests.Session()
	login_sc = session.post(login_url, auth_credentials)

	if login_sc.ok:
		print("Authorization Successful! ✅")
		team = select_team(session)
		session.headers.update({"X-Press-Team": team, "Connection": "keep-alive"})
		return session
	else:
		handle_request_failure(
			message="Authorization Failed with Error Code {}".format(login_sc.status_code),
			traceback=False,
		)


def frappecloud_migrator(local_site):
	global login_url, upload_url, remote_link_url, register_remote_url, options_url, site_exists_url, site_info_url, restore_site_url, account_details_url, all_site_url, finish_multipart_url
	global session, migrator_actions, remote_site

	remote_site = frappe.conf.frappecloud_url or "frappecloud.com"
	scheme = "https"

	login_url = "{}://{}/api/method/login".format(scheme, remote_site)
	upload_url = "{}://{}/api/method/press.api.site.new".format(scheme, remote_site)
	remote_link_url = "{}://{}/api/method/press.api.site.get_upload_link".format(
		scheme, remote_site
	)
	register_remote_url = "{}://{}/api/method/press.api.site.uploaded_backup_info".format(
		scheme, remote_site
	)
	options_url = "{}://{}/api/method/press.api.site.options_for_new".format(
		scheme, remote_site
	)
	site_exists_url = "{}://{}/api/method/press.api.site.exists".format(
		scheme, remote_site
	)
	site_info_url = "{}://{}/api/method/press.api.site.get".format(scheme, remote_site)
	account_details_url = "{}://{}/api/method/press.api.account.get".format(
		scheme, remote_site
	)
	all_site_url = "{}://{}/api/method/press.api.site.all".format(scheme, remote_site)
	restore_site_url = "{}://{}/api/method/press.api.site.restore".format(
		scheme, remote_site
	)
	finish_multipart_url = "{}://{}/api/method/press.api.site.multipart_exit".format(
		scheme, remote_site
	)

	migrator_actions = [
		{"title": "Create a new site", "fn": new_site},
		{"title": "Restore to an existing site", "fn": restore_site},
	]

	if raise_limits_warning():
		notice = (
			"\n"
			"Note:\n"
			"* For migrating sites with compressed database backup larger than 500MiB, "
			"please schedule a migration with us from {}"
		).format("https://frappecloud.com/migration-request")
		click.secho(notice, fg="yellow")
		sys.exit(1)

	# get credentials + auth user + start session
	try:
		session = create_session()
	except RetryError:
		raise KeyboardInterrupt

	# available actions defined in migrator_actions
	primary_action = select_primary_action()

	primary_action(local_site)


def cleanup(current_file):
	print("Cleaning Up...")
	os.remove(current_file)


def executed_from_temp_dir():
	"""Return True if script executed from temp directory"""
	temp_dir = tempfile.gettempdir()
	cur_file = __file__
	return cur_file.startswith(temp_dir)


if __name__ in ("__main__", "frappe.integrations.frappe_providers.frappecloud"):
	if executed_from_temp_dir():
		current_file = os.path.abspath(__file__)
		atexit.register(cleanup, current_file)

	try:
		local_site = sys.argv[1]
	except Exception:
		local_site = input("Name of the site you want to migrate: ").strip()

	try:
		frappe.init(site=local_site)
		frappe.connect()
		frappecloud_migrator(local_site)
	except (KeyboardInterrupt, click.exceptions.Abort):
		print("\nExitting...")
	except Exception:
		from frappe.utils import get_traceback

		print(get_traceback())

	frappe.destroy()
