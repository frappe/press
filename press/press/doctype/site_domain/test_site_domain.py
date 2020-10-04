# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from ..site.test_site import create_test_site
from .site_domain import SiteDomain


def create_test_site_domain(site: str, domain: str) -> SiteDomain:
	"""Create test Site Domain doc."""
	return frappe.get_doc({
		"doctype": "Site Domain",
		"site": site,
		"domain": domain,
		"status": "Active",
		"retry_count": 1,
		"dns_type": "A"
	}).insert(ignore_if_duplicate=True)


class TestSiteDomain(unittest.TestCase):
	"""Tests for Site Domain Document methods."""

	def tearDown(self):
		frappe.db.rollback()
