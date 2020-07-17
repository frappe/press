# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

from datetime import datetime, timedelta
import frappe
from pathlib import Path
from press.utils import get_current_team, log_error
import requests
import jwt
import re
from base64 import b64decode
from frappe.core.utils import find


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
	expiry = now + timedelta(minutes=10)
	payload = {"iat": int(now.timestamp()), "exp": int(expiry.timestamp()), "iss": app_id}
	token = jwt.encode(payload, key.encode(), algorithm="RS256")
	return token.decode()


def get_access_token(install):
	token = get_jwt_token()
	headers = {
		"Authorization": f"Bearer {token}",
		"Accept": "application/vnd.github.machine-man-preview+json",
	}
	response = requests.post(
		f"https://api.github.com/app/installations/{install}/access_tokens", headers=headers,
	).json()
	return response["token"]


@frappe.whitelist()
def options():
	team = get_current_team()
	token = frappe.db.get_value("Team", team, "github_access_token")
	enable_custom_apps = frappe.db.get_value("Team", team, "enable_custom_apps")
	public_link = frappe.db.get_single_value("Press Settings", "github_app_public_link")

	groups = frappe.get_all("Release Group", {"public": True})
	for group in groups:
		group_doc = frappe.get_doc("Release Group", group.name)
		group_apps = frappe.get_all(
			"Frappe App",
			fields=["name", "frappe", "scrubbed", "branch"],
			filters={"name": ("in", [row.app for row in group_doc.apps])},
		)
		frappe_app = find(group_apps, lambda x: x.frappe)
		group["frappe"] = frappe_app
		group["apps"] = group_apps

	options = {
		"authorized": bool(token),
		"enable_custom_apps": bool(enable_custom_apps),
		"installation_url": f"{public_link}/installations/new",
		"installations": installations(token) if token else [],
		"groups": groups,
	}
	return options


def installations(token):
	headers = {
		"Authorization": f"token {token}",
		"Accept": "application/vnd.github.machine-man-preview+json",
	}
	response = requests.get("https://api.github.com/user/installations", headers=headers)
	installations = []
	for installation in response.json()["installations"]:
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
	response = requests.get(
		f"https://api.github.com/user/installations/{installation}/repositories",
		params={"per_page": 100},
		headers=headers,
	)
	repositories = []
	for repository in response.json()["repositories"]:
		repositories.append(
			{
				"id": repository["id"],
				"name": repository["name"],
				"private": repository["private"],
				"url": repository["html_url"],
			}
		)
	return repositories


@frappe.whitelist()
def repository(installation, owner, name):
	token = get_access_token(installation)
	headers = {
		"Authorization": f"token {token}",
	}
	repo = requests.get(
		f"https://api.github.com/repos/{owner}/{name}", headers=headers,
	).json()
	repo["branches"] = requests.get(
		f"https://api.github.com/repos/{owner}/{name}/branches",
		params={"per_page": 100},
		headers=headers,
	).json()
	return repo


@frappe.whitelist()
def app(installation, owner, repository, branch):
	def _construct_tree(tree, children, children_map):
		for file in children:
			if file.path in children_map:
				tree[file.name] = _construct_tree({}, children_map[file.path], children_map)
			else:
				tree[file.name] = None
		return tree

	def _generate_files_tree(files):
		children = {}
		for file in files:
			path = Path(file["path"])
			children.setdefault(str(path.parent), []).append(
				frappe._dict({"name": str(path.name), "path": file["path"]})
			)
		return _construct_tree({}, children["."], children)

	token = get_access_token(installation)
	headers = {
		"Authorization": f"token {token}",
	}
	branch = requests.get(
		f"https://api.github.com/repos/{owner}/{repository}/branches/{branch}",
		headers=headers,
	).json()
	sha = branch["commit"]["commit"]["tree"]["sha"]
	contents = requests.get(
		f"https://api.github.com/repos/{owner}/{repository}/git/trees/{sha}",
		params={"recursive": True},
		headers=headers,
	).json()

	tree = _generate_files_tree(contents["tree"])
	app_name = None
	title = None
	if "setup.py" in tree and "requirements.txt" in tree:
		for directory, files in tree.items():
			if files and "hooks.py" in files and "patches.txt" in files:
				app_name = directory
				hooks = requests.get(
					f"https://api.github.com/repos/{owner}/{repository}/contents/{app_name}/hooks.py",
					params={"ref": branch["name"]},
					headers=headers,
				).json()
				content = b64decode(hooks["content"]).decode()
				match = re.search('app_title = "(.*)"', content)
				if match:
					title = match.group(1)
				break
	return {"name": app_name, "title": title}
