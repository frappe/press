# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from ..site.test_site import create_test_site
from .site_domain import SiteDomain

from ..tls_certificate.tls_certificate import TLSCertificate


def fake_tls_certificate():
	"""Fake tls certificate obtain call."""

	def obtain_certificate(self):
		return

	TLSCertificate.obtain_certificate = obtain_certificate


def create_test_site_domain(
	site: str, domain: str, status: str = "Active"
) -> SiteDomain:
	"""Create test Site Domain doc."""
	fake_tls_certificate()
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

	def setUp(self):
		self.site_subdomain = "testsubdomain"

	def test_set_host_name(self):
		"""Test set_host_name() method of Site doctype sets host_name property."""
		site = create_test_site(self.site_subdomain)
		domain_name = frappe.mock("domain_name")

		site_domain = create_test_site_domain(site.name, domain_name)
		site.set_host_name(site_domain.name)
		self.assertEqual(site.host_name, domain_name)

	def test_only_active_site_domain_can_be_primary(self):
		"""Ensure only active site domains can be primary."""
		site = create_test_site(self.site_subdomain)
		domain_name = frappe.mock("domain_name")

		site_domain = create_test_site_domain(
			site.name, domain_name, "Pending"
		)
		self.assertRaises(
			frappe.exceptions.LinkValidationError, site.set_host_name,
			site_domain.name
		)

	def test_default_host_name_is_site_subdomain(self):
		"""Ensure subdomain+domain is default primary host_name."""
		site = create_test_site(self.site_subdomain)
		self.assertEqual(site.host_name, site.name)

	def test_default_site_domain_cannot_be_deleted(self):
		"""Ensure default site domain for a site cannot be deleted."""
		site = create_test_site(self.site_subdomain)
		site_domain = frappe.get_doc({
			"doctype": "Site Domain",
			"site": site.name,
			"name": site.name
		})
		test_domain_name = frappe.mock("domain_name")
		test_domain = create_test_site_domain(site.name, test_domain_name)
		site.set_host_name(test_domain.name)
		self.assertRaises(Exception, site.remove_domain, site_domain.name)

	def test_only_site_domains_can_be_host_names(self):
		"""Ensure error is thrown if string other than site domain name is passed."""
		site = create_test_site(self.site_subdomain)
		self.assertRaises(
			frappe.exceptions.LinkValidationError, site.set_host_name,
			"site-domain-name-that-doesnt-exist"
		)

	def test_site_domain_for_other_site_cant_be_primary(self):
		"""Ensure host_name cannot be set to site domain for another site."""
		site1 = create_test_site(self.site_subdomain)
		site2 = create_test_site("testing-another")
		site_domain = create_test_site_domain(site2.name, "hellohello.com")
		self.assertRaises(
			frappe.exceptions.LinkValidationError, site1.set_host_name,
			site_domain.name
		)

	def test_set_host_name_removes_redirect_of_domain(self):
		"""Ensure set_host_name removes redirect of domain."""
		site = create_test_site(self.site_subdomain)
		site_domain = create_test_site_domain(site.name, "hellohello.com")
		site_domain.redirect_to_primary = True
		site_domain.save()
		site.set_host_name(site_domain.domain)
		site_domain.reload()
		self.assertFalse(site_domain.redirect_to_primary)

	def test_primary_domain_cannot_have_redirect_to_primary_checked(self):
		"""Ensure primary domain cannot have redirect_to_primary checked."""
		site = create_test_site(self.site_subdomain)
		site_domain = create_test_site_domain(site.name, "hellohello.com")
		site.set_host_name(site_domain.domain)
		site_domain.reload()
		site_domain.redirect_to_primary = True
		self.assertRaises(frappe.exceptions.ValidationError, site_domain.save)
