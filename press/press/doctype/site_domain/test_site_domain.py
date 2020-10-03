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

	def test_only_one_primary_site_domain_for_site(self):
		"""Ensure only one primary domain for a site is possible."""
		site = create_test_site("test-subdomain-b")
		site_domain = create_test_site_domain(site.name, "domain-a")
		site_domain2 = create_test_site_domain(site.name, "domain-b")
		site_domain.primary = True
		site_domain.save()
		site_domain2.primary = True
		self.assertRaises(
			frappe.exceptions.ValidationError, site_domain2.save
		)

	def test_primary_domain_is_site_domain_when_checked_primary(self):
		"""Ensure primary domain is primary Site Domain if available."""
		site = create_test_site("testingbalu")
		self.assertEqual(site.primary_domain_name, site.name)
		site_domain = create_test_site_domain(site.name, "test-domain")
		site_domain.primary = True
		site_domain.save()
		self.assertEqual(site.primary_domain_name, site_domain.name)
		site_domain.primary = False
		site_domain.save()
		self.assertEqual(site.primary_domain_name, site.name)

	def test_primary_domain_name_property_works_for_multiple_site_domains(
		self
	):
		"""
		Check primary_domain_name for multiple domains.

		Ensure primary_domain_name gives single primary value when multiple
		site domains for same site exists.
		"""
		site = create_test_site("testingbalu")
		site_domain = create_test_site_domain(site.name, "domain-a")
		site_domain.primary = True
		site_domain.save()
		site_domain2 = create_test_site_domain(site.name, "domain-b")
		self.assertEqual(site.primary_domain_name, site_domain.name)
		site_domain.primary = False
		site_domain.save()
		self.assertEqual(site.primary_domain_name, site.name)
		site_domain2.primary = True
		site_domain2.save()
		self.assertEqual(site.primary_domain_name, site_domain2.name)

	def test_primary_domain_when_site_domain_for_some_other_site_exists(
		self
	):
		"""Ensure primary domain works when multiple sites for site domains exist."""
		site = create_test_site("site-a")
		site2 = create_test_site("site-b")
		site_domain = create_test_site_domain(site.name, "domain-a")
		site2_domain = create_test_site_domain(site2.name, "domain-b")
		site2_domain.primary = True
		site2_domain.save()
		self.assertEqual(site.primary_domain_name, site.name)
		self.assertEqual(site2.primary_domain_name, site2_domain.name)

		site_domain.primary = True
		site_domain.save()
		self.assertEqual(site.primary_domain_name, site_domain.name)
		self.assertEqual(site2.primary_domain_name, site2_domain.name)
