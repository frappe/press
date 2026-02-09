# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import contextlib
import functools
import json
import re
import socket
import ssl
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypedDict, TypeVar, overload
from urllib.parse import urljoin
from urllib.request import urlopen

import frappe
import frappe.utils
import pytz
import requests
import wrapt
from babel.dates import format_timedelta
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import ExtensionOID
from frappe.utils import get_datetime, get_system_timezone
from frappe.utils.caching import site_cache

from press.utils.email_validator import validate_email

if TYPE_CHECKING:
	from press.press.doctype.team.team import Team


class SupervisorProcess(TypedDict):
	program: str
	name: str
	status: str
	uptime: float | None
	uptime_string: str | None
	message: str | None
	group: str | None
	pid: int | None


def log_error(title, **kwargs):
	if frappe.flags.in_test:
		try:
			raise
		except RuntimeError as e:
			if e.args[0] == "No active exception to reraise":
				pass
			else:
				raise

	reference_doctype = kwargs.get("reference_doctype")
	reference_name = kwargs.get("reference_name")

	# Prevent double logging as `message`
	if reference_doctype and reference_name:
		del kwargs["reference_doctype"]
		del kwargs["reference_name"]

	if doc := kwargs.get("doc"):
		reference_doctype = doc.doctype
		reference_name = doc.name
		del kwargs["doc"]

	with contextlib.suppress(Exception):
		kwargs["user"] = frappe.session.user
		kwargs["team"] = frappe.local.team()

	message = ""
	if serialized := json.dumps(
		kwargs,
		indent=4,
		sort_keys=True,
		default=str,
		skipkeys=True,
	):
		message += f"Data:\n{serialized}\n"

	if traceback := frappe.get_traceback(with_context=True):
		message += f"Exception:\n{traceback}\n"

	with contextlib.suppress(Exception):
		frappe.log_error(
			title=title,
			message=message,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)


@overload
def get_current_team(get_doc: Literal[True]) -> Team: ...


@overload
def get_current_team(get_doc: Literal[False] = False) -> str: ...


def get_current_team(get_doc=False) -> Team | str:
	if frappe.session.user == "Guest":
		frappe.throw("Not Permitted", frappe.AuthenticationError)

	if not hasattr(frappe.local, "request"):
		# if this is not a request, send the current user as default team
		# always use parent_team for background jobs
		return (
			frappe.get_doc(
				"Team",
				{"user": frappe.session.user, "enabled": 1, "parent_team": ("is", "not set")},
			)
			if get_doc
			else frappe.get_value(
				"Team",
				{"user": frappe.session.user, "enabled": 1, "parent_team": ("is", "not set")},
				"name",
			)
		)

	system_user = frappe.session.data.user_type == "System User"

	# get team passed via request header
	x_press_team = frappe.get_request_header("X-Press-Team")
	# In case if X-Press-Team is not passed, check if `team_name` is available in frappe.local
	# `team_name` getting injected by press.saas.api.whitelist_saas_api decorator
	team = x_press_team if x_press_team else getattr(frappe.local, "team_name", "")

	if not team and has_role("Press Admin") and frappe.db.exists("Team", {"user": frappe.session.user}):
		# if user has_role of Press Admin then just return current user as default team
		return (
			frappe.get_doc("Team", {"user": frappe.session.user, "enabled": 1})
			if get_doc
			else frappe.get_value("Team", {"user": frappe.session.user, "enabled": 1}, "name")
		)

	# if team is not passed via header, get the default team for user
	team = team if team else get_default_team_for_user(frappe.session.user)

	if not system_user and not is_user_part_of_team(frappe.session.user, team):
		# if user is not part of the team, get the default team for user
		team = get_default_team_for_user(frappe.session.user)

	if not team:
		frappe.throw(
			f"User {frappe.session.user} is not part of any team",
			frappe.AuthenticationError,
		)

	if not frappe.db.exists("Team", {"name": team, "enabled": 1}):
		frappe.throw("Invalid Team", frappe.AuthenticationError)

	if get_doc:
		return frappe.get_doc("Team", team)

	return team


