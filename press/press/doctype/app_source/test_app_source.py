# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import patch

import frappe

from press.press.doctype.app.app import App
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.release_group.release_group import ReleaseGroup


def create_test_app_source(release_group: ReleaseGroup, app: App) -> AppSource:
	"""Create test app source for app and release group."""
	with patch.object(AppSource, "after_insert"):
		return app.add_source(release_group.version, frappe.mock("url"), "master")


class TestAppSource(unittest.TestCase):
	pass
