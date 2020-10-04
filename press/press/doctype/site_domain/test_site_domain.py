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

	def tearDown(self):
		frappe.db.rollback()

	def test_set_host_name(self):
		"""Test set_host_name() method of Site doctype sets host_name property."""
		site = create_test_site("testing")
		domain_name = frappe.mock("domain_name")

		site_domain = create_test_site_domain(site.name, domain_name)
		site.set_host_name(site_domain.name)
		self.assertEqual(site.host_name, domain_name)

	def test_only_active_site_domain_can_be_primary(self):
		"""Ensure active site domains can be primary."""
		site = create_test_site("testing")
		domain_name = frappe.mock("domain_name")

		site_domain = create_test_site_domain(
			site.name, domain_name, "Pending"
		)
		self.assertRaises(
			frappe.exceptions.LinkValidationError, site.set_host_name,
			site_domain.name
		)

	def test_default_host_name_is_site_subdomain(self):
		"""Ensure subdomain+domain is default primary host_name"""
		site = create_test_site("testing")
		self.assertEqual(site.host_name, site.name)