def _get_current_team():
	if not getattr(frappe.local, "_current_team", None):
		frappe.local._current_team = get_current_team(get_doc=True)
	return frappe.local._current_team


def _system_user():
	return frappe.get_cached_value("User", frappe.session.user, "user_type") == "System User"


def has_role(role, user=None):
	if not user:
		user = frappe.session.user

	return frappe.db.exists("Has Role", {"parenttype": "User", "parent": user, "role": role})


@functools.lru_cache(maxsize=1024)
def get_app_tag(repository, repository_owner, hash):
	return frappe.db.get_value(
		"App Tag",
		{"repository": repository, "repository_owner": repository_owner, "hash": hash},
		"tag",
	)


def get_default_team_for_user(user):
	"""Returns the Team if user has one, or returns the Team in which they belong"""
	if frappe.db.exists("Team", {"user": user, "enabled": 1}):
		return frappe.db.get_value("Team", {"user": user, "enabled": 1}, "name")

	teams = frappe.db.get_values(
		"Team Member",
		filters={"parenttype": "Team", "user": user},
		fieldname="parent",
		pluck="parent",
	)
	for team in teams:
		# if user is part of multiple teams, send the first enabled one
		if frappe.db.exists("Team", {"name": team, "enabled": 1}):
			return team
	return None


def get_valid_teams_for_user(user):
	teams = frappe.db.get_all("Team Member", filters={"user": user}, pluck="parent")
	return frappe.db.get_all("Team", filters={"name": ("in", teams), "enabled": 1}, fields=["name", "user"])


def is_user_part_of_team(user, team):
	"""Returns True if user is part of the team"""
	return frappe.db.exists("Team Member", {"parenttype": "Team", "parent": team, "user": user})


def get_country_info():
	if frappe.flags.in_test:
		return {}

	ip = frappe.local.request_ip
	ip_api_key = frappe.conf.get("ip-api-key")

	def _get_country_info():
		fields = [
			"status",
			"message",
			"continent",
			"continentCode",
			"country",
			"countryCode",
			"region",
			"regionName",
			"city",
			"district",
			"zip",
			"lat",
			"lon",
			"timezone",
			"offset",
			"currency",
			"isp",
			"org",
			"as",
			"asname",
			"reverse",
			"mobile",
			"proxy",
			"hosting",
			"query",
		]

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


def get_last_doc(*args, **kwargs):
	"""Wrapper around frappe.get_last_doc but does not throw"""
	try:
		return frappe.get_last_doc(*args, **kwargs)
	except Exception:
		return None


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


def chunk(iterable, size):
	"""Creates list of elements split into groups of n."""
	for i in range(0, len(iterable), size):
		yield iterable[i : i + size]


@cache(seconds=1800)
def get_minified_script():
	migration_script = "../apps/press/press/scripts/migrate.py"
	with open(migration_script) as f:
		return f.read()


@cache(seconds=1800)
def get_minified_script_2():
	migration_script = "../apps/press/press/scripts/migrate_2.py"
	with open(migration_script) as f:
		return f.read()


def get_frappe_backups(url, email, password):
	return RemoteFrappeSite(url, email, password).get_backups()


def is_allowed_access_performance_tuning():
	team = get_current_team(get_doc=True)
	return team.enable_performance_tuning


