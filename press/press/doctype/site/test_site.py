# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from press.agent import Agent

from ..bench.test_bench import create_test_bench
from ..frappe_app.test_frappe_app import create_test_frappe_app
from ..plan.test_plan import create_test_plan
from ..proxy_server.test_proxy_server import create_test_proxy_server
from ..release_group.test_release_group import create_test_release_group
from ..server.test_server import create_test_server
from ..site_domain.test_site_domain import create_test_site_domain
from .site import Site


def create_test_site(subdomain: str) -> Site:
	"""Create test Site doc."""
	frappe.set_user("Administrator")

	proxy_server = create_test_proxy_server()
	server = create_test_server(proxy_server.name)
	frappe_app = create_test_frappe_app()

	release_group = create_test_release_group(frappe_app.name)
	release_group.create_deploy_candidate()

	plan = create_test_plan()
	bench = create_test_bench(release_group.name, server.name)

	return frappe.get_doc({
		"doctype": "Site",
		"status": "Active",
		"subdomain": subdomain,
		"server": server.name,
		"bench": bench.name,
		"plan": plan.name,
		"apps": [{
			"app": frappe_app.name
		}],
		"admin_password": "admin"
	}).insert(ignore_if_duplicate=True)


def fake_agent_job():
	"""Monkey patch Agent Job doctype methods to work in isolated tests."""

	def create_agent_job(
		self,
		job_type,
		path,
		data=None,
		files=None,
		method="POST",
		bench=None,
		site=None,
		upstream=None,
		host=None,
	):
		return {"job": 1}

	Agent.create_agent_job = create_agent_job


class TestSite(unittest.TestCase):
	"""Tests for Site Document methods."""

	def setUp(self):
		self.subdomain = "testsubdomain"
		fake_agent_job()

	def tearDown(self):
		frappe.db.rollback()

	# TODO: remove this test when implementing with defautl site domain doc <01-10-20, Balamurali M> #
	def test_primary_domain_is_default_when_no_site_domain_exists(self):
		site = create_test_site(self.subdomain)
		self.assertEqual(site.primary_domain_name, site.name)

	def test_primary_domain_is_site_domain_when_checked_primary(self):
		"""Ensure primary domain is primary Site Domain."""
		site = create_test_site(self.subdomain)
		self.assertEqual(site.primary_domain_name, site.name)
		site_domain = create_test_site_domain(site.name)
		site_domain.primary = True
		site_domain.save()
		self.assertNotEqual(site.primary_domain_name, site.name)
		self.assertEqual(site.primary_domain_name, site_domain.name)
		site_domain.primary = False
		site_domain.save()
		self.assertEqual(site.primary_domain_name, site.name)
		self.assertNotEqual(site.primary_domain_name, site_domain.name)

	def test_primary_domain_name_property_works_for_multiple_site_domains(
		self
	):
		"""
		Check primary_domain_name for multiple domains.

		Ensure primary_domain_name gives single primary value when multiple
		site domains for same site exists.
		"""
		site = create_test_site(self.subdomain)
		site_domain = create_test_site_domain(site.name)
		site_domain.primary = True
		site_domain.save()
		site_domain_2 = create_test_site_domain(site.name)
		self.assertNotEqual(site.primary_domain_name, site.name)
		self.assertEqual(site.primary_domain_name, site_domain.name)
		site_domain.primary = False
		site_domain.save()
		self.assertEqual(site.primary_domain_name, site.name)
		self.assertNotEqual(site.primary_domain_name, site_domain.name)
		site_domain_2.primary = True
		site_domain_2.save()
		self.assertEqual(site.primary_domain_name, site_domain_2.name)

	def test_primary_domain_when_site_domain_for_some_other_site_exists(
		self
	):
		# TODO: commit previous tests before implementing <01-10-20, Balamurali M> #
		# TODO: need mocks to implement <01-10-20, Balamurali M> #
		pass

	# TODO: test for default site domain created when site created <01-10-20, Balamurali M> #
