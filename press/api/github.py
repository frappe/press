# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import re
from base64 import b64decode, urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict
from urllib.parse import urlencode, urlparse

import frappe
import jwt
import requests
import tomli
from frappe.utils.verified_command import get_secret

from press.utils import get_current_team, log_error

if TYPE_CHECKING:
	from press.press.doctype.github_webhook_log.github_webhook_log import GitHubWebhookLog


DEFAULT_GITHUB_REDIRECT_PATH = "/dashboard"
GITHUB_OAUTH_STATE_MAX_AGE = timedelta(minutes=10)


class InvalidGitHubOAuthState(frappe.ValidationError):
	pass


class AppDependencyFetch(TypedDict):
	frappe_dependencies: dict[str, str]
	python_version: str | None


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


def get_installation_data(team: str, redirect_url: str | None = None) -> dict[str, str]:
	public_link = frappe.db.get_single_value("Press Settings", "github_app_public_link")
	return {
		"installation_url": f"{public_link}/installations/new",
		"state": encode_github_oauth_state(team, redirect_url),
	}


def encode_github_oauth_state(team: str, redirect_url: str | None = None) -> str:
	payload = {
		"issued_at": int(datetime.now().timestamp()),
		"redirect_url": get_safe_github_redirect_url(redirect_url),
		"team": team,
		"user": frappe.session.user,
	}
	encoded_payload = _encode_github_state_payload(payload)
	return f"{encoded_payload}.{_sign_github_oauth_state(encoded_payload)}"


def decode_github_oauth_state(state: str) -> dict[str, str]:
	try:
		encoded_payload, signature = state.rsplit(".", 1)
	except ValueError as exc:
		raise InvalidGitHubOAuthState("Invalid GitHub authorization state") from exc

	expected_signature = _sign_github_oauth_state(encoded_payload)
	if not hmac.compare_digest(signature, expected_signature):
		raise InvalidGitHubOAuthState("Invalid GitHub authorization state")

	try:
		payload = json.loads(_decode_github_state_payload(encoded_payload))
	except Exception as exc:
		raise InvalidGitHubOAuthState("Invalid GitHub authorization state") from exc

	redirect_url = get_safe_github_redirect_url(payload.get("redirect_url"))
	issued_at = payload.get("issued_at")
	team = payload.get("team")
	user = payload.get("user")

	if (
		not team
		or not isinstance(team, str)
		or not user
		or not isinstance(user, str)
		or not isinstance(issued_at, int)
	):
		raise InvalidGitHubOAuthState("Invalid GitHub authorization state")

	if datetime.now().timestamp() - issued_at > GITHUB_OAUTH_STATE_MAX_AGE.total_seconds():
		raise InvalidGitHubOAuthState("Invalid GitHub authorization state")

	if user != frappe.session.user:
		raise InvalidGitHubOAuthState("Invalid GitHub authorization state")

	return {"redirect_url": redirect_url, "team": team}


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
def clear_token_and_get_installation_url(redirect_url: str | None = None):
	team = get_current_team()
	clear_current_team_access_token(team)
	return get_installation_data(team, redirect_url)


def clear_current_team_access_token(team: str | None = None):
	team = team or get_current_team()
	frappe.db.set_value("Team", team, "github_access_token", "")  # clear access token


@frappe.whitelist()
def options(redirect_url: str | None = None):
	team = get_current_team()
	token = frappe.db.get_value("Team", team, "github_access_token")
	installation_data = get_installation_data(team, redirect_url)

	return {
		"authorized": bool(token),
		**installation_data,
		"installations": installations(token) if token else [],
	}


def get_safe_github_redirect_url(redirect_url: str | None = None) -> str:
	if not redirect_url:
		return DEFAULT_GITHUB_REDIRECT_PATH

	parsed_redirect_url = urlparse(redirect_url)
	if parsed_redirect_url.scheme or parsed_redirect_url.netloc:
		parsed_site_url = urlparse(frappe.utils.get_url())
		if (
			parsed_redirect_url.scheme != parsed_site_url.scheme
			or parsed_redirect_url.netloc != parsed_site_url.netloc
		):
			return DEFAULT_GITHUB_REDIRECT_PATH

	redirect_path = parsed_redirect_url.path or DEFAULT_GITHUB_REDIRECT_PATH
	if not redirect_path.startswith("/dashboard"):
		return DEFAULT_GITHUB_REDIRECT_PATH

	if parsed_redirect_url.query:
		redirect_path = f"{redirect_path}?{parsed_redirect_url.query}"

	if parsed_redirect_url.fragment:
		redirect_path = f"{redirect_path}#{parsed_redirect_url.fragment}"

	return redirect_path


def get_github_callback_login_redirect(code: str | None, state: str | None) -> str:
	login_url = "/dashboard/login"
	if not (code and state):
		return frappe.utils.get_url(login_url)

	callback_url = f"/github/authorize?{urlencode({'code': code, 'state': state})}"
	return frappe.utils.get_url(f"{login_url}?{urlencode({'redirect': callback_url})}")


def _decode_github_state_payload(payload: str) -> str:
	padding = "=" * (-len(payload) % 4)
	return urlsafe_b64decode(f"{payload}{padding}").decode()


def _encode_github_state_payload(payload: dict[str, str | int]) -> str:
	encoded_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
	return urlsafe_b64encode(encoded_payload).decode().rstrip("=")


