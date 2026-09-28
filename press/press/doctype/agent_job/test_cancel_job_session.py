# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from unittest.mock import patch

import frappe
from frappe.tests.test_api import FrappeAPITestCase, make_request
from frappe.utils import get_test_client

from press.agent import Agent
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_team

PASSWORD = "Cancel-Job-Test-1!"  # pragma: allowlist secret


class TestCancelJobSession(FrappeAPITestCase):
	"""Each request runs in its own thread and connection, so the fixtures are committed."""

	def setUp(self):
		self.client = get_test_client()
		self.email = frappe.mock("email")
		Team.create_user(first_name="Cancel", email=self.email, password=PASSWORD)
		self.team = create_test_team(self.email)
		self.site = frappe.get_doc(
			{"doctype": "Site", "name": f"{frappe.generate_hash(8)}.test", "team": self.team.name}
		)
		self.site.db_insert()
		self.job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"name": frappe.generate_hash(10),
				"job_type": "Backup Site",
				"status": "Running",
				"server_type": "Server",
				"server": "cancel-job-test-server",
				"site": self.site.name,
				"job_id": 42,
			}
		)
		self.job.db_insert()
		frappe.db.commit()

	def tearDown(self):
		frappe.db.delete("Agent Job", self.job.name)
		frappe.db.delete("Site", self.site.name)
		frappe.delete_doc("Team", self.team.name, force=True, ignore_permissions=True)
		frappe.db.delete("Account Request", {"email": self.email})
		frappe.delete_doc("User", self.email, force=True, ignore_permissions=True)
		frappe.db.delete("Sessions", {"user": self.email})
		frappe.db.commit()
		super().tearDown()

	def post(self, method: str, data: dict | None = None):
		return make_request(
			target=self.client.post,
			args=(f"/api/method/{method}",),
			# buffered closes the response, which runs after_response and saves the session
			kwargs={"json": data or {}, "headers": {"X-Press-Team": self.team.name}, "buffered": True},
		)

	@patch.object(Agent, "cancel_job")
	def test_press_user_is_still_logged_in_on_the_request_after_cancel_job(self, cancel_job):
		self.post("login", {"usr": self.email, "pwd": PASSWORD})

		cancel = self.post(
			"press.press.doctype.agent_job.agent_job.cancel_job_from_dashboard", {"name": self.job.name}
		)
		self.assertEqual(cancel.status_code, 200, cancel.json)
		cancel_job.assert_called_once_with(42)

		me = self.post("press.api.account.me")
		self.assertEqual(me.status_code, 200, me.json)
		self.assertEqual(me.json["message"]["user"], self.email)
