# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest


def create_test_app_release(
	app: str, app_source: str,
):
	frappe.get_doc(
		{
			"doctype": "App Release",
			"app": app,
			"source": app_source,
			"hash": "sdf89s",
			"message": "Test Msg",
			"author": "Test Author",
			"deployable": True,
		}
	).insert(ignore_if_duplicate=True)


class TestAppRelease(unittest.TestCase):
	pass
