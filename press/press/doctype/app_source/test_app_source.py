# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import frappe
import unittest

from unittest.mock import patch
from press.press.doctype.app.app import App
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.team.test_team import create_test_team


@patch.object(AppSource, "create_release", create_test_app_release)
def create_test_app_source(
	version: str,
	app: App,
	repository_url=None,
	branch: str = "master",
	team: str = None,
) -> AppSource:
	"""
	Create test app source for app with given version.

	Also creates app release without github api call.
	"""
	if not repository_url:
		repository_url = frappe.mock("url")
	team = team if team else create_test_team().name
	return app.add_source(version, repository_url, branch, team)


class TestAppSource(unittest.TestCase):
	pass