class RemoteFrappeSite:
	def __init__(self, url, usr, pwd):
		if not url.startswith("http"):
			# http will be redirected to https in requests
			url = f"http://{url}"

		self.user_site = url.strip()
		self.user_login = usr.strip()
		self.password_login = pwd
		self._remote_backup_links = {}

		self._validate_frappe_site()
		self._validate_user_permissions()

	@property
	def user_sid(self):
		return self._user_sid

	@property
	def site(self):
		return self._site

	@property
	def backup_links(self):
		return self._remote_backup_links

	def _validate_frappe_site(self):
		"""Validates if Frappe Site and sets RemoteBackupRetrieval.site"""
		res = requests.get(f"{self.user_site}/api/method/frappe.ping", timeout=(5, 10))

		if not res.ok:
			frappe.throw("Invalid Frappe Site")

		if res.json().get("message") == "pong":
			# Get final redirect URL
			url = res.url.split("/api/method")[0]
			self._site = url

	def _validate_user_permissions(self):
		"""Validates user permssions on Frappe Site and sets RemoteBackupRetrieval.user_sid"""
		response = requests.post(
			f"{self.site}/api/method/login",
			data={"usr": self.user_login, "pwd": self.password_login},
			timeout=(5, 10),
		)
		if not response.ok:
			if response.status_code == 401:
				frappe.throw("Invalid Credentials")
			else:
				response.raise_for_status()

		self._user_sid = response.cookies.get("sid")

	def _handle_backups_retrieval_failure(self, response):
		log_error(
			"Backups Retrieval Error - Magic Migration",
			response=response.text,
			remote_site=self.site,
		)
		if response.status_code == 403:
			error_msg = "Insufficient Permissions"
		else:
			side = "Client" if 400 <= response.status_code < 500 else "Server"
			error_msg = (
				f"{side} Error occurred: {response.status_code} {response.raw.reason}"
				f" received from {self.site}"
			)
		frappe.throw(error_msg)

	def get_backups(self):
		self._create_fetch_backups_request()
		self._processed_backups_from_response()
		self._validate_missing_backups()

		return self.backup_links

	def _create_fetch_backups_request(self):
		headers = {"Accept": "application/json", "Content-Type": "application/json"}
		suffix = f"?sid={self.user_sid}" if self.user_sid else ""
		res = requests.get(
			f"{self.site}/api/method/frappe.utils.backups.fetch_latest_backups{suffix}",
			headers=headers,
			timeout=(5, 10),
		)
		if not res.ok:
			self._handle_backups_retrieval_failure(res)
		self._fetch_latest_backups_response = res.json().get("message", {})

	def _validate_missing_backups(self):
		missing_files = []

		for file_type, file_path in self.backup_links.items():
			if not file_path:
				missing_files.append(file_type)

		if missing_files:
			missing_config = "site config and " if not self.backup_links.get("config") else ""
			missing_backups = (
				f"Missing {missing_config}backup files: {', '.join([x.title() for x in missing_files])}"
			)
			frappe.throw(missing_backups)

	def __process_frappe_url(self, path):
		if not path:
			return None
		backup_path = path.split("/private")[1]
		return urljoin(self.site, f"{backup_path}?sid={self.user_sid}")

	def _processed_backups_from_response(self):
		for file_type, file_path in self._fetch_latest_backups_response.items():
			self._remote_backup_links[file_type] = self.__process_frappe_url(file_path)


@site_cache(ttl=5 * 60)
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


def human_readable(num: int | float) -> str:
	"""Assumes int data to describe size is in Bytes"""
	for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
		if abs(num) < 1024:
			return f"{num:3.1f} {unit}B"
		num /= 1024
	return f"{num:.1f} YiB"


def is_json(string):
	if isinstance(string, str):
		string = string.strip()
		return string.startswith("{") and string.endswith("}")
	if isinstance(string, (dict, list)):
		return True
	return None


def is_list(string):
	if isinstance(string, list):
		return True
	if isinstance(string, str):
		string = string.strip()
		return string.startswith("[") and string.endswith("]")
	return False


def guess_type(value):
	type_dict = {
		int: "Number",
		float: "Number",
		bool: "Boolean",
		dict: "JSON",
		list: "JSON",
		str: "String",
	}
	value_type = type(value)

	if value_type in type_dict:
		return type_dict[value_type]
	if is_json(value):
		return "JSON"
	return "String"