def _sign_github_oauth_state(encoded_payload: str) -> str:
	return hmac.new(get_secret().encode(), encoded_payload.encode(), digestmod=hashlib.sha256).hexdigest()


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
		data = response.json()
		if not response.ok:
			frappe.throw("Error fetching installations from GitHub: " + data.get("message", "Unknown error"))
		if len(data.get("installations", [])) < 100:
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
def repository(owner: str, name: str, installation: str | None = None):
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
def app(owner: str, repository: str, branch: str, installation: str | None = None):
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
def branches(owner: str, name: str, installation: str | None = None, app_source: str | None = None):
	"""
	Return ALL branches for the repo, following GitHub pagination.
	"""
	if not installation and app_source:
		installation = frappe.db.get_value("App Source", app_source, "github_installation_id")

	headers = get_auth_headers(installation)

	out: list[dict] = []
	page = 1
	while True:
		resp = requests.get(
			f"https://api.github.com/repos/{owner}/{name}/branches",
			params={"per_page": 100, "page": page},
			headers=headers,
			timeout=20,
		)
		if not resp.ok:
			frappe.throw("Error fetching branch list from GitHub: " + resp.text)

		chunk = resp.json() or []
		out.extend(chunk)

		# If GitHub says there is a next page, keep going.
		has_next = "next" in (resp.links or {})
		if not has_next or len(chunk) == 0:
			break
		page += 1

	# Optional: float `version-*` branches to the top without touching the UI
	out.sort(
		key=lambda b: (0 if str(b.get("name", "")).startswith("version-") else 1, str(b.get("name", "")))
	)
	return out


def get_auth_headers(installation_id: str | None = None) -> "dict[str, str]":
	if token := get_access_token(installation_id):
		return {"Authorization": f"token {token}"}
	return {}


def _get_compatible_frappe_version_from_pyproject(
	owner: str, repository: str, branch_info: dict, headers: dict[str, str]
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

		if not hasattr(e, "doc") or not hasattr(e, "lineno"):
			frappe.throw("\n".join(out))

		lines = e.doc.splitlines()

		start = max(e.lineno - 3, 0)
		end = e.lineno + 2

		for i, line in enumerate(lines[start:end], start=start + 1):
			out.append(f"{i:>4}: {line}")

		out_s = "\n".join(out)
		frappe.throw(out_s)

	with contextlib.suppress(Exception):
		compatible_frappe_version = str(
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
			"Please ensure '[tool.bench.frappe-dependencies]' is defined. "
			"Click <a class='underline' href='https://docs.frappe.io/cloud/benches/custom-app#note'>here</a> for more details."
		)
		raise  # for mypy: NoReturn

	return compatible_frappe_version


def _get_app_name_and_title_from_hooks(
	owner,
	repository,
	branch_info,
	headers,
	tree,
) -> tuple[str, str]:
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
		# - app_title\s*=\s*   : matches 'app_title', optional spaces, '=', optional spaces
		# - ["\']              : matches opening quote (single or double)
		# - ([^"\']+)          : captures any characters except quotes (the app title)
		# - ["\']              : matches closing quote
		pattern = r'app_title\s*=\s*["\']([^"\']+)["\']'
		if match := re.search(pattern, content):
			return directory, match.group(1)

		reason_for_invalidation = (
			f"File {frappe.bold('hooks.py')} does not have {frappe.bold('app_title')} defined."
		)
		break

	frappe.throw(f"Not a valid Frappe App! {reason_for_invalidation}")
	raise  # for mypy: NoReturn


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


def _get_pyproject_from_commit(app_source: str, commit: str):
	repository_owner, repository, installation_id = frappe.db.get_value(
		"App Source", app_source, ["repository_owner", "repository", "github_installation_id"]
	)
	headers = get_auth_headers(installation_id)
	url = f"https://api.github.com/repos/{repository_owner}/{repository}/contents/pyproject.toml"

	response = requests.get(url, params={"ref": commit}, headers=headers)

	if response.status_code == 400:
		frappe.throw("Pyproject not found at this commit", frappe.ValidationError)

	if not response.ok:
		frappe.throw("Error fetching app info from github", frappe.ValidationError)

	content = b64decode(response.json().get("content", "")).decode()
	try:
		return tomli.loads(content)
	except tomli.TOMLDecodeError:
		frappe.throw("Invalid pyproject.toml file found in the app repository.", frappe.ValidationError)


def get_dependant_apps_with_versions(
	app_source: str,
	commit: str,
	cache: bool = True,
	raises: bool = True,
) -> AppDependencyFetch:
	"""Return app dependencies and Python version for a repository at a given commit."""
	cache_key = f"app_deps:{app_source}:{commit}"

	if cache and (cached := frappe.cache().get_value(cache_key)) is not None:
		return cached

	try:
		pyproject = _get_pyproject_from_commit(app_source, commit)
	except frappe.ValidationError as exc:
		if raises:
			raise exc

		dependency_data = AppDependencyFetch(frappe_dependencies={}, python_version=None)
	else:
		frappe_dependencies = pyproject.get("tool", {}).get("bench", {}).get("frappe-dependencies", {}).copy()
		dependency_data = AppDependencyFetch(
			frappe_dependencies=frappe_dependencies,
			python_version=pyproject.get("project", {}).get("requires-python"),
		)

	# In case of failures as well we want to cache the result to avoid hitting GitHub
	frappe.cache().set_value(cache_key, dependency_data, expires_in_sec=60 * 60)
	return dependency_data
