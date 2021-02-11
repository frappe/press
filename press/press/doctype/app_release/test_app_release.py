# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from press.press.doctype.app_source.app_source import AppSource


def create_test_app_release(app_source: AppSource):
	"""Create test app release given App source."""
	frappe.get_doc(
		{
			"doctype": "App Release",
			"app": app_source.app,
			"source": app_source.name,
			"hash": "sdf89s",
			"message": "Test Msg",
			"author": "Test Author",
			"deployable": True,
		}
	).insert(ignore_if_duplicate=True)


class TestAppRelease(unittest.TestCase):
	pass
