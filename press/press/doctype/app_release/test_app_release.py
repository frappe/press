# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import unittest
import typing
import frappe

from press.press.doctype.app_source.app_source import AppSource

if typing.TYPE_CHECKING:
	from press.press.doctype.app_release.app_release import AppRelease


def create_test_app_release(app_source: AppSource, hash: str = None) -> AppRelease:
	"""Create test app release given App source."""
	hash = hash or frappe.mock("sha1")
	app_release = frappe.get_doc(
		{
			"doctype": "App Release",
			"app": app_source.app,
			"source": app_source.name,
			"hash": hash,
			"message": "Test Msg",
			"author": "Test Author",
			"deployable": True,
			"status": "Approved",
		}
	).insert(ignore_if_duplicate=True)
	app_release.reload()
	return app_release


class TestAppRelease(unittest.TestCase):
	pass
