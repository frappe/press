# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import datetime
import unittest
from unittest.mock import Mock, patch

import frappe

from press.api.site import all
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestAPISite(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_options_contains_only_public_groups_when_private_group_is_not_given(
		self,
	):
		from press.api.site import get_new_site_options

		app = create_test_app()

		group12 = create_test_release_group([app], public=True, frappe_version="Version 12")
		group13 = create_test_release_group([app], public=True, frappe_version="Version 13")
		group14 = create_test_release_group([app], public=True, frappe_version="Version 14")
		private_group = create_test_release_group(
			[app], public=False, frappe_version="Version 14"
		)

		create_test_bench(group=group12)
		create_test_bench(group=group13)
		create_test_bench(group=group14)
		create_test_bench(group=private_group)

		options = get_new_site_options()

		for version in options["versions"]:
			if version["name"] == "Version 14":
				self.assertEqual(version["group"]["name"], group14.name)

	def create_test_sites_for_site_list(self):
		from press.press.doctype.press_tag.test_press_tag import create_and_add_test_tag
		from press.press.doctype.site.test_site import create_test_site

		app = create_test_app()
		group = create_test_release_group([app])
		bench = create_test_bench(group=group)

		broken_site = create_test_site(bench=bench)
		broken_site.status = "Broken"
		broken_site.save()
		self.broken_site_dict = {
			"name": broken_site.name,
			"host_name": broken_site.host_name,
			"status": broken_site.status,
			"creation": broken_site.creation,
			"bench": broken_site.bench,
			"current_cpu_usage": broken_site.current_cpu_usage,
			"current_database_usage": broken_site.current_database_usage,
			"current_disk_usage": broken_site.current_disk_usage,
			"trial_end_date": broken_site.trial_end_date,
			"team": broken_site.team,
			"title": group.title,
			"version": group.version,
		}

		trial_site = create_test_site(bench=bench)
		trial_site.trial_end_date = datetime.datetime.now()
		trial_site.save()

		self.trial_site_dict = {
			"name": trial_site.name,
			"host_name": trial_site.host_name,
			"status": trial_site.status,
			"creation": trial_site.creation,
			"bench": trial_site.bench,
			"current_cpu_usage": trial_site.current_cpu_usage,
			"current_database_usage": trial_site.current_database_usage,
			"current_disk_usage": trial_site.current_disk_usage,
			"trial_end_date": trial_site.trial_end_date.date(),
			"team": trial_site.team,
			"title": group.title,
			"version": group.version,
		}

		tagged_site = create_test_site(bench=bench)
		create_and_add_test_tag(tagged_site.name, "Site")

		self.tagged_site_dict = {
			"name": tagged_site.name,
			"host_name": tagged_site.host_name,
			"status": tagged_site.status,
			"creation": tagged_site.creation,
			"bench": tagged_site.bench,
			"current_cpu_usage": tagged_site.current_cpu_usage,
			"current_database_usage": tagged_site.current_database_usage,
			"current_disk_usage": tagged_site.current_disk_usage,
			"trial_end_date": tagged_site.trial_end_date,
			"team": tagged_site.team,
			"title": group.title,
			"version": group.version,
		}

	def test_list_all_sites(self):
		self.create_test_sites_for_site_list()
		self.assertEqual(
			all(), [self.broken_site_dict, self.trial_site_dict, self.tagged_site_dict]
		)

	def test_list_broken_sites(self):
		self.create_test_sites_for_site_list()
		self.assertEqual(all(site_filter="Broken"), [self.broken_site_dict])

	def test_list_trial_sites(self):
		self.create_test_sites_for_site_list()
		self.assertEqual(all(site_filter="Trial"), [self.trial_site_dict])

	def test_list_tagged_sites(self):
		self.create_test_sites_for_site_list()
		self.assertEqual(all(site_filter="tag:test_tag"), [self.tagged_site_dict])
