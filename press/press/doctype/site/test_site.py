# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import patch, Mock

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.frappe_app.test_frappe_app import create_test_frappe_app
from press.press.doctype.plan.test_plan import create_test_plan
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.site import Site
from press.press.doctype.site.site import process_rename_site_job_update


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


@patch.object(AgentJob, "after_insert", new=Mock())
class TestSite(unittest.TestCase):
	"""Tests for Site Document methods."""

	def tearDown(self):
		frappe.db.rollback()

	def test_host_name_updates_perform_checks_on_host_name(self):
		"""Ensure update of host name triggers verification of host_name."""
		site = create_test_site("testsubdomain")
		site.host_name = "balu.codes"  # domain that doesn't exist
		self.assertRaises(frappe.exceptions.ValidationError, site.save)

	def test_site_has_default_site_domain_on_create(self):
		"""Ensure site has default site domain on create."""
		site = create_test_site("testsubdomain")
		self.assertEqual(site.name, site.host_name)
		self.assertTrue(frappe.db.exists("Site Domain", {"domain": site.name}))

	def test_new_sites_set_host_name_in_site_config(self):
		"""Ensure new sites set host_name in site config in f server."""
		with patch.object(Site, "_update_configuration") as mock_update_config:
			site = create_test_site("testsubdomain", new=True)
		mock_update_config.assert_called_with(
			{"host_name": f"https://{site.name}"}, save=False
		)

	def test_rename_updates_name(self):
		"""Ensure rename changes name of site."""
		domain = frappe.db.get_single_value("Press Settings", "domain")
		site = create_test_site("old-name")
		new_name = f"new-name.{domain}"
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

		self.assertFalse(frappe.db.exists("Site", {"name": f"old-name.{domain}"}))
		self.assertTrue(frappe.db.exists("Site", {"name": new_name}))

	def test_rename_creates_2_agent_jobs(self):
		"""Ensure rename creates 2 agent jobs (for f & n)."""
		domain = frappe.db.get_single_value("Press Settings", "domain")
		site = create_test_site("old-name")
		new_name = f"new-name.{domain}"

		rename_jobs_count_before = frappe.db.count("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_jobs_count_before = frappe.db.count(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)

		site.rename(new_name)

		rename_jobs_count_after = frappe.db.count("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_jobs_count_after = frappe.db.count(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)

		self.assertEqual(rename_jobs_count_after - rename_jobs_count_before, 1)
		self.assertEqual(
			rename_upstream_jobs_count_after - rename_upstream_jobs_count_before, 1
		)

	def test_subdomain_update_renames_site(self):
		"""Ensure updating subdomain renames site."""
		site = create_test_site("old-name")
		new_subdomain_name = "new-name"

		rename_jobs_count_before = frappe.db.count("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_jobs_count_before = frappe.db.count(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)

		site.subdomain = new_subdomain_name
		site.save()

		rename_jobs_count_after = frappe.db.count("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_jobs_count_after = frappe.db.count(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)

		self.assertEqual(rename_jobs_count_after - rename_jobs_count_before, 1)
		self.assertEqual(
			rename_upstream_jobs_count_after - rename_upstream_jobs_count_before, 1
		)

	def test_default_domain_is_renamed_along_with_site(self):
		"""Ensure default domains are renamed when site is renamed."""
		site = create_test_site("old-name")
		old_name = site.name
		new_name = "new-name.fc.dev"

		self.assertTrue(frappe.db.exists("Site Domain", site.name))
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

		self.assertFalse(frappe.db.exists("Site Domain", old_name))
		self.assertTrue(frappe.db.exists("Site Domain", new_name))

	def test_site_becomes_active_after_successful_rename(self):
		"""Ensure site becomes active after successful rename."""
		site = create_test_site("old-name")
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
		self.assertEqual(site.status, "Active")

	@patch.object(Site, "rename")
	def test_rename_site_not_called_for_new_site(self, mock_rename):
		"""Rename Site job isn't created for new site."""
		create_test_site("some-name", new=True)
		mock_rename.assert_not_called()

	def test_site_rename_update_site_config(self):
		"""Ensure site configuration child table is updated after rename."""
		site = create_test_site("old-name")
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
		self.assertEqual(config_host, f"https://{new_name}")

	def test_no_new_jobs_after_rename(self):
		"""Ensure no new jobs are created after rename."""
		site = create_test_site("old-name")
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

		job_count_before = frappe.db.count("Agent Job")
		process_rename_site_job_update(rename_job)
		job_count_after = frappe.db.count("Agent Job")
		self.assertEqual(job_count_before, job_count_after)