def convert(string):
	if isinstance(string, (dict, list)):
		return json.dumps(string)
	return string


def unique(seq, unique_by=None):
	"""Remove duplicates from a list based on an expression
	Usage:
	unique([{'x': 1, 'y': 2}, {'x': 1, 'y': 2}], lambda d: d['x'])
	# output: [{'x': 1, 'y': 2}]
	"""

	unique_by = unique_by or (lambda x: x)
	out = []
	seen = set()
	for d in seq:
		unique_key = unique_by(d)
		if unique_key not in seen:
			out.append(d)
			seen.add(unique_key)
	return out


def group_children_in_result(result, child_field_map):
	"""Usage:
	result =
	[
	{'name': 'test1', 'full_name': 'Faris Ansari', role: 'System Manager'},
	{'name': 'test1', 'full_name': 'Faris Ansari', role: 'Press Admin'},
	{'name': 'test2', 'full_name': 'Aditya Hase', role: 'Press Admin'},
	{'name': 'test2', 'full_name': 'Aditya Hase', role: 'Press Member'},
	]

	out = group_children_in_result(result, {'role': 'roles'})
	print(out)
	[
	{'name': 'test1', 'full_name': 'Faris Ansari', roles: ['System Manager', 'Press Admin']},
	{'name': 'test2', 'full_name': 'Aditya Hase', roles: ['Press Admin', 'Press Member']},
	]
	"""
	out = {}
	for d in result:
		out[d.name] = out.get(d.name) or d
		for child_field, target in child_field_map.items():
			out[d.name][target] = out[d.name].get(target) or []
			out[d.name][target].append(d.get(child_field))
			out[d.name].pop(child_field, "")
	return out.values()


def convert_user_timezone_to_utc(datetime):
	timezone = pytz.timezone(get_system_timezone())
	datetime_obj = get_datetime(datetime)
	return timezone.localize(datetime_obj).astimezone(pytz.utc).isoformat()


class ttl_cache:
	"""
	Does not invalidate cache depending on function
	args. Ideally it's for functions with 0 arity.

	Example:

	# or use it as a decorator
	cached_func = ttl_cache()(func)

	# to invalidate cache
	cached_func.cache.invalidate()
	"""

	def __init__(self, ttl: int = 60):
		self.ttl = ttl
		self.result = None
		self.start = 0

	def invalidate(self):
		self.result = None
		self.start = 0

	def __call__(self, func):
		self.result = None
		self.start = time.time()

		def wrapper_func(*args, **kwargs):
			if self.result is not None and (time.time() - self.start) < self.ttl:
				return self.result
			self.start = time.time()
			self.result = func(*args, **kwargs)
			return self.result

		wrapper_func.cache = self
		return wrapper_func


def poly_get_doctype(doctypes, name):
	"""Get the doctype value from the given name of a doc from a list of doctypes"""
	for doctype in doctypes:
		if frappe.db.exists(doctype, name):
			return doctype
	return doctypes[-1]


def reconnect_on_failure():
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		try:
			return wrapped(*args, **kwargs)
		except Exception as e:
			if frappe.db.is_interface_error(e):
				frappe.db.connect()
				return wrapped(*args, **kwargs)
			raise

	return wrapper


