# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

from frappe.tests import IntegrationTestCase, UnitTestCase

from press.press.doctype.agent_auth.agent_auth import regenerate_token

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]


class UnitTestAgentAuth(UnitTestCase):
	@patch("frappe.enqueue_doc")
	@patch("frappe.get_all")
	def test_regenerate_token_enqueues_jobs(
		self,
		mock_get_all,
		mock_enqueue_doc,
	):
		mock_get_all.return_value = [
			{"name": "auth-1"},
			{"name": "auth-2"},
		]

		regenerate_token()

		self.assertEqual(mock_enqueue_doc.call_count, 2)


class IntegrationTestAgentAuth(IntegrationTestCase):
	"""
	Integration tests for AgentAuth.
	Use this class for testing interactions between multiple components.
	"""

	pass
