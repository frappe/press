# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.site_plan_utils import (
	attach_warranty_info_to_dedicated_servers,
	get_available_warranty_quota_for_server,
	get_server_site_warranty_count,
	get_server_site_warranty_quota,
	is_product_warranty_enabled_for_plan_,
)
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.team.test_team import create_test_team


class TestGetServerSiteWarrantyQuota(FrappeTestCase):
	"""Tests for get_server_site_warranty_quota()."""

	def setUp(self):
		frappe.set_user("Administrator")
		create_test_press_settings()
		self.team = create_test_team()
		self.server = create_test_server(team=self.team.name)

	def tearDown(self):
		frappe.db.rollback()

	def test_raises_when_neither_server_nor_site_given(self):
		"""Calling with no arguments raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			get_server_site_warranty_quota()

	def test_returns_zero_when_no_quota_set(self):
		"""Default server has supported_site_quota=0."""
		quota = get_server_site_warranty_quota(server=self.server.name)
		self.assertEqual(quota, 0)

	def test_returns_correct_quota_after_setting(self):
		"""Returns the current value of supported_site_quota."""
		frappe.db.set_value("Server", self.server.name, "supported_site_quota", 5)
		quota = get_server_site_warranty_quota(server=self.server.name)
		self.assertEqual(quota, 5)


class TestGetServerSiteWarrantyCount(FrappeTestCase):
	"""Tests for get_server_site_warranty_count()."""

	def setUp(self):
		frappe.set_user("Administrator")
		create_test_press_settings()
		self.team = create_test_team()
		self.server = create_test_server(team=self.team.name)

	def tearDown(self):
		frappe.db.rollback()

	def test_raises_when_neither_server_nor_site_given(self):
		"""Calling with no arguments raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			get_server_site_warranty_count()

	def test_returns_zero_when_no_warranty_sites(self):
		"""A server with no warranty-plan sites has count=0."""
		count = get_server_site_warranty_count(server=self.server.name)
		self.assertEqual(count, 0)


class TestIsProductWarrantyEnabledForPlan(FrappeTestCase):
	"""Tests for is_product_warranty_enabled_for_plan_()."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.plan = create_test_plan("Site")

	def tearDown(self):
		frappe.db.rollback()

	def test_returns_false_when_support_not_included(self):
		"""Returns falsy when support_included is not set on the plan."""
		result = is_product_warranty_enabled_for_plan_(self.plan.name)
		self.assertFalse(result)

	def test_returns_true_when_support_included(self):
		"""Returns truthy when support_included is enabled on the plan."""
		frappe.db.set_value("Site Plan", self.plan.name, "support_included", 1)
		result = is_product_warranty_enabled_for_plan_(self.plan.name)
		self.assertTrue(result)


class TestGetAvailableWarrantyQuota(FrappeTestCase):
	"""Tests for get_available_warranty_quota_for_server()."""

	def setUp(self):
		frappe.set_user("Administrator")
		create_test_press_settings()
		self.team = create_test_team()
		self.server = create_test_server(team=self.team.name)

	def tearDown(self):
		frappe.db.rollback()

	def test_returns_dict_with_consumed_total_available_keys(self):
		"""Return value always has consumed, total, and available keys."""
		result = get_available_warranty_quota_for_server(self.server.name)
		self.assertIn("consumed", result)
		self.assertIn("total", result)
		self.assertIn("available", result)

	def test_available_is_total_minus_consumed(self):
		"""available == total - consumed."""
		frappe.db.set_value("Server", self.server.name, "supported_site_quota", 10)
		result = get_available_warranty_quota_for_server(self.server.name)
		self.assertEqual(result["available"], result["total"] - result["consumed"])


class TestAttachWarrantyInfoToDedicatedServers(FrappeTestCase):
	"""Tests for attach_warranty_info_to_dedicated_servers()."""

	def tearDown(self):
		frappe.db.rollback()

	def test_public_server_is_skipped(self):
		"""A server with public=True should NOT receive product_warranty info."""
		servers = [{"name": "some-server", "public": True}]
		result = attach_warranty_info_to_dedicated_servers(servers)
		self.assertNotIn("product_warranty", result[0])

	def test_server_without_public_flag_defaults_to_truthy_and_is_skipped(self):
		"""If 'public' is absent, server.get('public', True) defaults to True → skipped."""
		servers = [{"name": "some-server"}]
		result = attach_warranty_info_to_dedicated_servers(servers)
		self.assertNotIn("product_warranty", result[0])

	def test_private_server_receives_warranty_info(self):
		"""A server with public=False receives product_warranty from the DB."""
		fake_quota = {"consumed": 1, "total": 5, "available": 4}
		servers = [{"name": "some-server", "public": False}]

		with patch(
			"press.press.doctype.site.site_plan_utils.get_available_warranty_quota_for_server",
			return_value=fake_quota,
		):
			result = attach_warranty_info_to_dedicated_servers(servers)

		self.assertIn("product_warranty", result[0])
		self.assertEqual(result[0]["product_warranty"], fake_quota)

	def test_mixed_server_list_only_attaches_to_private(self):
		"""Only non-public servers in a mixed list get warranty info."""
		fake_quota = {"consumed": 0, "total": 3, "available": 3}
		servers = [
			{"name": "public-srv", "public": True},
			{"name": "private-srv", "public": False},
		]

		with patch(
			"press.press.doctype.site.site_plan_utils.get_available_warranty_quota_for_server",
			return_value=fake_quota,
		):
			result = attach_warranty_info_to_dedicated_servers(servers)

		self.assertNotIn("product_warranty", result[0])
		self.assertIn("product_warranty", result[1])

	def test_returns_the_same_list_mutated_in_place(self):
		"""The function mutates and returns the same list object."""
		servers = [{"name": "some-server", "public": True}]
		result = attach_warranty_info_to_dedicated_servers(servers)
		self.assertIs(result, servers)