def parse_supervisor_status(output: str) -> list[SupervisorProcess]:
	# Note: this function is verbose due to supervisor status being kinda
	# unstructured, and I'm not entirely sure of all possible input formats.
	#
	# example lines:
	# ```
	#   frappe-bench-web:frappe-bench-frappe-web            RUNNING   pid 1327, uptime 23:13:00
	#   frappe-bench-workers:frappe-bench-frappe-worker-4   RUNNING   pid 3794915, uptime 68 days, 6:10:37
	#   sshd                                                FATAL     Exited too quickly (process log may have details)
	# ```

	pid_rex = re.compile(r"^pid\s+\d+")

	lines = output.split("\n")
	parsed: list[SupervisorProcess] = []

	for line in lines:
		if "DeprecationWarning:" in line or "pkg_resources is deprecated" in line:
			continue

		entry: SupervisorProcess = {
			"program": "",
			"status": "",
			"name": "",
			"uptime": None,
			"uptime_string": None,
			"message": None,
			"group": None,
			"pid": None,
		}

		splits = strip_split(line, maxsplit=1)
		if len(splits) != 2:
			continue

		program, info = splits

		# example: "code-server"
		entry["program"] = program
		entry["name"] = program

		prog_splits = program.split(":")

		if len(prog_splits) == 2:
			# example: "frappe-bench-web:frappe-bench-frappe-web"
			entry["group"] = prog_splits[0]
			entry["name"] = prog_splits[1]

		info_splits = strip_split(info, maxsplit=1)
		if len(info_splits) != 2:
			continue

		# example: "STOPPED   Not started"
		entry["status"] = info_splits[0].title()
		if not pid_rex.match(info_splits[1]):
			entry["message"] = info_splits[1]

		else:
			# example: "RUNNING   pid 9, uptime 150 days, 2:55:52"
			pid, uptime, uptime_string = parse_pid_uptime(info_splits[1])
			entry["pid"] = pid
			entry["uptime"] = uptime
			entry["uptime_string"] = uptime_string

		parsed.append(entry)

	return parsed


def parse_pid_uptime(s: str):
	pid: int | None = None
	uptime: float | None = None
	splits = strip_split(s, ",", maxsplit=1)

	if len(splits) != 2:
		return pid, uptime, None

	# example: "pid 9"
	pid_split = splits[0]

	# example: "uptime 150 days, 2:55:52"
	uptime_split = splits[1]

	pid_split, uptime_split = splits
	pid_splits = strip_split(pid_split, maxsplit=1)

	if len(pid_splits) == 2 and pid_splits[0] == "pid":
		pid = int(pid_splits[1])

	uptime_string = ""
	uptime_splits = strip_split(uptime_split, maxsplit=1)
	if len(uptime_splits) == 2 and uptime_splits[0] == "uptime":
		uptime_string = uptime_splits[1]
		uptime = parse_uptime(uptime_string)

	return pid, uptime, uptime_string


def parse_uptime(s: str) -> float | None:
	# example `s`: "uptime 68 days, 6:10:37"
	days = 0.0
	hours = 0.0
	minutes = 0.0
	seconds = 0.0

	t_string = ""
	splits = strip_split(s, sep=",", maxsplit=1)

	# Uptime has date info too
	if len(splits) == 2 and (splits[0].endswith("days") or splits[0].endswith("day")):
		t_string = splits[1]
		d_string = splits[0].split(" ")[0]
		days = float(d_string)

	# Uptime less than a day
	elif len(splits) == 1:
		t_string = splits[0]
	else:
		return None

	# Time string format hh:mm:ss
	t_splits = t_string.split(":")
	if len(t_splits) == 3:
		hours = float(t_splits[0])
		minutes = float(t_splits[1])
		seconds = float(t_splits[2])

	return timedelta(
		days=days,
		hours=hours,
		minutes=minutes,
		seconds=seconds,
	).total_seconds()


def strip_split(string: str, sep: str = " ", maxsplit: int = -1) -> list[str]:
	splits: list[str] = []
	for part in string.split(sep, maxsplit):
		if p_stripped := part.strip():
			splits.append(p_stripped)

	return splits


def get_filepath(root: str, filename: str, max_depth: int = 1):
	"""
	Returns the absolute path of a `filename` under `root`. If
	it is not found, returns None.

	Example: get_filepath("apps/hrms", "hooks.py", 2)

	Depth of search under file tree can be set using `max_depth`.
	"""
	path = _get_filepath(
		Path(root),
		filename,
		max_depth,
	)

	if path is None:
		return path

	return path.absolute().as_posix()


