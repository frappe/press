# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.exceptions import FrappeTypeError
from frappe.tests.utils import FrappeTestCase

from press.api.notifications import get_notifications, get_unread_count
from press.press.doctype.agent_job.agent_job import poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy_candidate_difference.test_deploy_candidate_difference import (
	create_test_deploy_candidate_differences,
)
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.site.test_site import create_test_bench, create_test_site


class TestPressNotification(FrappeTestCase):
	def setUp(self):
		super().setUp()

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

		create_test_deploy_candidate_differences(bench2.candidate)  # for site update to be available

		site = create_test_site(bench=bench1.name)

		self.assertEqual(frappe.db.count("Press Notification"), 0)
		with (
			fake_agent_job(
				"Update Site Pull",
				"Failure",
			),
			fake_agent_job(
				"Recover Failed Site Update",
				"Success",
			),
		):
			site.schedule_update()
			poll_pending_jobs()

		notification = frappe.get_last_doc("Press Notification")
		self.assertEqual(notification.type, "Site Update")
		# api test is added here since it's trivial
		# move to separate file if it gets more complex
		self.assertEqual(get_unread_count(), 1)
		self.assertEqual(get_unread_count("Site Update"), 1)
		self.assertEqual(len(get_notifications(filters={"type": "Site Update"})), 1)

	def test_get_notifications_rejects_sql_in_pagination_arguments(self):
		with self.assertRaisesRegex(FrappeTypeError, "Argument 'limit_start'.*should be of type 'int'"):
			get_notifications(limit_start="0; SELECT SLEEP(10)-- -")
		with self.assertRaisesRegex(FrappeTypeError, "Argument 'limit_page_length'.*should be of type 'int'"):
			get_notifications(limit_page_length="20; SELECT SLEEP(10)-- -")

	def test_get_notifications_accepts_numeric_strings_for_pagination(self):
		self.assertEqual(get_notifications(limit_start="0", limit_page_length="20"), [])
