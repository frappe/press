# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe

from press.press.doctype.app.app import App
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.utils import get_current_team


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
	team = team or get_current_team()
	return app.add_source(version, repository_url, branch, team)


class TestAppSource(unittest.TestCase):
	pass
