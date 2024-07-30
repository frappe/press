# -*- coding: utf-8 -*-
# imports - standard imports
import atexit
import getpass
import json
import mimetypes
import os
import re
import shlex
import subprocess
import sys
import tempfile

# imports - module imports
import frappe
import frappe.utils.backups
from frappe.utils import update_progress_bar
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
		"mimetypes",
	]
	install_command = shlex.split(
		"{} -m pip install {}".format(sys.executable, " ".join(dependencies))
	)
	subprocess.check_call(install_command, stdout=open(os.devnull, "w"))
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
	key = ""

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
		if not upload_remote.ok:
			# not needed. try the failed parts again!!!
			handle_request_failure(upload_remote)

	else:
		url = payload["url"]
		fields = payload["fields"]
		key = fields["key"]
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
			"path": key,
			"type": ("application/x-gzip" if file_type == "database" else "application/x-tar"),
			"size": os.path.getsize(file_path),
		},
	)

	if register_press.ok:
		return register_press.json()["message"]

	handle_request_failure(register_press)


def render_site_table(sites_info, version_info):
	sites_table = [["#", "Site Name", "Frappe Version"]]
	available_sites = {}

	for n, site_data in enumerate(sites_info):
		name = site_data["name"]
		frappe = version_info[0]
		sites_table.append([n + 1, name, frappe])
		available_sites[name] = {
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


def handle_request_failure(request=None, message=None, traceback=True, exit_code=1):
	message = message or "Request failed with error code {}".format(request.status_code)
	response = html2text.html2text(request.text) if traceback else ""

	print("{0}{1}".format(message, "\n" + response))
	sys.exit(exit_code)


def get_site_info(site):
	site_info_response = session.post(site_info_url, {"name": site})
	if site_info_response.ok:
		return site_info_response.json()["message"]
	return {}


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
		sites_version = [details["latest_frappe_version"] for details in sites_info.values()]
		available_sites = render_site_table(all_sites, sites_version)

		while True:
			selected_site = click.prompt(
				"Name of the site you want to restore to", type=str
			).strip()
			if selected_site in available_sites:
				site_data = available_sites[selected_site]
				global has_external_files
				if not has_external_files:
					downgrade = is_downgrade(sites_info[selected_site])
					if (not downgrade) or (
						downgrade
						and click.confirm(
							"Downgrading may lead to a broken site. Are you sure you want to do this?"
						)
					):
						return site_data
				else:
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
		team = available_teams[0]["name"]
	else:
		render_teams_table(available_teams)
		idx = click.prompt("Select Team", type=click.IntRange(1, len(available_teams))) - 1
		team = available_teams[idx]["name"]

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
def take_backup(local_site):
	print(f"Taking backup for site {local_site}")
	odb = frappe.utils.backups.new_backup(ignore_files=False, force=True)
	return [
		(
			"config",
			getattr(odb, "site_config_backup_path", None)
			or getattr(odb, "backup_path_conf", None),
		),
		("database", odb.backup_path_db),
		("public", odb.backup_path_files),
		("private", odb.backup_path_private_files),
	]


@add_line_after
def upload_files(files):
	files_uploaded = {}
	for file_type, file_path in files:
		file_name = file_path.split(os.sep)[-1]
		uploaded_file = upload_backup_file(file_type, file_name, file_path)
		if uploaded_file:
			files_uploaded[file_type] = uploaded_file
		else:
			print(f"Upload failed for: {file_path}")
			print("Cannot create site on Frappe Cloud without all site backup files uploaded.")
			print("Exiting...")
			sys.exit(1)
	print("Uploaded backup files! ✅")
	return files_uploaded


def external_file_checker(file_path, file_type):
	file_name = os.path.basename(file_path)
	mime_type, _ = mimetypes.guess_type(file_path)
	if file_type == "database":
		if not file_name.endswith((".sql.gz", ".sql")) and not file_name.endswith(
			tuple(f".sql ({i}).gz" for i in range(1, 10))
		):
			raise ValueError(
				'Database backup file should end with the name "database.sql.gz" or "database.sql"'
			)
		if mime_type not in [
			"application/x-gzip",
			"application/x-sql",
			"application/gzip",
			"application/sql",
		]:
			raise ValueError("Invalid database backup file")

	elif file_type in ["public", "private"]:
		if mime_type != "application/x-tar":
			raise ValueError(f"Invalid {file_type} files backup file")

	elif file_type == "config":
		if mime_type != "application/json":
			raise ValueError("Invalid config files backup file")


@add_line_after
def upload_backup(local_site):
	files_uploaded = {}
	if has_external_files:
		print("Trying to upload externally added files to S3")
		files_to_upload = [
			("config", external_config_file_path),
			("database", external_db_path),
			("public", external_public_files_path),
			("private", external_private_files_path),
		]
	else:
		files_to_upload = take_backup(local_site)
	files_uploaded = upload_files(files_to_upload)
	return files_uploaded


@add_line_after
def restore_site(local_site):
	# get list of existing sites they can restore
	selected_site = select_site()["name"]

	# TODO: check if they can restore it

	click.confirm(
		"This is an irreversible action. Are you sure you want to continue?", abort=True
	)

	# backup site
	try:
		files_uploaded = upload_backup(local_site)
	except Exception as e:
		print(f"{e}")
		sys.exit()

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


def frappecloud_migrator(local_site, frappe_provider):
	global login_url, upload_url, remote_link_url, register_remote_url, options_url, site_exists_url, site_info_url, restore_site_url, account_details_url, all_site_url, finish_multipart_url
	global session, remote_site, site_plans_url
	global has_external_files, external_db_path, external_public_files_path, external_private_files_path, external_config_file_path

	remote_site = frappe_provider or frappe.conf.frappecloud_url
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
	site_plans_url = "{}://{}/api/method/press.api.site.get_site_plans".format(
		scheme, remote_site
	)

	# get credentials + auth user + start session
	try:
		session = create_session()
	except RetryError:
		raise KeyboardInterrupt

	restore_site(local_site)


def cleanup(current_file):
	print("Cleaning Up...")
	os.remove(current_file)


def executed_from_temp_dir():
	"""Return True if script executed from temp directory"""
	temp_dir = tempfile.gettempdir()
	cur_file = __file__
	return cur_file.startswith(temp_dir)


@click.command()
def main():
	global has_external_files, external_db_path, external_public_files_path, external_private_files_path, external_config_file_path
	local_site = ""
	if executed_from_temp_dir():
		current_file = os.path.abspath(__file__)
		atexit.register(cleanup, current_file)

	frappe_provider = click.prompt(
		"Frappe provider (default: frappecloud.com)", default="frappecloud.com"
	)

	restore_choice = click.prompt(
		"Do you want to restore from external files? (yes/no)", default="no"
	)
	if restore_choice.lower() in ["yes", "y"]:
		has_external_files = True
		try:
			external_db_path = click.prompt("Enter full path to the external database file")
			external_file_checker(external_db_path, "database")
			external_public_files_path = click.prompt("Enter full path to the public files")
			external_file_checker(external_public_files_path, "public")
			external_private_files_path = click.prompt("Enter full path to the private files")
			external_file_checker(external_private_files_path, "private")
			external_config_file_path = click.prompt("Enter full path to the config file")
			external_file_checker(external_config_file_path, "config")
		except ValueError as e:
			print(f"Error while file validation ': {str(e)}")
			sys.exit()
	else:
		local_site = click.prompt("Name of the site you want to migrate")
		has_external_files = False
		external_db_path = None
		external_public_files_path = None
		external_private_files_path = None
		external_config_file_path = None

	try:
		if not has_external_files:
			frappe.init(site=local_site)
			frappe.connect()
			frappecloud_migrator(local_site, frappe_provider)
		else:
			frappecloud_migrator(local_site=None, frappe_provider=frappe_provider)
	except (KeyboardInterrupt, click.exceptions.Abort):
		print("\nExiting...")
	except Exception:
		from frappe.utils import get_traceback

		print(get_traceback())
	finally:
		frappe.destroy()


if __name__ == "__main__":
	main()
