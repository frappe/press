# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest


def create_test_frappe_version():
	"""Create test Frappe Version doc"""
	frappe_version = frappe.get_doc(
		{"doctype": "Frappe Version", "name": "Version 13", "number": 13, "status": "Stable"}
	).insert(ignore_if_duplicate=True)
	frappe_version.reload()
	return frappe_version


class TestFrappeVersion(unittest.TestCase):
	pass
