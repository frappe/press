# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from ..site.test_site import create_test_site
from .site_domain import SiteDomain


def create_test_site_domain(
	site: str, domain: str, status: str = "Active"
) -> SiteDomain:
	"""Create test Site Domain doc."""
	return frappe.get_doc({
		"doctype": "Site Domain",
		"site": site,
		"domain": domain,
		"status": status,
		"retry_count": 1,
		"dns_type": "A"
	}).insert(ignore_if_duplicate=True)


class TestSiteDomain(unittest.TestCase):
	"""Tests for Site Domain Document methods."""

	def setUp(self):
		self.site = create_test_site("testing")
		self.domain_name = frappe.mock("domain_name")

	def tearDown(self):
		frappe.db.rollback()

	def test_set_host_name(self):
		"""Test set_host_name() method of Site doctype sets host_name property."""
		site_domain = create_test_site_domain(self.site.name, self.domain_name)
		self.site.set_host_name(site_domain.name)
		self.assertEqual(self.site.host_name, self.domain_name)

	def test_only_active_site_domain_can_be_primary(self):
		"""Ensure active site domains can be primary."""
		site_domain = create_test_site_domain(
			self.site.name, self.domain_name, "Pending"
		)
		self.assertRaises(
			frappe.exceptions.LinkValidationError, self.site.set_host_name,
			site_domain.name
		)
