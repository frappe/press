# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt

from datetime import datetime, timedelta

import json
import unittest
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.database_server.test_database_server import (
	create_test_database_server,
)
from press.press.doctype.proxy_server.test_proxy_server import create_test_proxy_server
from press.press.doctype.root_domain.root_domain import RootDomain
from press.press.doctype.server.test_server import create_test_server


@patch.object(RootDomain, "after_insert", new=Mock())
def create_test_root_domain(
	name: str,
	default_cluster: str = "Default",
):
	root_domain = frappe.get_doc(
		{
			"doctype": "Root Domain",
			"name": name,
			"default_cluster": default_cluster,
			"aws_access_key_id": "a",
			"aws_secret_access_key": "b",
		}
	).insert(ignore_if_duplicate=True)
	root_domain.reload()
	return root_domain


@patch.object(AgentJob, "after_insert", new=Mock())
class TestRootDomain(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _create_fake_rename_job(self, site_name: str, creation=None):
		if not creation:
			creation = datetime.now()
		server = create_test_server(
			create_test_proxy_server().name, create_test_database_server().name
		)

		job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"job_type": "Rename Site",
				"request_data": json.dumps({"new_name": site_name}),
				"server_type": "Server",
				"server": server.name,
				"request_path": "fake/rename/path",
			}
		).insert(ignore_if_duplicate=True)
		job.db_set("creation", creation)

	def test_sites_being_renamed_are_considered_active(self):
		new_site_name = "new_site.frappe.cloud"
		old_site_name = "old_site.frappe.cloud"
		root_domain = create_test_root_domain("frappe.dev")

		self._create_fake_rename_job(new_site_name)
		self._create_fake_rename_job(old_site_name, datetime.now() - timedelta(hours=2))

		self.assertIn(new_site_name, root_domain.get_active_domains())
		self.assertNotIn(old_site_name, root_domain.get_active_domains())
