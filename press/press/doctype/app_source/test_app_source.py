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


def github_not_found_response(message: str) -> Mock:
	return Mock(status_code=404, text=f'{{"message": "{message}"}}')


class TestAppSource(FrappeTestCase):
	def create_app(self, name: str, title: str):
		app: App = frappe.get_doc({"doctype": "App", "name": name, "title": title})
		app.insert(ignore_if_duplicate=True)
		return app

	def create_hrms_source(self) -> AppSource:
		return self.create_app("hrms", "HRMS").add_source(
			frappe_version="Nightly",
			repository_url="https://github.com/frappe/hrms",
			branch="develop",
			team=create_test_team().name,
		)

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

	@patch.object(AppSource, "after_insert", new=Mock())
	def test_sync_versions_replaces_versions_with_what_the_repo_currently_supports(self):
		team_name = create_test_team().name
		app: App = self.create_app("hrms", "HRMS")
		source = app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/frappe/hrms",
			branch="develop",
			team=team_name,
		)
		source.append("versions", {"version": "Version 13"})
		source.save()

		with patch(
			"press.press.doctype.app_source.app_source.get_repo_app_info",
			return_value={"frappe_version": "Version 15", "title": "HRMS"},
		):
			source.sync_versions()

		self.assertEqual([row.version for row in source.versions], ["Version 15"])

	@patch.object(AppSource, "after_insert", new=Mock())
	def test_poll_of_deleted_branch_sets_branch_deleted_and_leaves_source_installed(self):
		source = self.create_hrms_source()

		source.set_poll_failed(github_not_found_response("Branch not found"))

		self.assertTrue(source.branch_deleted)
		self.assertFalse(source.uninstalled)

	@patch.object(AppSource, "after_insert", new=Mock())
	def test_poll_of_inaccessible_repository_sets_uninstalled_and_not_branch_deleted(self):
		source = self.create_hrms_source()

		source.set_poll_failed(github_not_found_response("Not Found"))

		self.assertFalse(source.branch_deleted)
		self.assertTrue(source.uninstalled)

	@patch.object(AppSource, "after_insert", new=Mock())
	def test_branch_deleted_is_false_while_the_last_poll_succeeded(self):
		source = self.create_hrms_source()
		source.last_github_response = '{"message": "Branch not found"}'
		source.last_github_poll_failed = False

		self.assertFalse(source.branch_deleted)
