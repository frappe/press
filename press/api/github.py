# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import re
import jwt
import frappe
import requests

from pathlib import Path
from base64 import b64decode
from datetime import datetime, timedelta
from press.utils import get_current_team, log_error
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Optional


@frappe.whitelist(allow_guest=True, xss_safe=True)
def hook(*args, **kwargs):
	try:
		user = frappe.session.user
		# set user to Administrator, to not have to do ignore_permissions everywhere
		frappe.set_user("Administrator")

		headers = frappe.request.headers
		doc = frappe.get_doc(
			{
				"doctype": "GitHub Webhook Log",
				"name": headers.get("X-Github-Delivery"),
				"event": headers.get("X-Github-Event"),
				"signature": headers.get("X-Hub-Signature").split("=")[1],
				"payload": frappe.request.get_data().decode(),
			}
		)
		doc.insert()
	except Exception:
		frappe.set_user(user)
		log_error("GitHub Webhook Error", args=args, kwargs=kwargs)
		raise Exception


def get_jwt_token():
	key = frappe.db.get_single_value("Press Settings", "github_app_private_key")
	app_id = frappe.db.get_single_value("Press Settings", "github_app_id")
	now = datetime.now()
	expiry = now + timedelta(minutes=9)
	payload = {"iat": int(now.timestamp()), "exp": int(expiry.timestamp()), "iss": app_id}
	token = jwt.encode(payload, key.encode(), algorithm="RS256")
	return token


def get_access_token(installation_id: "Optional[str]" = None):
	if not installation_id:
		return frappe.db.get_value(
			"Press Settings",
			None,
			"github_access_token",
		)

	token = get_jwt_token()
	headers = {
		"Authorization": f"Bearer {token}",
		"Accept": "application/vnd.github.machine-man-preview+json",
	}
	response = requests.post(
		f"https://api.github.com/app/installations/{installation_id}/access_tokens",
		headers=headers,
	).json()
	return response.get("token")


@frappe.whitelist()
def clear_token_and_get_installation_url():
	clear_current_team_access_token()
	public_link = frappe.db.get_single_value("Press Settings", "github_app_public_link")
	return f"{public_link}/installations/new"


def clear_current_team_access_token():
	team = get_current_team()
	frappe.db.set_value("Team", team, "github_access_token", "")  # clear access token


@frappe.whitelist()
def options():
	team = get_current_team()
	token = frappe.db.get_value("Team", team, "github_access_token")
	public_link = frappe.db.get_single_value("Press Settings", "github_app_public_link")

	versions = frappe.get_all("Frappe Version", filters={"public": True})

	options = {
		"authorized": bool(token),
		"installation_url": f"{public_link}/installations/new",
		"installations": installations(token) if token else [],
		"versions": versions,
	}
	return options


def installations(token):
	headers = {
		"Authorization": f"token {token}",
		"Accept": "application/vnd.github.machine-man-preview+json",
	}
	response = requests.get("https://api.github.com/user/installations", headers=headers)
	data = response.json()
	installations = []
	if response.ok:
		for installation in data["installations"]:
			installations.append(
				{
					"id": installation["id"],
					"login": installation["account"]["login"],
					"url": installation["html_url"],
					"image": installation["account"]["avatar_url"],
					"repos": repositories(installation["id"], token),
				}
			)
	else:
		frappe.throw(data.get("message") or "An error occured")

	return installations


def repositories(installation, token):
	headers = {
		"Authorization": f"token {token}",
		"Accept": "application/vnd.github.machine-man-preview+json",
	}
	repositories = []
	current_page, is_last_page = 1, False
	while not is_last_page:
		response = requests.get(
			f"https://api.github.com/user/installations/{installation}/repositories",
			params={"per_page": 100, "page": current_page},
			headers=headers,
		)
		if len(response.json().get("repositories", [])) < 100:
			is_last_page = True

		for repository in response.json().get("repositories", []):
			repositories.append(
				{
					"id": repository["id"],
					"name": repository["name"],
					"private": repository["private"],
					"url": repository["html_url"],
					"default_branch": repository["default_branch"],
				}
			)
		current_page += 1

	return repositories


