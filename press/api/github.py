# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from base64 import b64decode
from datetime import datetime, timedelta
from pathlib import Path
import contextlib
from typing import TYPE_CHECKING

import frappe
import jwt
import requests
import tomli

from press.utils import get_current_team, log_error

if TYPE_CHECKING:
	from press.press.doctype.github_webhook_log.github_webhook_log import GitHubWebhookLog


@frappe.whitelist(allow_guest=True, xss_safe=True)
def hook(*args, **kwargs):
	user = frappe.session.user
	# set user to Administrator, to not have to do ignore_permissions everywhere
	frappe.set_user("Administrator")
	headers = frappe.request.headers
	doc: "GitHubWebhookLog" = frappe.get_doc(
		{
			"doctype": "GitHub Webhook Log",
			"name": headers.get("X-Github-Delivery"),
			"event": headers.get("X-Github-Event"),
			"signature": headers.get("X-Hub-Signature").split("=")[1],
			"payload": frappe.request.get_data().decode(),
		}
	)

	try:
		doc.insert()
		frappe.db.commit()
	except Exception as e:
		frappe.set_user(user)
		log_error("GitHub Webhook Insert Error", args=args, kwargs=kwargs)
		raise Exception from e

	try:
		doc.handle_events()
	except Exception as e:
		frappe.set_user(user)
		log_error("GitHub Webhook Error", doc=doc)
		raise Exception from e


def get_jwt_token():
	key = frappe.db.get_single_value("Press Settings", "github_app_private_key")
	app_id = frappe.db.get_single_value("Press Settings", "github_app_id")
	now = datetime.now()
	expiry = now + timedelta(minutes=9)
	payload = {"iat": int(now.timestamp()), "exp": int(expiry.timestamp()), "iss": app_id}
	return jwt.encode(payload, key.encode(), algorithm="RS256")


def get_access_token(installation_id: str | None = None):
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

	return {
		"authorized": bool(token),
		"installation_url": f"{public_link}/installations/new",
		"installations": installations(token) if token else [],
	}


def fetch_installations(token):
	headers = {
		"Authorization": f"token {token}",
		"Accept": "application/vnd.github.machine-man-preview+json",
	}
	installations = []
	current_page, is_last_page = 1, False
	while not is_last_page:
		response = requests.get(
			"https://api.github.com/user/installations",
			params={"per_page": 100, "page": current_page},
			headers=headers,
		)
		if len(response.json().get("installations", [])) < 100:
			is_last_page = True
		installations.extend(response.json().get("installations", []))
		current_page += 1
	return installations


def installations(token):
	installations = []
	for installation in fetch_installations(token):
		installations.append(
			{
				"id": installation["id"],
				"login": installation["account"]["login"],
				"url": installation["html_url"],
				"image": installation["account"]["avatar_url"],
				"repos": repositories(installation["id"], token),
			}
		)

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
	repo = requests.get(f"https://api.github.com/repos/{owner}/{name}", headers=headers).json()

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
	response = requests.get(
		f"https://api.github.com/repos/{owner}/{repository}/branches/{branch}",
		headers=headers,
	)

	if not response.ok:
		frappe.throw(f"Could not fetch branch ({branch}) info for repo {owner}/{repository}")

	branch_info = response.json()
	sha = branch_info["commit"]["commit"]["tree"]["sha"]
	contents = requests.get(
		f"https://api.github.com/repos/{owner}/{repository}/git/trees/{sha}",
		params={"recursive": True},
		headers=headers,
	).json()

	tree = _generate_files_tree(contents["tree"])

	# Force pyproject.toml as a setup file
	if "pyproject.toml" not in tree:
		reason = "pyproject.toml does not exist in app directory."
		frappe.throw(f"Not a valid Frappe App! {reason}")

	app_name, title = _get_app_name_and_title_from_hooks(
		owner,
		repository,
		branch_info,
		headers,
		tree,
	)

	frappe_version = _get_compatible_frappe_version_from_pyproject(
		owner,
		repository,
		branch_info,
		headers,
	)

	return {"name": app_name, "title": title, "frappe_version": frappe_version}


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
	frappe.throw("Error fetching branch list from GitHub: " + response.text)
	return None


def get_auth_headers(installation_id: str | None = None) -> "dict[str, str]":
	if token := get_access_token(installation_id):
		return {"Authorization": f"token {token}"}
	return {}


def _get_compatible_frappe_version_from_pyproject(
	owner: str, repository: str, branch_info: str, headers: dict[str, str]
) -> str:
	"""Get frappe version from pyproject.toml file."""
	compatible_frappe_version = None
	pyproject = requests.get(
		f"https://api.github.com/repos/{owner}/{repository}/contents/pyproject.toml",
		params={"ref": branch_info["name"]},
		headers=headers,
	).json()

	if "content" not in pyproject:
		frappe.throw("Could not fetch pyproject.toml file.")

	pyproject = b64decode(pyproject["content"]).decode()

	try:
		pyproject = tomli.loads(pyproject)
	except tomli.TOMLDecodeError as e:
		out = []
		out.append("Invalid pyproject.toml file found")
		lines = e.doc.splitlines()
		start = max(e.lineno - 3, 0)
		end = e.lineno + 2

		for i, line in enumerate(lines[start:end], start=start + 1):
			out.append(f"{i:>4}: {line}")

		out = "\n".join(out)
		frappe.throw(out)

	with contextlib.suppress(Exception):
		compatible_frappe_version = (
			pyproject.get("tool", {})
			.get("bench", {})
			.get("frappe-dependencies", {})
			.get(
				"frappe",
			)
		)

	if not compatible_frappe_version:
		frappe.throw(
			"Could not find compatible Frappe version in pyproject.toml file. "
			"Please ensure '[tool.bench.frappe-dependencies]"
		)

	return compatible_frappe_version


def _get_app_name_and_title_from_hooks(
	owner,
	repository,
	branch_info,
	headers,
	tree,
) -> tuple[str, str] | None:
	reason_for_invalidation = f"Files {frappe.bold('hooks.py or patches.txt')} not found."
	for directory, files in tree.items():
		if not files:
			continue

		if ("hooks.py" not in files) or ("patches.txt" not in files):
			reason_for_invalidation = (
				f"Files {frappe.bold('hooks.py or patches.txt')} does not exist"
				f" inside {directory}/{directory} directory."
			)
			continue

		hooks = requests.get(
			f"https://api.github.com/repos/{owner}/{repository}/contents/{directory}/hooks.py",
			params={"ref": branch_info["name"]},
			headers=headers,
		).json()
		if "content" not in hooks:
			reason_for_invalidation = f"File {frappe.bold('hooks.py')} could not be fetched."
			continue

		content = b64decode(hooks["content"]).decode()
		match = re.search(r"""app_title = ["'](.*)["']""", content)

		if match:
			return directory, match.group(1)

		reason_for_invalidation = (
			f"File {frappe.bold('hooks.py')} does not have {frappe.bold('app_title')} defined."
		)
		break

	frappe.throw(f"Not a valid Frappe App! {reason_for_invalidation}")
	return None


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
