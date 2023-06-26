# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import Mock, patch

import frappe
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