def _get_filepath(root: Path, filename: str, max_depth: int) -> Path | None:
	if root.name == filename:
		return root
	if max_depth == 0 or not root.is_dir():
		return None
	for new_root in root.iterdir():
		if possible_path := _get_filepath(
			new_root,
			filename,
			max_depth - 1,
		):
			return possible_path
	return None


def fmt_timedelta(td: timedelta | int):
	locale = frappe.local.lang.replace("-", "_") if frappe.local.lang else None
	return format_timedelta(td, locale=locale)


V = TypeVar("V")


def flatten(value_lists: "list[list[V]]") -> "list[V]":
	return [value for values in value_lists for value in values]


def is_valid_hostname(hostname):
	if len(hostname) > 255:
		return False
	allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
	return all(allowed.match(x) for x in hostname.split("."))


def mask_email(email: str, percentage: float) -> str:
	"""
	Mask email address with 'x'

	Example:
	> mask_email("tanmoysarkar@gmail.com", 50)
	> tanxxxxxxkar@gmxxxxcom

	> mask_email("tanmoysarkar@gmail.com", 30)
	> tanmxxxarkar@gmaxx.com
	"""
	if "@" not in email:
		return "Invalid email address"

	local_part, domain = email.split("@")

	local_mask_length = int(len(local_part) * (percentage / 100))
	domain_mask_length = int(len(domain) * (percentage / 100))

	def mask_middle(s: str, mask_len: int) -> str:
		if mask_len == 0:
			return s
		start_idx = (len(s) - mask_len) // 2
		end_idx = start_idx + mask_len
		return s[:start_idx] + "x" * mask_len + s[end_idx:]

	masked_local_part = mask_middle(local_part, local_mask_length)
	masked_domain = mask_middle(domain, domain_mask_length)

	return masked_local_part + "@" + masked_domain


def get_mariadb_root_password(site):
	from frappe.utils.password import get_decrypted_password

	database_server, managed_database_service = frappe.get_cached_value(
		"Bench", site.bench, ["database_server", "managed_database_service"]
	)

	if managed_database_service:
		doctype = "Managed Database Service"
		name = managed_database_service
		field = "root_user_password"
	else:
		doctype = "Database Server"
		name = database_server
		field = "mariadb_root_password"

	return get_decrypted_password(doctype, name, field)


def is_valid_email_address(email) -> bool:
	if frappe.cache.exists(f"email_validity:{email}"):
		return bool(frappe.utils.data.cint(frappe.cache.get_value(f"email_validity:{email}")))
	try:
		is_valid = bool(validate_email(email=email, check_mx=True, verify=True, smtp_timeout=10))
		frappe.cache.set_value(f"email_validity:{email}", int(is_valid), expires_in_sec=3600)
		if not is_valid:
			log_error("Invalid email address on signup", data=email)
		return bool(is_valid)
	except Exception as e:
		log_error("Email validation error on signup", data=e)
		frappe.cache.set_value(f"email_validity:{email}", 0, expires_in_sec=3600)
		return False


def get_full_chain_cert_of_domain(domain: str) -> str:
	cert_chain = []

	# Get initial certificate
	context = ssl.create_default_context()
	with socket.create_connection((domain, 443)) as sock:  # noqa: SIM117
		with context.wrap_socket(sock, server_hostname=domain) as ssl_socket:
			cert_pem = ssl.DER_cert_to_PEM_cert(ssl_socket.getpeercert(True))  # type: ignore
			cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
			cert_chain.append(cert_pem)

	# Walk up the chain via certificate authority information access (AIA)
	while True:
		try:
			aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS)
			for access in aia.value:
				if access.access_method._name == "caIssuers":
					uri = access.access_location._value
					with urlopen(uri) as response:
						der_cert = response.read()
						pem_cert = ssl.DER_cert_to_PEM_cert(der_cert)
						cert = x509.load_pem_x509_certificate(pem_cert.encode(), default_backend())
						cert_chain.append(pem_cert)
						break
		except:  # noqa: E722
			break

	cert_chain_str = ""
	for cert in cert_chain:
		cert_chain_str += cert + "\n"
	return cert_chain_str


