# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import patch

import frappe

from press.press.doctype.app.app import App
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.app_release.test_app_release import create_test_app_release


@patch.object(AppSource, "create_release", create_test_app_release)
def create_test_app_source(version: str, app: App) -> AppSource:
	"""
	Create test app source for app with given version.

	Also creates app release without github api call.
	"""
	return app.add_source(version, frappe.mock("url"), "master", "Administrator")


class TestAppSource(unittest.TestCase):
	pass
