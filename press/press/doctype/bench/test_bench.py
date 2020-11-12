# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import Mock, patch

import frappe

from press.agent import Agent
from press.press.doctype.bench.bench import Bench


def create_test_bench(release_group: str, server: str) -> Bench:
	"""
	Create test Bench doc.

	API call to agent will be faked when creating the doc.
	"""

	with patch.object(
		Agent, "create_agent_job", new=Mock(return_value={"job": 1})
	):
		name = frappe.mock("name")
		return frappe.get_doc(
			{
				"name": f"Test Bench{name}",
				"doctype": "Bench",
				"status": "Active",
				"workers": 1,
				"gunicorn_workers": 2,
				"group": release_group,
				"server": server,
			}
		).insert(ignore_if_duplicate=True)


class TestBench(unittest.TestCase):
	pass
