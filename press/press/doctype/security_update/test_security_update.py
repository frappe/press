# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""
Tests for security_update/security_update.py.

_prepare_package_list() is a pure static method that parses Ansible task output.
Tested with mocked frappe.db.get_value — no real Ansible play is needed.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.security_update.security_update import SecurityUpdate

_MODULE = "press.press.doctype.security_update.security_update"


class TestSecurityUpdatePreparePackageList(FrappeTestCase):
	"""_prepare_package_list() extracts package names from Ansible output."""

	def _run(self, output: str | None):
		play = SimpleNamespace(name="test-play")
		with patch(f"{_MODULE}.frappe.db.get_value", return_value=output):
			return SecurityUpdate._prepare_package_list(play)

	def test_returns_empty_list_when_output_is_none(self):
		result = self._run(None)
		self.assertEqual(result, [])

	def test_parses_single_package(self):
		result = self._run("openssl/focal-security 1.1.1f-1ubuntu2.19 amd64")
		self.assertEqual(result, ["openssl"])

	def test_parses_multiple_packages(self):
		output = "openssl/focal-security 1.1.1f\nlibc6/focal-security 2.31"
		result = self._run(output)
		self.assertIn("openssl", result)
		self.assertIn("libc6", result)

	def test_skips_listing_line(self):
		"""'Listing...' is a header line that must be filtered out."""
		output = "Listing...\nopenssl/focal-security 1.1.1f"
		result = self._run(output)
		self.assertNotIn("Listing...", result)
		self.assertIn("openssl", result)

	def test_empty_string_output_returns_empty_list(self):
		result = self._run("")
		self.assertEqual(result, [])

	def test_package_name_split_on_slash(self):
		"""The package name is the part before the first '/'."""
		result = self._run("curl/focal-security 7.68.0-1ubuntu2.18")
		self.assertEqual(result, ["curl"])

	def test_multiple_packages_with_listing_header(self):
		output = "Listing...\ncurl/focal 7.68\nwget/focal 1.20"
		result = self._run(output)
		self.assertEqual(len(result), 2)
		self.assertIn("curl", result)
		self.assertIn("wget", result)
