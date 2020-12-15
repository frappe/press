# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import patch

import frappe

from press.agent import Agent
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.frappe_app.test_frappe_app import create_test_frappe_app
from press.press.doctype.plan.test_plan import create_test_plan
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.site import Site


def create_test_site(subdomain: str, new: bool = False) -> Site:
	"""Create test Site doc."""
	proxy_server = create_test_proxy_server()
	server = create_test_server(proxy_server.name)
	frappe_app = create_test_frappe_app()

	release_group = create_test_release_group(frappe_app.name)
	release_group.create_deploy_candidate()

	plan = create_test_plan("Site")
	bench = create_test_bench(release_group.name, server.name)

	status = "Pending" if new else "Active"
	# on_update checks won't be triggered if not Active

	return frappe.get_doc(
		{
			"doctype": "Site",
			"status": status,
			"subdomain": subdomain,
			"server": server.name,
			"bench": bench.name,
			"plan": plan.name,
			"apps": [{"app": frappe_app.name}],
			"admin_password": "admin",
		}
	).insert(ignore_if_duplicate=True)


@patch.object(Agent, "create_agent_job")
class TestSite(unittest.TestCase):
	"""Tests for Site Document methods."""

	def tearDown(self):
		frappe.db.rollback()

	def test_host_name_updates_perform_checks_on_host_name(self, *args):
		"""Ensure update of host name triggers verification of host_name."""
		site = create_test_site("testsubdomain")
		site.host_name = "balu.codes"  # domain that doesn't exist
		self.assertRaises(frappe.exceptions.ValidationError, site.save)

	def test_site_has_default_site_domain_on_create(self, *args):
		"""Ensure site has default site domain on create."""
		site = create_test_site("testsubdomain")
		self.assertEqual(site.name, site.host_name)
		self.assertTrue(frappe.db.exists("Site Domain", {"domain": site.name}))

	def test_new_sites_set_host_name_in_site_config(self, *args):
		"""Ensure new sites set host_name in site config in f server."""
		with patch.object(Site, "_update_configuration") as mock_update_config:
			site = create_test_site("testsubdomain", new=True)
		mock_update_config.assert_called_with(
			{"host_name": f"https://{site.name}"}, save=False
		)
