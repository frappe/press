# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import patch

import frappe

from press.utils import log_error

from press.press.doctype.frappe_app.frappe_app import FrappeApp


def create_test_frappe_app(name=frappe.mock("name")) -> FrappeApp:
	"""
	Create test Frappe App doc.

	Github API call will not be made when creating the doc.
	"""

	def create_app_release(self):
		if not self.enabled:
			return
		try:
			hash = frappe.mock("name")
			if not frappe.db.exists("App Release", {"hash": hash, "app": self.name}):
				is_first_release = frappe.db.count("App Release", {"app": self.name}) == 0
				frappe.get_doc(
					{
						"doctype": "App Release",
						"app": self.name,
						"hash": hash,
						"message": "Test commit message",
						"author": frappe.mock("name"),
						"deployable": bool(is_first_release),
					}
				).insert()
		except Exception:
			log_error("App Release Creation Error", app=self.name)

	with patch.object(FrappeApp, "create_app_release", new=create_app_release):
		return frappe.get_doc(
			{
				"doctype": "Frappe App",
				"url": frappe.mock("url"),
				"scrubbed": "frappe",
				"branch": "master",
				"repo_owner": "frappe",
				"repo": "frappe",
				"name": f"Test Frappe App {name}",
				"skip_review": True,
				"enable_auto_deploy": True,
				"frappe": True,
			}
		).insert(ignore_if_duplicate=True)


class TestAppSource(unittest.TestCase):
	pass
