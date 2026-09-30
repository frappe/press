# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from unittest.mock import Mock, patch

import frappe
from frappe.tests.test_api import FrappeAPITestCase, make_request
from frappe.utils import get_test_client

from press.press.doctype.release_pipeline.release_pipeline import ReleasePipeline
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_team

PASSWORD = "Stop-Deploy-Test-1!"  # pragma: allowlist secret


class TestStopDeploySession(FrappeAPITestCase):
	"""Each request runs in its own thread and connection, so the fixtures are committed."""

	def setUp(self):
		self.client = get_test_client()
		self.email = frappe.mock("email")
		Team.create_user(first_name="Stop", email=self.email, password=PASSWORD)
		self.team = create_test_team(self.email)
		self.pipeline = frappe.get_doc(
			{
				"doctype": "Release Pipeline",
				"release_group": "stop-deploy-test-group",
				"team": self.team.name,
				"status": "Running",
			}
		)
		self.pipeline.flags.ignore_links = True
		self.pipeline.insert(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.delete_doc("Release Pipeline", self.pipeline.name, force=True, ignore_permissions=True)
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

	# The fixture pipeline has no workflow, and the failure notification reads it
	@patch.object(ReleasePipeline, "send_failure_notification", Mock())
	def test_press_user_is_still_logged_in_on_the_request_after_stop_deploy(self):
		self.post("login", {"usr": self.email, "pwd": PASSWORD})

		stop = self.post(
			"press.api.client.run_doc_method",
			{"dt": "Release Pipeline", "dn": self.pipeline.name, "method": "force_fail"},
		)
		self.assertEqual(stop.status_code, 200, stop.json)
		self.assertEqual(stop.json["docs"][0]["status"], "Failure")

		me = self.post("press.api.account.me")
		self.assertEqual(me.status_code, 200, me.json)
		self.assertEqual(me.json["message"]["user"], self.email)
