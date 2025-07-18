# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import frappe
from frappe.core.utils import find
from moto import mock_aws

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.root_domain.root_domain import RootDomain


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


@mock_aws
@patch.object(AgentJob, "after_insert", new=Mock())
class TestRootDomain(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _create_fake_rename_job(self, site_name: str, creation=None):
		from press.press.doctype.database_server.test_database_server import (
			create_test_database_server,
		)
		from press.press.doctype.proxy_server.test_proxy_server import (
			create_test_proxy_server,
		)
		from press.press.doctype.server.test_server import create_test_server

		creation = creation or frappe.utils.now_datetime()
		server = create_test_server(create_test_proxy_server().name, create_test_database_server().name)

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

	def _create_aws_root_domain(self, name: str, parent_domain: str | None = None) -> RootDomain:
		return frappe.get_doc(
			{
				"doctype": "Root Domain",
				"name": name,
				"default_cluster": "Default",
				"dns_provider": "AWS Route 53",
				"aws_access_key_id": "a",
				"aws_secret_access_key": "b",
				"parent_domain": parent_domain,
			}
		).insert()

	def test_creation_of_root_domain_creates_aws_hosted_zone(self):
		root_domain = self._create_aws_root_domain("frappe.dev")
		self.assertIsNotNone(root_domain.hosted_zone)

	def test_creation_of_root_domain_that_is_subdomain_of_existing_zone_creates_ns_record_within_root_domain(
		self,
	):
		d = self._create_aws_root_domain(
			"b.frappe.dev"
		)  # similar record to subdomain to throw off any guessing
		self.assertIsNotNone(d.hosted_zone)

		root_domain_1 = self._create_aws_root_domain("frappe.dev")
		self.assertIsNotNone(root_domain_1.hosted_zone)
		records_1 = next(iter(root_domain_1.get_dns_record_pages()))["ResourceRecordSets"]
		self.assertEqual(len(records_1), 2)

		self._create_aws_root_domain("ub.frappe.dev")  # similar record to subdomain to throw off any guessing
		self.assertIsNotNone(d.hosted_zone)

		root_domain_2 = self._create_aws_root_domain("sub.frappe.dev", parent_domain="frappe.dev")
		self.assertIsNotNone(root_domain_2.hosted_zone)
		records_2 = next(iter(root_domain_2.get_dns_record_pages()))["ResourceRecordSets"]
		self.assertEqual(len(records_2), 2)

		records_1 = next(iter(root_domain_1.get_dns_record_pages()))["ResourceRecordSets"]
		self.assertEqual(len(records_1), 3)
		self.assertEqual(find(records_1, lambda x: x["Name"] == "sub.frappe.dev.")["Type"], "NS")

	def test_creation_of_sibling_domain_does_not_add_ns_record_to_existing_root_domain(self):
		root_domain_1 = self._create_aws_root_domain("x.frappe.dev")
		self.assertIsNotNone(root_domain_1.hosted_zone)

		records_1 = next(iter(root_domain_1.get_dns_record_pages()))["ResourceRecordSets"]
		self.assertEqual(len(records_1), 2)

		root_domain_2 = self._create_aws_root_domain("y.frappe.dev")
		self.assertIsNotNone(root_domain_2.hosted_zone)
		records_2 = next(iter(root_domain_2.get_dns_record_pages()))["ResourceRecordSets"]
		self.assertEqual(len(records_2), 2)

		records_1 = next(iter(root_domain_1.get_dns_record_pages()))["ResourceRecordSets"]
		self.assertEqual(len(records_1), 2)
