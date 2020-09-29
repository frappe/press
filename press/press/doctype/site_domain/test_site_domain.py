# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe


def create_test_site_domain(site):
	"""Create test Site Domain doc."""
	return frappe.get_doc({
		"doctype": "Site Domain",
		"site": site,
		"domain": frappe.mock("url"),
		"status": "Active",
		"retry_count": 1,
		"dns_type": "A"
	}).insert(ignore_if_duplicate=True)


class TestSiteDomain(unittest.TestCase):
	pass
