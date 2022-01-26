# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
import unittest


def create_test_frappe_version():
	"""Create test Frappe Version doc"""
	return frappe.get_doc(
		{"doctype": "Frappe Version", "name": "Version 13", "number": 13, "status": "Stable"}
	).insert(ignore_if_duplicate=True)


class TestFrappeVersion(unittest.TestCase):
	pass
