# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests
import responses
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent, AgentRequestSkippedException
from press.press.doctype.agent_request_failure.agent_request_failure import (
	remove_old_failures,
)
from press.press.doctype.server.test_server import create_test_server


def create_test_agent_request_failure(server, traceback="Traceback", error="Error", failure_count=1):
	fields = {
		"server_type": server.doctype,
		"server": server.name,
		"traceback": traceback,
		"error": error,
		"failure_count": failure_count,
	}

	return frappe.new_doc("Agent Request Failure", **fields).insert(ignore_permissions=True)


class TestAgent(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@responses.activate
	def test_ping_request(self):
		server = create_test_server()

		responses.add(
			responses.GET,
			f"https://{server.name}:443/agent/ping",
			status=200,
			json={"message": "pong"},
		)

		agent = Agent(server.name, server.doctype)
		agent.request("GET", "ping")

	@responses.activate
	def test_request_failure_creates_failure_record(self):
		server = create_test_server()

		responses.add(
			responses.GET,
			f"https://{server.name}:443/agent/ping",
			body=requests.ConnectTimeout(),
		)

		failures_before = frappe.db.count("Agent Request Failure")

		agent = Agent(server.name, server.doctype)
		self.assertRaises(requests.ConnectTimeout, agent.request, "GET", "ping")

		failures_after = frappe.db.count("Agent Request Failure")
		self.assertEqual(failures_after, failures_before + 1)

		failure = frappe.get_last_doc("Agent Request Failure")
		self.assertEqual(failure.server, server.name)
		self.assertEqual(failure.server_type, server.doctype)
		self.assertEqual(failure.failure_count, 1)

	@responses.activate
	def test_request_skips_after_past_failure(self):
		server = create_test_server()

		responses.add(
			responses.GET,
			f"https://{server.name}:443/agent/ping",
			body=requests.ConnectTimeout(),
		)

		agent = Agent(server.name, server.doctype)
		self.assertRaises(requests.ConnectTimeout, agent.request, "GET", "ping")
		self.assertRaises(AgentRequestSkippedException, agent.request, "GET", "ping")

	def test_failure_record_asks_to_skip_requests(self):
		server = create_test_server()

		agent = Agent(server.name, server.doctype)
		self.assertEqual(agent.should_skip_requests(), False)

		create_test_agent_request_failure(server)
		self.assertEqual(agent.should_skip_requests(), True)

	@responses.activate
	def test_request_succeeds_after_removing_failure_record(self):
		server = create_test_server()

		create_test_agent_request_failure(server)
		agent = Agent(server.name, server.doctype)
		self.assertRaises(AgentRequestSkippedException, agent.request, "GET", "ping")

		responses.add(
			responses.GET,
			f"https://{server.name}:443/agent/ping",
			status=200,
			json={"message": "pong"},
		)
		frappe.db.delete("Agent Request Failure", {"server": server.name})
		self.assertEqual(agent.request("GET", "ping"), {"message": "pong"})

	@responses.activate
	def test_remove_function_removes_failure_if_ping_succeeds(self):
		server = create_test_server()

		create_test_agent_request_failure(server)
		responses.add(
			responses.GET,
			f"https://{server.name}:443/agent/ping",
			status=200,
			json={"message": "pong"},
		)

		remove_old_failures()

		responses.assert_call_count(f"https://{server.name}:443/agent/ping", 1)
		self.assertEqual(frappe.db.count("Agent Request Failure", {"server": server.name}), 0)
