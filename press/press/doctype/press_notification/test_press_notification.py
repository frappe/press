# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy.deploy import create_deploy_candidate_differences
from press.api.notifications import get_unread_count, get_notifications
from press.press.doctype.deploy_candidate.test_deploy_candidate import (
	create_test_deploy_candidate,
)
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.site.test_site import create_test_bench, create_test_site


class TestPressNotification(FrappeTestCase):
	def setUp(self):
		app1 = create_test_app()  # frappe
		app2 = create_test_app("app2", "App 2")
		app3 = create_test_app("app3", "App 3")
		self.apps = [app1, app2, app3]

	def tearDown(self):
		frappe.db.rollback()

	def test_notification_is_created_when_agent_job_fails(self):
		group = create_test_release_group(self.apps)
		bench1 = create_test_bench(group=group)
		bench2 = create_test_bench(group=group, server=bench1.server)

		create_deploy_candidate_differences(bench2)  # for site update to be available

		site = create_test_site(bench=bench1.name)

		self.assertEqual(frappe.db.count("Press Notification"), 0)
		with fake_agent_job("Update Site Pull", "Failure",), fake_agent_job(
			"Recover Failed Site Update",
			"Success",
		):
			site.schedule_update()
			poll_pending_jobs()

		notification = frappe.get_last_doc("Press Notification")
		self.assertEqual(notification.type, "Site Update")
		# api test is added here since it's trivial
		# move to separate file if it gets more complex
		self.assertEqual(get_unread_count(), 1)

	def test_notification_is_created_when_deploy_fails(self):
		group = create_test_release_group(self.apps)
		dc = create_test_deploy_candidate(group)

		self.assertEqual(frappe.db.count("Press Notification"), 0)

		dc.status = "Failure"
		dc.save()

		notification = frappe.get_last_doc("Press Notification")
		self.assertEqual(notification.type, "Bench Deploy")
		# api test is added here since it's trivial
		# move to separate file if it gets more complex
		self.assertEqual(len(get_notifications()), 1)
