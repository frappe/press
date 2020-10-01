# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from .bench import Bench


def create_test_bench(release_group: str, server: str) -> Bench:
	"""Create test Bench doc."""
	name = frappe.mock("name")
	return frappe.get_doc({
		"name": f"Test Bench{name}",
		"doctype": "Bench",
		"status": "Active",
		"workers": 1,
		"gunicorn_workers": 2,
		"group": release_group,
		"server": server
	}).insert(ignore_if_duplicate=True)


class TestBench(unittest.TestCase):
	pass
