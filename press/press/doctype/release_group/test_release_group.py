# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from .release_group import ReleaseGroup


def create_test_release_group(frappe_app: str) -> ReleaseGroup:
	"""Create Release Group doc."""
	name = frappe.mock("name")

	return frappe.get_doc(
		{
			"doctype": "Release Group",
			"name": f"Test Release Group{name}",
			"apps": [{"app": frappe_app,}],
			"enabled": True,
		}
	).insert(ignore_if_duplicate=True)


class TestReleaseGroup(unittest.TestCase):
	pass
