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


@frappe.whitelist(allow_guest=True)
def hook(*args, **kwargs):
	try:
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
		doc.insert(ignore_permissions=True)
	except Exception:
		log_error("GitHub Webhook Error", args=args, kwargs=kwargs)



@frappe.whitelist()
def options():
	team = get_current_team()
	token = frappe.db.get_value("Team", team, "github_access_token")
	public_link = frappe.db.get_single_value("Press Settings", "github_app_public_link")
	options = {
		"authorized": bool(token),
		"installation_url": f"{public_link}/installations/new",
		"installations": installations(token) if token else [],
	}
	return options


def installations(token):
	headers = {
		"Authorization": f"token {token}",
		"Accept": "application/vnd.github.machine-man-preview+json",
	}
	response = requests.get(f"https://api.github.com/user/installations", headers=headers)
	installations = []
	for installation in response.json()["installations"]:
		installations.append(
			{
				"id": installation["id"],
				"login": installation["account"]["login"],
				"url": installation["account"]["html_url"],
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
		f"https://api.github.com/repos/{owner}/{name}/branches", headers=headers,
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
	if "setup.py" in tree and "requirements.txt" in tree:
		for directory, files in tree.items():
			if files and "hooks.py" in files and "patches.txt" in files:
				app_name = directory
				break
	return {
		"name": app_name,
	}
