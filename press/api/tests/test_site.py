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

		site1 = create_test_site(bench=bench)
		site1.status = "Broken"
		site1.save()
		self.site1_dict = {
			"name": site1.name,
			"host_name": site1.host_name,
			"status": site1.status,
			"creation": site1.creation,
			"bench": site1.bench,
			"current_cpu_usage": site1.current_cpu_usage,
			"current_database_usage": site1.current_database_usage,
			"current_disk_usage": site1.current_disk_usage,
			"trial_end_date": site1.trial_end_date,
			"team": site1.team,
			"title": group.title,
			"version": group.version,
		}

		site2 = create_test_site(bench=bench)
		site2.trial_end_date = datetime.datetime.now()
		site2.save()

		self.site2_dict = {
			"name": site2.name,
			"host_name": site2.host_name,
			"status": site2.status,
			"creation": site2.creation,
			"bench": site2.bench,
			"current_cpu_usage": site2.current_cpu_usage,
			"current_database_usage": site2.current_database_usage,
			"current_disk_usage": site2.current_disk_usage,
			"trial_end_date": site2.trial_end_date.date(),
			"team": site2.team,
			"title": group.title,
			"version": group.version,
		}

		site3 = create_test_site(bench=bench)
		create_and_add_test_tag(site3.name, "Site")

		self.site3_dict = {
			"name": site3.name,
			"host_name": site3.host_name,
			"status": site3.status,
			"creation": site3.creation,
			"bench": site3.bench,
			"current_cpu_usage": site3.current_cpu_usage,
			"current_database_usage": site3.current_database_usage,
			"current_disk_usage": site3.current_disk_usage,
			"trial_end_date": site3.trial_end_date,
			"team": site3.team,
			"title": group.title,
			"version": group.version,
		}

	def test_list_all_sites(self):
		self.create_test_sites_for_site_list()
		self.assertEqual(all(), [self.site1_dict, self.site2_dict, self.site3_dict])

	def test_list_broken_sites(self):
		self.create_test_sites_for_site_list()
		self.assertEqual(all(site_filter="Broken"), [self.site1_dict])

	def test_list_trial_sites(self):
		self.create_test_sites_for_site_list()
		self.assertEqual(all(site_filter="Trial"), [self.site2_dict])

	def test_list_tagged_sites(self):
		self.create_test_sites_for_site_list()
		self.assertEqual(all(site_filter="tag:test_tag"), [self.site3_dict])
