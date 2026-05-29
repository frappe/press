from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from press.api.agent_auth import verify_agent


class TestAgentAuth(TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_verify_agent_throws_without_token(self):
		frappe.local.request = frappe._dict({"headers": {}})

		self.assertRaises(
			frappe.PermissionError,
			verify_agent,
		)

	@patch("press.api.agent_auth.extract_server_from_token")
	@patch("press.api.agent_auth.Agent")
	def test_verify_agent_calls_extract_and_verify_token(
		self,
		mock_agent,
		mock_extract_server,
	):
		mock_extract_server.return_value = (
			"test-server",
			"Server",
		)

		mock_instance = Mock()
		mock_agent.return_value = mock_instance

		frappe.local.request = frappe._dict({"headers": {"X-Agent-Token": "test-token"}})

		server, server_type = verify_agent()

		self.assertEqual(server, "test-server")
		self.assertEqual(server_type, "Server")

		mock_extract_server.assert_called_once_with("test-token")

		mock_agent.assert_called_once_with("test-server")

		mock_instance.extract_and_verify_token.assert_called_once_with("test-token")
