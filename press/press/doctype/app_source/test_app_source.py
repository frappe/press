# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

import typing
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.team.test_team import create_test_team
from press.utils import get_current_team

if typing.TYPE_CHECKING:
	from press.press.doctype.app.app import App


@patch.object(AppSource, "create_release", create_test_app_release)
def create_test_app_source(
	version: str,
	app: App,
	repository_url=None,
	branch: str = "master",
	team: str | None = None,
) -> AppSource:
	"""
	Create test app source for app with given version.

	Also creates app release without github api call.
	"""
	if not repository_url:
		repository_url = "https://github.com/frappe/erpnext"
	team = team or get_current_team()
	return app.add_source(repository_url=repository_url, branch=branch, frappe_version=version, team=team)


class TestAppSource(FrappeTestCase):
	def create_app(self, name: str, title: str):
		app: App = frappe.get_doc({"doctype": "App", "name": name, "title": title})
		app.insert(ignore_if_duplicate=True)
		return app

	def tearDown(self):
		frappe.db.rollback()

	@patch.object(AppSource, "after_insert", new=Mock())
	def test_validate_dependant_apps(self):
		team_name = create_test_team().name
		app: App = self.create_app("hrms", "HRMS")
		source = app.add_source(
			frappe_version="Nightly",
			repository_url="https://github.com/frappe/hrms",
			branch="develop",
			team=team_name,
		)

		for req_app in source.required_apps:
			self.assertEqual("https://github.com/frappe/erpnext", req_app.repository_url)

	# -----------------------------------------------------------------------
	# validate_source_signature
	# -----------------------------------------------------------------------

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_validate_source_signature_throws_on_duplicate(self):
		"""validate_source_signature raises when the same repo+branch+team
		combination is already stored in the database."""
		team_name = create_test_team().name
		app = self.create_app("erpnext2", "ERPNext")
		# Insert the first source directly so it exists in DB
		first = frappe.get_doc(
			{
				"doctype": "App Source",
				"app": app.name,
				"versions": [{"version": "Version 14"}],
				"repository_url": "https://github.com/frappe/erpnext",
				"branch": "version-14",
				"team": team_name,
			}
		).insert()
		# Build a second doc with the same signature (different name) and call
		# validate_source_signature — it should throw
		second = frappe.get_doc(
			{
				"doctype": "App Source",
				"app": app.name,
				"versions": [{"version": "Version 15"}],
				"repository_url": "https://github.com/frappe/erpnext",
				"branch": "version-14",
				"team": team_name,
			}
		)
		# Give it a distinct name so the "name != self.name" check in
		# validate_source_signature does not short-circuit
		second.name = first.name + "-dup"
		with self.assertRaises(frappe.ValidationError):
			second.validate_source_signature()

	# -----------------------------------------------------------------------
	# validate_duplicate_versions
	# -----------------------------------------------------------------------

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_validate_duplicate_versions_throws(self):
		"""AppSource.versions should not contain the same version twice."""
		team_name = create_test_team().name
		app = self.create_app("myapp", "My App")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/frappe/myapp",
			branch="develop",
			team=team_name,
		)
		# Manually add a duplicate version row
		source.append("versions", {"version": "Version 14"})
		with self.assertRaises(frappe.ValidationError):
			source.validate_duplicate_versions()

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_validate_duplicate_versions_passes_unique_versions(self):
		team_name = create_test_team().name
		app = self.create_app("myapp2", "My App 2")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/frappe/myapp2",
			branch="main",
			team=team_name,
		)
		source.append("versions", {"version": "Version 15"})
		# Should not raise
		source.validate_duplicate_versions()

	# -----------------------------------------------------------------------
	# set_required_apps
	# -----------------------------------------------------------------------

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_set_required_apps_parses_full_owner_repo_format(self):
		team_name = create_test_team().name
		app = self.create_app("myapp3", "My App 3")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/frappe/myapp3",
			branch="main",
			team=team_name,
		)
		source.required_apps = []
		source.set_required_apps("frappe/erpnext, frappe/hrms")
		repo_urls = [r.repository_url for r in source.required_apps]
		self.assertIn("https://github.com/frappe/erpnext", repo_urls)
		self.assertIn("https://github.com/frappe/hrms", repo_urls)

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_set_required_apps_skips_already_added_urls(self):
		"""Duplicate URLs should not be added again."""
		team_name = create_test_team().name
		app = self.create_app("myapp4", "My App 4")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/frappe/myapp4",
			branch="main",
			team=team_name,
		)
		source.required_apps = []
		source.set_required_apps("frappe/erpnext")
		initial_count = len(source.required_apps)
		# Call again with same app
		source.set_required_apps("frappe/erpnext")
		self.assertEqual(len(source.required_apps), initial_count)

	# -----------------------------------------------------------------------
	# Task 4: Private repository URL generation (tenancy safeguards)
	# -----------------------------------------------------------------------

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_get_repo_url_returns_plain_url_for_public_repo(self):
		"""When no github_installation_id is set, get_repo_url() returns the
		plain repository_url without an auth token embedded."""
		team_name = create_test_team().name
		app = self.create_app("publicapp", "Public App")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/frappe/publicapp",
			branch="main",
			team=team_name,
		)
		source.github_installation_id = None
		result = source.get_repo_url()
		self.assertEqual(result, "https://github.com/frappe/publicapp")
		self.assertNotIn("x-access-token", result)

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_get_repo_url_embeds_token_for_private_repo(self):
		"""When github_installation_id is set, get_repo_url() returns an HTTPS
		URL with the GitHub App access token embedded for cloning private repos."""

		team_name = create_test_team().name
		app = self.create_app("privateapp", "Private App")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/myorg/privateapp",
			branch="main",
			team=team_name,
		)
		source.github_installation_id = "fake-installation-123"

		with patch(
			"press.press.doctype.app_source.app_source.get_access_token",
			return_value="ghp_faketoken",
		):
			result = source.get_repo_url()

		self.assertIn("x-access-token:ghp_faketoken", result)
		self.assertIn("github.com/myorg/privateapp", result)

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_get_repo_url_raises_when_token_fetch_fails(self):
		"""If get_access_token returns None for a private source, get_repo_url()
		raises an exception (prevents a silent clone with no credentials)."""
		team_name = create_test_team().name
		app = self.create_app("privateapp2", "Private App 2")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/myorg/privateapp2",
			branch="main",
			team=team_name,
		)
		source.github_installation_id = "bad-installation"

		with patch(
			"press.press.doctype.app_source.app_source.get_access_token",
			return_value=None,
		):
			self.assertRaisesRegex(
				Exception,
				"App installation token could not be fetched",
				source.get_repo_url,
			)

	@patch.object(AppSource, "after_insert", new=Mock())
	@patch.object(AppSource, "on_update", new=Mock())
	def test_get_access_token_falls_back_to_press_settings_for_public_source(self):
		"""For a source without a github_installation_id, get_access_token()
		returns the global token from Press Settings (public source flow)."""
		team_name = create_test_team().name
		app = self.create_app("pubsrc", "Pub Src")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/frappe/pubsrc",
			branch="main",
			team=team_name,
		)
		source.github_installation_id = None

		with patch(
			"frappe.get_value",
			return_value="ghs_global_token",
		):
			token = source.get_access_token()

		self.assertEqual(token, "ghs_global_token")
