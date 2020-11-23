# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe


def create_test_plan(document_type: str):
	"""Create test Plan doc."""
	name = frappe.mock("name")
	return frappe.get_doc(
		{
			"name": f"Test 10 dollar plan {name}",
			"doctype": "Plan",
			"document_type": document_type,
			"price_inr": 750.0,
			"price_usd": 10.0,
			"period": 30,
		}
	).insert(ignore_if_duplicate=True)


class TestPlan(unittest.TestCase):
	pass
