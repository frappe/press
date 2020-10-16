# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import functools
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests

import frappe


def log_error(title, **kwargs):
	traceback = frappe.get_traceback()
	serialized = json.dumps(kwargs, indent=4, sort_keys=True, default=str, skipkeys=True)
	message = f"Data:\n{serialized}\nException:\n{traceback}"
	frappe.log_error(title=title, message=message)


def get_current_team(get_doc=False):
	if not hasattr(frappe.local, "request"):
		# if this is not a request, send the current user as default team
		return frappe.session.user

	user_is_system_user = frappe.session.data.user_type == "System User"
	# get team passed via request header
	team = frappe.get_request_header("X-Press-Team")

	if not team:
		# if team is not passed via header, get the first team that this user is part of
		team = frappe.db.get_value(
			"Team Member", {"parenttype": "Team", "user": frappe.session.user}, "parent"
		)

	if not frappe.db.exists("Team", team):
		frappe.throw("Invalid Team", frappe.PermissionError)

	valid_team = frappe.db.exists(
		"Team Member", {"parenttype": "Team", "parent": team, "user": frappe.session.user}
	)
	if not valid_team and not user_is_system_user:
		frappe.throw(
			"User {0} does not belong to Team {1}".format(frappe.session.user, team),
			frappe.PermissionError,
		)

	if get_doc:
		return frappe.get_doc("Team", team)

	return team


def get_default_team_for_user(user):
	"""Returns the Team if user has one, or returns the Team to which they belong"""
	if frappe.db.exists("Team", user):
		return user

	team = frappe.db.get_value(
		"Team Member", filters={"parenttype": "Team", "user": user}, fieldname="parent"
	)
	if team:
		return team


def get_country_info():
	ip = frappe.local.request_ip
	ip_api_key = frappe.conf.get("ip-api-key")

	def _get_country_info():
		fields = ["countryCode", "country", "regionName", "city"]
		res = requests.get(
			"https://pro.ip-api.com/json/{ip}?key={key}&fields={fields}".format(
				ip=ip, key=ip_api_key, fields=",".join(fields)
			)
		)
		try:
			data = res.json()
			if data.get("status") != "fail":
				return data
		except Exception:
			pass

		return {}

	return frappe.cache().hget("ip_country_map", ip, generator=_get_country_info)


def cache(seconds: int, maxsize: int = 128, typed: bool = False):
	def wrapper_cache(func):
		func = functools.lru_cache(maxsize=maxsize, typed=typed)(func)
		func.delta = timedelta(seconds=seconds)
		func.expiration = datetime.utcnow() + func.delta

		@functools.wraps(func)
		def wrapped_func(*args, **kwargs):
			if datetime.utcnow() >= func.expiration:
				func.cache_clear()
				func.expiration = datetime.utcnow() + func.delta

			return func(*args, **kwargs)

		return wrapped_func

	return wrapper_cache


@cache(seconds=1800)
def get_minified_script():
	migration_script = "../apps/press/press/scripts/migrate.py"
	script_contents = open(migration_script).read()
	return script_contents


def verify_frappe_site(site_url):
	url = None

	try:
		res = requests.get(f"{site_url}/api/method/frappe.ping")
		if res.ok:
			data = res.json()
			if data.get("message") == "pong":
				url = res.url.split("/api")[0]
	except Exception:
		pass

	return url


def get_frappe_backups(site_url, username, password):
	headers = {"Accept": "application/json", "Content-Type": "application/json"}

	if not site_url.startswith("http"):
		# http will be redirected to https in requests
		site_url = f"http://{site_url}"

	site_url = verify_frappe_site(site_url)
	if not site_url:
		frappe.throw("Invalid Frappe Site")

	# tested - works
	response = requests.post(
		f"{site_url}/api/method/login", data={"usr": username, "pwd": password},
	)
	if response.ok:
		sid = response.cookies.get("sid")
	else:
		if response.status_code == 401:
			frappe.throw("Invalid Credentials")
		else:
			response.raise_for_status()

	suffix = f"?sid={sid}" if sid else ""
	res = requests.get(
		f"{site_url}/api/method/frappe.utils.backups.fetch_latest_backups{suffix}",
		headers=headers,
	)

	def url(file_path, sid):
		if not file_path:
			return None
		backup_path = file_path.split("/private")[1]
		return urljoin(site_url, f"{backup_path}?sid={sid}")

	if res.ok:
		payload = res.json()
		files = payload.get("message", {})

		missing_files = []
		file_urls = {}
		for file_type, file_path in files.items():
			if not file_path:
				missing_files.append(file_type)
			else:
				file_urls[file_type] = url(file_path, sid)

		if missing_files:
			missing_config = "site config and " if not file_urls.get("config") else ""
			missing_backups = (
				f"Missing {missing_config}backup files:"
				f" {', '.join([x.title() for x in missing_files])}"
			)
			frappe.throw(missing_backups)

		# check if database is > 500MiB and show alert
		database_size = float(
			requests.head(file_urls["database"]).headers.get("Content-Length", 999)
		)

		if (database_size / 1024 * 2) > 500:
			frappe.throw("Your site exceeds the limits for this operation.")

		return file_urls
	else:
		log_error(
			"Backups Retreival Error - Magic Migration", response=res.text, remote_site=site_url
		)
		res.raise_for_status()


def get_client_blacklisted_keys() -> list:
	"""Returns list of blacklisted Site Config Keys accessible to Press /dashboard users."""
	return list(
		set(
			[
				x.key
				for x in frappe.get_all("Site Config Key Blacklist", fields=["`key`"])
				+ frappe.get_all("Site Config Key", fields=["`key`"], filters={"internal": True})
			]
		)
	)


def sanitize_config(config: dict) -> dict:
	client_blacklisted_keys = get_client_blacklisted_keys()
	sanitized_config = config.copy()

	for key in config:
		if key in client_blacklisted_keys:
			sanitized_config.pop(key)

	return sanitized_config


def developer_mode_only():
	if not frappe.conf.developer_mode:
		frappe.throw("You don't know what you're doing. Go away!", frappe.ValidationError)
