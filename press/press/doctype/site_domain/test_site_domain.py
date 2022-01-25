# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import Mock, call, patch

import frappe

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.site import (
	process_rename_site_job_update,
	site_cleanup_after_archive,
)
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


@patch.object(AgentJob, "after_insert", new=Mock())
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
		default_domain = frappe.get_doc(
			{"doctype": "Site Domain", "site": site.name, "name": site.name}
		)
		site_domain2 = create_test_site_domain(site.name, "hellohello.com")
		site.set_host_name(site_domain2.name)
		self.assertRaises(Exception, site.remove_domain, default_domain.name)

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
		mock_setup_redirects.assert_called_with(site.name, [site_domain.name], site.name)

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
		mock_setup_redirects.assert_called_with(site.name, [site_domain.name], site.name)

	def test_site_archive_removes_all_site_domains(self):
		"""Ensure site archive removes all site domains."""
		site = create_test_site(self.site_subdomain)
		site_domain = create_test_site_domain(site.name, "hellohello.com")

		site.archive()
		with patch("press.press.doctype.site.site.frappe.delete_doc") as mock_frappe_del:
			site_cleanup_after_archive(site.name)
		mock_frappe_del.assert_has_calls(
			[call("Site Domain", site.name), call("Site Domain", site_domain.name)],
			any_order=True,
		)

	def test_tls_certificate_isnt_created_for_default_domain(self):
		"""Ensure TLS Certificate isn't created for default domain."""
		with patch.object(SiteDomain, "create_tls_certificate") as mock_create_tls:
			create_test_site(self.site_subdomain)
		mock_create_tls.assert_not_called()

	def test_remove_host_called_for_site_domains_on_trash(self):
		"""Ensure remove host agent job is created when site domain is deleted."""
		site = create_test_site(self.site_subdomain)
		site_domain = create_test_site_domain(site.name, "hellohello.com")
		site.add_domain_to_config(site_domain.name)

		with patch.object(SiteDomain, "create_remove_host_agent_request") as mock_remove_host:
			site_domain.on_trash()
		mock_remove_host.assert_called()

	def test_remove_host_called_for_default_domain_only_on_redirect(self):
		"""
		Ensure remove host agent job isn't always created for default domain.

		Default domain host should be removed only if redirect exists.
		"""
		site = create_test_site(self.site_subdomain)
		def_domain = frappe.get_doc("Site Domain", site.name)
		site_domain = create_test_site_domain(site.name, "hellohello.com")
		site.set_host_name(site_domain.name)

		with patch.object(SiteDomain, "create_remove_host_agent_request") as mock_remove_host:
			# fake archive
			site.db_set("status", "Archived")
			def_domain.on_trash()
		mock_remove_host.assert_not_called()

		def_domain.setup_redirect()
		with patch.object(SiteDomain, "create_remove_host_agent_request") as mock_remove_host:
			def_domain.on_trash()
		mock_remove_host.assert_called()

	def test_domains_other_than_default_get_sent_for_rename(self):
		"""Ensure site domains are sent for rename."""
		site = create_test_site(self.site_subdomain)
		site_domain1 = create_test_site_domain(site.name, "sitedomain1.com")
		site_domain2 = create_test_site_domain(site.name, "sitedomain2.com")
		new_name = "new-name.fc.dev"
		with patch.object(Agent, "rename_upstream_site") as mock_rename_upstream_site:
			site.rename(new_name)
		args, kwargs = mock_rename_upstream_site.call_args
		from collections import Counter

		self.assertEqual(Counter(args[-1]), Counter([site_domain1.name, site_domain2.name]))

	def test_site_rename_doesnt_update_host_name_for_custom_domain(self):
		"""Ensure site configuration isn't updated after rename when custom domain is host_name."""
		site = create_test_site("old-name")
		site_domain1 = create_test_site_domain(site.name, "sitedomain1.com")
		site.set_host_name(site_domain1.name)
		new_name = "new-name.fc.dev"
		site.rename(new_name)

		rename_job = frappe.get_last_doc("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_job = frappe.get_last_doc(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)
		rename_job.status = "Success"
		rename_upstream_job.status = "Success"
		rename_job.save()
		rename_upstream_job.save()

		process_rename_site_job_update(rename_job)
		site = frappe.get_doc("Site", new_name)
		if site.configuration[0].key == "host_name":
			config_host = site.configuration[0].value
		self.assertEqual(config_host, f"https://{site_domain1.name}")

	def test_primary_domain_cannot_be_deleted(self):
		site = create_test_site("old-name")
		site_domain = create_test_site_domain(site.name, "sitedomain1.com")
		site.add_domain_to_config(site_domain.name)

		site.set_host_name(site_domain.name)

		self.assertRaises(frappe.exceptions.LinkExistsError, site_domain.delete)
		self.assertTrue(frappe.db.exists("Site Domain", {"name": site_domain.name}))
