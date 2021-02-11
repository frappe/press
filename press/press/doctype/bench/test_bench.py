# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from press.press.doctype.bench.bench import Bench


def create_test_bench(release_group: str, server: str) -> Bench:
	"""
	Create test Bench doc.

	API call to agent will be faked when creating the doc.
	"""
	name = frappe.mock("name")
	candidate = frappe.get_last_doc("Deploy Candidate", {"group": release_group})
	candidate.docker_image = frappe.mock("url")
	candidate.save()
	return frappe.get_doc(
		{
			"name": f"Test Bench{name}",
			"doctype": "Bench",
			"status": "Active",
			"background_workers": 1,
			"gunicorn_workers": 2,
			"group": release_group,
			"candidate": candidate.name,
			"server": server,
		}
	).insert(ignore_if_duplicate=True)


class TestBench(unittest.TestCase):
	pass
