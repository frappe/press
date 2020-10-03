# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from ..bench.test_bench import create_test_bench
from ..frappe_app.test_frappe_app import create_test_frappe_app
from ..plan.test_plan import create_test_plan
from ..proxy_server.test_proxy_server import create_test_proxy_server
from ..release_group.test_release_group import create_test_release_group
from ..server.test_server import create_test_server
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


class TestSite(unittest.TestCase):
	"""Tests for Site Document methods."""

	def tearDown(self):
		frappe.db.rollback()

	def test_primary_domain_is_default_when_no_site_domain_exists(self):
		site = create_test_site("test-subdomain")
		self.assertEqual(site.primary_domain_name, site.name)
