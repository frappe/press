# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import unittest
from datetime import datetime
from typing import Optional
from unittest.mock import Mock, patch

import frappe
from frappe.model.naming import make_autoname

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.site import Site, process_rename_site_job_update

from press.press.doctype.release_group.release_group import ReleaseGroup


def create_test_bench(
	user: str = "Administrator",
	group: ReleaseGroup = None,
	server: str = None,
	apps: Optional[list[dict]] = None,
):
	"""
	Create test Bench doc.

	API call to agent will be faked when creating the doc.
	"""
	if not server:
		proxy_server = create_test_proxy_server()
		database_server = create_test_database_server()
		server = create_test_server(proxy_server.name, database_server.name).name

	if not group:
		app = create_test_app()
		group = create_test_release_group([app], user)

	name = frappe.mock("name")
	candidate = group.create_deploy_candidate()
	candidate.db_set("docker_image", frappe.mock("url"))
	bench = frappe.get_doc(
		{
			"name": f"Test Bench{name}",
			"doctype": "Bench",
			"status": "Active",
			"background_workers": 1,
			"gunicorn_workers": 2,
			"group": group.name,
			"apps": apps,
			"candidate": candidate.name,
			"server": server,
		}
	).insert(ignore_if_duplicate=True)
	bench.reload()
	return bench


def create_test_site(
	subdomain: str = "",
	new: bool = False,
	creation: datetime = None,
	bench: str = None,
	team: str = None,
	standby_for: Optional[str] = None,
) -> Site:
	"""Create test Site doc.

	Installs all apps present in bench.
	"""
	if not creation:
		creation = datetime.now()
	if not subdomain:
		subdomain = make_autoname("test-site-.#####")
	if not bench:
		bench = create_test_bench()
	else:
		bench = frappe.get_doc("Bench", bench)
	group = frappe.get_doc("Release Group", bench.group)

	status = "Pending" if new else "Active"
	# on_update checks won't be triggered if not Active

	site = frappe.get_doc(
		{
			"doctype": "Site",
			"status": status,
			"subdomain": subdomain,
			"server": bench.server,
			"bench": bench.name,
			"team": team or frappe.get_value("Team", {"user": "Administrator"}, "name"),
			"apps": [{"app": app.app} for app in group.apps],
			"admin_password": "admin",
			"standby_for": standby_for,
		}
	).insert()
	site.db_set("creation", creation)
	site.reload()
	return site


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
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

		rename_job = self._fake_succeed_rename_jobs()
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

	def _fake_succeed_rename_jobs(self):
		rename_step_name_map = {
			"Rename Site": "Rename Site",
			"Rename Site on Upstream": "Rename Site File in Upstream Directory",
		}
		rename_job = frappe.get_last_doc("Agent Job", {"job_type": "Rename Site"})
		rename_upstream_job = frappe.get_last_doc(
			"Agent Job", {"job_type": "Rename Site on Upstream"}
		)
		frappe.db.set_value(
			"Agent Job Step",
			{
				"step_name": rename_step_name_map[rename_job.job_type],
				"agent_job": rename_job.name,
			},
			"status",
			"Success",
		)
		frappe.db.set_value(
			"Agent Job Step",
			{
				"step_name": rename_step_name_map[rename_upstream_job.job_type],
				"agent_job": rename_upstream_job.name,
			},
			"status",
			"Success",
		)
		return rename_job

	def test_default_domain_is_renamed_along_with_site(self):
		"""Ensure default domains are renamed when site is renamed."""
		site = create_test_site("old-name")
		old_name = site.name
		new_name = "new-name.fc.dev"

		self.assertTrue(frappe.db.exists("Site Domain", site.name))
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
		process_rename_site_job_update(rename_job)

		self.assertFalse(frappe.db.exists("Site Domain", old_name))
		self.assertTrue(frappe.db.exists("Site Domain", new_name))

	def test_site_becomes_active_after_successful_rename(self):
		"""Ensure site becomes active after successful rename."""
		site = create_test_site("old-name")
		new_name = "new-name.fc.dev"
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
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

		rename_job = self._fake_succeed_rename_jobs()
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

		rename_job = self._fake_succeed_rename_jobs()
		job_count_before = frappe.db.count("Agent Job")
		process_rename_site_job_update(rename_job)
		job_count_after = frappe.db.count("Agent Job")
		self.assertEqual(job_count_before, job_count_after)

	def test_add_domain_to_config_adds_domains_key_to_site_configuration(self):
		site = create_test_site("testsubdomain")
		domain = "prod.frappe.dev"

		site.add_domain_to_config(domain)
		site.reload()

		domains = site.get_config_value_for_key("domains")
		self.assertIn(domain, domains)

	def test_add_domain_to_config_updates_config_for_existing_domains_key(self):
		site = create_test_site("testsubdomain")
		domain = "prod.frappe.dev"
		domain_2 = "prod2.frappe.dev"
		site._update_configuration({"domains": [domain]})

		site.add_domain_to_config(domain_2)
		site.reload()

		domains = site.get_config_value_for_key("domains")
		self.assertIn(domain, domains)
		self.assertIn(domain_2, domains)

	def test_add_remove_domain_from_config_updates_domains_key(self):
		site = create_test_site("testsubdomain")
		domain = "prod.frappe.dev"
		domain_2 = "prod2.frappe.dev"
		site._update_configuration({"domains": [domain, domain_2]})

		site.remove_domain_from_config(domain)
		site.reload()

		domains = site.get_config_value_for_key("domains")
		self.assertNotIn(domain, domains)
		self.assertIn(domain_2, domains)

	def test_site_rename_doesnt_update_host_name_for_custom_domain(self):
		"""Ensure site configuration isn't updated after rename when custom domain is host_name."""
		from press.press.doctype.site_domain.test_site_domain import create_test_site_domain

		site = create_test_site("old-name")
		site_domain1 = create_test_site_domain(site.name, "sitedomain1.com")
		site.set_host_name(site_domain1.name)
		new_name = "new-name.fc.dev"
		site.rename(new_name)

		rename_job = self._fake_succeed_rename_jobs()
		process_rename_site_job_update(rename_job)
		site = frappe.get_doc("Site", new_name)
		if site.configuration[0].key == "host_name":
			config_host = site.configuration[0].value
		self.assertEqual(config_host, f"https://{site_domain1.name}")
