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

		app: App = self.create_app("lms", "LMS")
		source = app.add_source(
			frappe_version="Nightly",
			repository_url="https://github.com/frappe/lms",
			branch="develop",
			team=team_name,
		)

		self.assertEqual([], source.required_apps)