def timer(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		start_timestamp = time.time()
		result = f(*args, **kwargs)
		end_timestamp = time.time()
		duration = end_timestamp - start_timestamp
		if not hasattr(frappe.local, "timers"):
			frappe.local.timers = {}
		frappe.local.timers[f.__name__] = frappe.utils.rounded(duration, precision=3)
		return result

	return wrap


def validate_subdomain(subdomain: str):
	site_regex = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$"
	if not subdomain:
		frappe.throw("Subdomain is required to create a site.")
	if not re.match(site_regex, subdomain):
		frappe.throw("Subdomain contains invalid characters. Use lowercase characters, numbers and hyphens")
	if len(subdomain) > 32:
		frappe.throw("Subdomain too long. Use 32 or less characters")
	if len(subdomain) < 5:
		frappe.throw("Subdomain too short. Use 5 or more characters")


@site_cache(ttl=120)
def servers_using_alternative_port_for_communication() -> list:
	servers = frappe.db.get_value(
		"Press Settings", None, "servers_using_alternative_http_port_for_communication"
	)
	if not servers:
		return []
	sl: list[str] = servers.split("\n")
	return [x.strip() for x in sl if x.strip()]


def get_nearest_cluster():
	import math

	cluster_locations = {
		"Mumbai": {"latitude": 19.0760, "longitude": 72.8777},
		"Zurich": {"latitude": 47.3769, "longitude": 8.5417},
		"Frankfurt": {"latitude": 50.1109, "longitude": 8.6821},
		"Singapore": {"latitude": 1.3521, "longitude": 103.8198},
		"London": {"latitude": 51.5074, "longitude": -0.1278},
		"Virginia": {"latitude": 38.8048, "longitude": -77.0469},
		"Jakarta": {"latitude": -6.2088, "longitude": 106.8456},
		"Bahrain": {"latitude": 26.0667, "longitude": 50.5577},
		"UAE": {"latitude": 24.4539, "longitude": 54.3773},
		"KSA": {"latitude": 24.7136, "longitude": 46.6753},
		"Cape Town": {"latitude": -33.9249, "longitude": 18.4241},
		"Johannesburg": {"latitude": -26.2041, "longitude": 28.0473},
	}

	def haversine_distance(lat1, lon1, lat2, lon2):
		R = 6371  # Radius of Earth in kilometers

		lat1_rad = math.radians(lat1)
		lon1_rad = math.radians(lon1)
		lat2_rad = math.radians(lat2)
		lon2_rad = math.radians(lon2)

		longitude_diff = lon2_rad - lon1_rad
		latitude_diff = lat2_rad - lat1_rad

		a = (
			math.sin(latitude_diff / 2) ** 2
			+ math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(longitude_diff / 2) ** 2
		)
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

		return R * c

	user_geo_data = get_country_info()
	if not user_geo_data:
		return None

	user_latitude = user_geo_data.get("lat", 0.0)
	user_longitude = user_geo_data.get("lon", 0.0)

	min_distance = float("inf")
	nearest_cluster = None

	for cluster_name, cluster_coords in cluster_locations.items():
		cluster_latitude = cluster_coords["latitude"]
		cluster_longitude = cluster_coords["longitude"]

		distance = haversine_distance(user_latitude, user_longitude, cluster_latitude, cluster_longitude)

		if distance < min_distance:
			min_distance = distance
			nearest_cluster = cluster_name

	return nearest_cluster
