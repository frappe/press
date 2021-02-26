# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest


def create_test_team(email: str = frappe.mock("email")):
	"""Create test team doc."""
	return frappe.get_doc({"doctype": "Team", "name": email}).insert(
		ignore_if_duplicate=True
	)


class TestTeam(unittest.TestCase):
	pass
