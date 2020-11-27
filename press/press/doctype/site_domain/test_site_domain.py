# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import Mock, call, patch

import frappe

from press.agent import Agent
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_domain.site_domain import SiteDomain
from press.press.doctype.tls_certificate.tls_certificate import TLSCertificate


def create_test_site_domain(
	site: str, domain: str, status: str = "Active"
) -> SiteDomain:
	"""Create test Site Domain doc."""
	with patch.object(TLSCertificate, "obtain_certificate"):
		return frappe.get_doc(
			{
				"doctype": "Site Domain",
				"site": site,
				"domain": domain,
				"status": status,
				"retry_count": 1,
				"dns_type": "A",
			}
		).insert(ignore_if_duplicate=True)


@patch.object(Agent, "create_agent_job", new=Mock(return_value={"job": 1}))
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

		site_domain = create_test_site_domain(site.name, domain_name, "Pending")
		self.assertRaises(
			frappe.exceptions.LinkValidationError, site.set_host_name, site_domain.name
		)

	def test_default_host_name_is_site_subdomain(self):
		"""Ensure subdomain+domain is default primary host_name."""
		site = create_test_site(self.site_subdomain)
		self.assertEqual(site.host_name, site.name)

	def test_default_site_domain_cannot_be_deleted(self):
		"""Ensure default site domain for a site cannot be deleted."""
		site = create_test_site(self.site_subdomain)
		site_domain = frappe.get_doc(
			{"doctype": "Site Domain", "site": site.name, "name": site.name}
		)
		test_domain_name = frappe.mock("domain_name")
		test_domain = create_test_site_domain(site.name, test_domain_name)
		site.set_host_name(test_domain.name)
		self.assertRaises(Exception, site.remove_domain, site_domain.name)

	def test_only_site_domains_can_be_host_names(self):
		"""Ensure error is thrown if string other than site domain name is passed."""
		site = create_test_site(self.site_subdomain)
		self.assertRaises(
			frappe.exceptions.LinkValidationError,
			site.set_host_name,
			"site-domain-name-that-doesnt-exist",
		)

	def test_site_domain_for_other_site_cant_be_primary(self):
		"""Ensure host_name cannot be set to site domain for another site."""
		site1 = create_test_site(self.site_subdomain)
		site2 = create_test_site("testing-another")
		site_domain = create_test_site_domain(site2.name, "hellohello.com")
		self.assertRaises(
			frappe.exceptions.LinkValidationError, site1.set_host_name, site_domain.name
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

	def test_all_redirects_updated_on_updating_host_name(self):
		"""
		Ensure all redirects are updated when host_name of site is updated.

		(At least agent method is called.)
		"""
		site = create_test_site(self.site_subdomain)
		site_domain1 = create_test_site_domain(site.name, "sitedomain1.com")
		site_domain2 = create_test_site_domain(site.name, "sitedomain2.com")
		site_domain3 = create_test_site_domain(site.name, "sitedomain3.com")

		site_domain2.setup_redirect()
		site_domain3.setup_redirect()

		with patch.object(Agent, "setup_redirects") as mock_set_redirects:
			site.set_host_name(site_domain1.name)

		mock_set_redirects.assert_called()

	def test_setup_redirect_updates_redirect_in_agent(self):
		"""
		Ensure setting redirect_to_primary in doc updates agent.

		(At least agent method is called.)
		"""
		site = create_test_site(self.site_subdomain)
		site_domain = create_test_site_domain(site.name, "hellohello.com")

		with patch.object(Agent, "setup_redirects") as mock_setup_redirects:
			site_domain.setup_redirect()
		mock_setup_redirects.assert_called_with(
			site.name, [site_domain.name], site.name
		)

	def test_remove_redirect_updates_redirect_in_agent(self):
		"""
		Ensure removing redirect_to_primary in doc updates agent.

		(At least agent method is called.)
		"""
		site = create_test_site(self.site_subdomain)
		site_domain = create_test_site_domain(site.name, "hellohello.com")
		site_domain.setup_redirect()

		with patch.object(Agent, "remove_redirects") as mock_remove_redirects:
			site_domain.remove_redirect()
		mock_remove_redirects.assert_called_with(site.name, [site_domain.name])

	def test_making_doc_with_redirect_to_primary_true_updates_agent(self):
		"""Ensure agent is updated when redirected site domain is created."""
		site = create_test_site(self.site_subdomain)
		with patch.object(Agent, "setup_redirects") as mock_setup_redirects:
			site_domain = frappe.get_doc(
				{
					"doctype": "Site Domain",
					"site": site.name,
					"domain": "hellohello.com",
					"status": "Active",
					"retry_count": 1,
					"dns_type": "A",
					"redirect_to_primary": True,
				}
			).insert(ignore_if_duplicate=True)
		mock_setup_redirects.assert_called_with(
			site.name, [site_domain.name], site.name
		)

	def test_redirect_is_deleted_when_site_domain_is_deleted(self):
		"""Ensure redirect in agent is deleted when site domain doc is deleted."""
		site = create_test_site(self.site_subdomain)
		site_domain = create_test_site_domain(site.name, "hellohello.com")
		site_domain.setup_redirect()

		with patch.object(Agent, "remove_redirects") as mock_remove_redirects:
			site_domain.delete()

		# override eq because id of object is different
		def __eq__(self, other):
			return (
				self.name == other.name
				and self.domain == other.domain
				and self.site == other.site
			)

		with patch.object(SiteDomain, "__eq__", new=__eq__):
			mock_remove_redirects.assert_called_with(site.name, [site_domain.name])
		frappe.delete_doc(site_domain.doctype, site_domain.name, force=True)
		frappe.delete_doc("Site Domain", site.name, force=True)
		frappe.delete_doc("Site", site.name, force=True)
