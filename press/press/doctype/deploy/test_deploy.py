# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDeployBuildForBench(FrappeTestCase):
	"""Deploy._get_build_for_bench selects arm_build for arm64 servers and intel_build for x86_64.

	Wrong mapping deploys the wrong Docker image architecture, causing immediate bench startup failure.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.deploy = frappe.get_doc(
			{
				"doctype": "Deploy",
				"candidate": "DC-TEST-001",
				"group": "RG-TEST",
				"team": "test@example.com",
			}
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_arm64_fetches_arm_build_field(self):
		mock_build = Mock()
		with (
			patch("frappe.get_value", return_value="DCB-001") as mock_gv,
			patch("frappe.get_doc", return_value=mock_build),
		):
			result = self.deploy._get_build_for_bench("arm64")
		mock_gv.assert_called_once_with("Deploy Candidate", "DC-TEST-001", "arm_build")
		self.assertIs(result, mock_build)

	def test_x86_64_fetches_intel_build_field(self):
		mock_build = Mock()
		with (
			patch("frappe.get_value", return_value="DCB-001") as mock_gv,
			patch("frappe.get_doc", return_value=mock_build),
		):
			result = self.deploy._get_build_for_bench("x86_64")
		mock_gv.assert_called_once_with("Deploy Candidate", "DC-TEST-001", "intel_build")
		self.assertIs(result, mock_build)

	def test_unknown_platform_passes_none_field(self):
		"""Platform not in the mapping must pass None as field — callers handle the None build."""
		mock_build = Mock()
		with (
			patch("frappe.get_value", return_value=None) as mock_gv,
			patch("frappe.get_doc", return_value=mock_build),
		):
			self.deploy._get_build_for_bench("riscv64")
		mock_gv.assert_called_once_with("Deploy Candidate", "DC-TEST-001", None)