@frappe.whitelist()
def repository(owner, name, installation=None):
	token = ""
	if not installation:
		token = frappe.db.get_value("Press Settings", "github_access_token")
	else:
		token = get_access_token(installation)
	headers = {
		"Authorization": f"token {token}",
	}
	repo = requests.get(
		f"https://api.github.com/repos/{owner}/{name}", headers=headers
	).json()

	current_page, is_last_page = 1, False
	branches = []
	while not is_last_page:
		response = requests.get(
			f"https://api.github.com/repos/{owner}/{name}/branches",
			params={"per_page": 100, "page": current_page},
			headers=headers,
		)
		if response.ok:
			branches.extend(response.json())
		else:
			break

		if len(response.json()) < 100:
			is_last_page = True

		current_page += 1

	repo["branches"] = branches

	return repo


@frappe.whitelist()
def app(owner, repository, branch, installation=None):
	headers = get_auth_headers(installation)
	branch_info = requests.get(
		f"https://api.github.com/repos/{owner}/{repository}/branches/{branch}",
		headers=headers,
	).json()
	sha = branch_info["commit"]["commit"]["tree"]["sha"]
	contents = requests.get(
		f"https://api.github.com/repos/{owner}/{repository}/git/trees/{sha}",
		params={"recursive": True},
		headers=headers,
	).json()

	tree = _generate_files_tree(contents["tree"])
	py_setup_files = ["setup.py", "setup.cfg", "pyproject.toml"]

	if not any(x in tree for x in py_setup_files):
		setup_filenames = frappe.bold(" or ".join(py_setup_files))
		reason = f"Files {setup_filenames} do not exist in app directory."
		frappe.throw(f"Not a valid Frappe App! {reason}")

	app_name, title = _get_app_name_and_title_from_hooks(
		owner,
		repository,
		branch_info,
		headers,
		tree,
	)

	return {"name": app_name, "title": title}


@frappe.whitelist()
def branches(owner, name, installation=None):
	if installation:
		token = get_access_token(installation)
	else:
		token = frappe.get_value("Press Settings", None, "github_access_token")

	if token:
		headers = {
			"Authorization": f"token {token}",
		}
	else:
		headers = {}

	response = requests.get(
		f"https://api.github.com/repos/{owner}/{name}/branches",
		params={"per_page": 100},
		headers=headers,
	)

	if response.ok:
		return response.json()
	else:
		frappe.throw("Error fetching branch list from GitHub")


def get_auth_headers(installation_id: "Optional[str]" = None) -> "dict[str, str]":
	if token := get_access_token(installation_id):
		return {"Authorization": f"token {token}"}
	return {}


def _get_app_name_and_title_from_hooks(
	owner,
	repository,
	branch_info,
	headers,
	tree,
) -> "tuple[str, str]":
	reason_for_invalidation = ""
	for directory, files in tree.items():
		if files and ("hooks.py" not in files or "patches.txt" not in files):
			reason_for_invalidation = (
				f"Files {frappe.bold('hooks.py or patches.txt')} does not exist"
				f" inside {directory}/{directory} directory."
			)
			continue

		app_name = directory
		hooks = requests.get(
			f"https://api.github.com/repos/{owner}/{repository}/contents/{app_name}/hooks.py",
			params={"ref": branch_info["name"]},
			headers=headers,
		).json()
		content = b64decode(hooks["content"]).decode()
		match = re.search(r"""app_title = ["'](.*)["']""", content)

		if match:
			return app_name, match.group(1)

		reason_for_invalidation = (
			f"File {frappe.bold('hooks.py')} does not have {frappe.bold('app_title')} defined."
		)
		break

	frappe.throw(f"Not a valid Frappe App! {reason_for_invalidation}")


def _generate_files_tree(files):
	children = {}
	for file in files:
		path = Path(file["path"])
		children.setdefault(str(path.parent), []).append(
			frappe._dict({"name": str(path.name), "path": file["path"]})
		)
	return _construct_tree({}, children["."], children)


def _construct_tree(tree, children, children_map):
	for file in children:
		if file.path in children_map:
			tree[file.name] = _construct_tree({}, children_map[file.path], children_map)
		else:
			tree[file.name] = None
	return tree
