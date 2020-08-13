# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import functools
import json
import requests
from datetime import datetime, timedelta
from python_minifier import minify


def log_error(title, **kwargs):
	traceback = frappe.get_traceback()
	serialized = json.dumps(kwargs, indent=4, sort_keys=True, default=str, skipkeys=True)
	message = f"Data:\n{serialized}\nException:\n{traceback}"
	frappe.log_error(title=title, message=message)


def get_current_team():
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
	return minify(script_contents)


def verify_frappe_site(site):
	schema = "http"
	status = False

	try:
		res = requests.get(f"{schema}://{site}/api/method/frappe.ping")
		data = res.json()
		if data.get("message") == "pong":
			status = True
	except Exception:
		pass

	return {"schema": schema, "status": status}


def get_frappe_backups(site, auth):
	schema = "https"
	headers = {"Accept": "application/json", "Content-Type": "application/json"}
	usr = auth.get("usr")
	pwd = auth.get("pwd")
	passwd = usr and pwd

	def url(path):
		host = site.split(":")[0]
		file = path.lstrip(f"./{host}/private/")
		url = f"{schema}://{site}/{file}?sid={sid}"
		return url

	if passwd:
		# tested - works
		response = requests.post(
			f"{schema}://{site}/api/method/login", data={"usr": usr, "pwd": pwd},
		)
		sid = response.cookies.get("sid")

	suffix = f"?sid={sid}" if passwd else ""
	data = requests.post(
		f"{schema}://{site}/api/method/frappe.utils.backups.fetch_latest_backups{suffix}",
		headers=headers,
	)

	if data.ok:
		payload = data.json()
		files = {x: url(y) for x, y in payload.get("message", {}).items()}
		exc = payload.get("exc", "")
	else:
		files = {}
		exc = data.raw

	return {"site": site, "status": data.status_code, "exc": exc, "files": files}
