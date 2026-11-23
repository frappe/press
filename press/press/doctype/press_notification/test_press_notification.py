# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import frappe
from frappe.exceptions import FrappeTypeError
from frappe.tests.utils import FrappeTestCase

from press.api.notifications import get_notifications, get_unread_count
from press.press.doctype.agent_job.agent_job import poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import create_test_agent_job, fake_agent_job
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy_candidate_difference.test_deploy_candidate_difference import (
	create_test_deploy_candidate_differences,
)
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.team.test_team import create_test_team


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

	def test_secrets_in_traceback_are_masked(self):
		from press.press.doctype.agent_job.test_agent_job import create_test_agent_job
		from press.press.doctype.team.test_team import create_test_team

		notification = frappe.get_doc(
			{
				"doctype": "Press Notification",
				"team": create_test_team().name,
				"type": "Agent Job Failure",
				"document_type": "Agent Job",
				"document_name": create_test_agent_job().name,
				"traceback": "self = Conn(db_name='_db1', password='leaked')",  # pragma: allowlist secret
			}
		).insert()

		traceback = frappe.db.get_value("Press Notification", notification.name, "traceback")
		self.assertEqual(traceback, "self = Conn(db_name='_db1', password='********')")

	def test_get_notifications_rejects_sql_in_pagination_arguments(self):
		with self.assertRaisesRegex(FrappeTypeError, "Argument 'limit_start'.*should be of type 'int'"):
			get_notifications(limit_start="0; SELECT SLEEP(10)-- -")
		with self.assertRaisesRegex(FrappeTypeError, "Argument 'limit_page_length'.*should be of type 'int'"):
			get_notifications(limit_page_length="20; SELECT SLEEP(10)-- -")

	def test_get_notifications_accepts_numeric_strings_for_pagination(self):
		self.assertEqual(get_notifications(limit_start="0", limit_page_length="20"), [])


class TestPressNotificationReference(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def notify_about(self, document_type: str, document_name: str, **fields):
		return frappe.get_doc(
			{
				"doctype": "Press Notification",
				"team": create_test_team().name,
				"type": "Agent Job Failure",
				"document_type": document_type,
				"document_name": document_name,
				**fields,
			}
		).insert(ignore_permissions=True)

	def test_agent_job_notification_references_the_site_of_the_job(self):
		site = create_test_site()
		job = create_test_agent_job()
		job.db_set({"site": site.name, "bench": site.bench})

		notification = self.notify_about("Agent Job", job.name)

		self.assertEqual((notification.reference_doctype, notification.reference_name), ("Site", site.name))

	def test_agent_job_notification_on_a_bench_references_the_release_group_of_the_bench(self):
		bench = create_test_bench(group=create_test_release_group([create_test_app()]))
		job = create_test_agent_job()
		job.db_set("bench", bench.name)

		notification = self.notify_about("Agent Job", job.name)

		self.assertEqual(
			(notification.reference_doctype, notification.reference_name), ("Release Group", bench.group)
		)

	def test_agent_job_notification_without_site_or_bench_references_the_server_of_the_job(self):
		job = create_test_agent_job()

		notification = self.notify_about("Agent Job", job.name)

		self.assertEqual(
			(notification.reference_doctype, notification.reference_name), ("Server", job.server)
		)

	def test_agent_job_notification_without_a_job_does_not_reference_another_teams_job(self):
		site = create_test_site()
		create_test_agent_job().db_set({"site": site.name})

		notification = self.notify_about("Agent Job", 0)

		self.assertFalse(notification.reference_doctype)
		self.assertFalse(notification.reference_name)

	def test_auto_scale_and_nfs_volume_notifications_reference_the_primary_server(self):
		for document_type in ("Auto Scale Record", "NFS Volume Attachment", "NFS Volume Detachment"):
			with self.subTest(document_type=document_type):
				document = frappe.get_doc({"doctype": document_type, "primary_server": "f1.example.com"})
				document.db_insert()

				notification = self.notify_about(document_type, document.name)

				self.assertEqual(
					(notification.reference_doctype, notification.reference_name),
					("Server", "f1.example.com"),
				)

	def test_notification_keeps_the_reference_its_creator_set(self):
		site = create_test_site()

		notification = self.notify_about(
			"Site", site.name, reference_doctype="Server", reference_name=site.server
		)

		self.assertEqual(
			(notification.reference_doctype, notification.reference_name), ("Server", site.server)
		)
