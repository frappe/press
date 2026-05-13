# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing

import frappe
from frappe.tests.utils import FrappeTestCase

if typing.TYPE_CHECKING:
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.app_source.app_source import AppSource


def create_test_app_release(app_source: AppSource, hash: str | None = None) -> "AppRelease":
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


class TestAppRelease(FrappeTestCase):
	pass
